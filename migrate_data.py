"""BCE Project 2A, Step 6: copy SQLite users to the existing Azure SQL table.

Save this file in ~/bce-legacy-app and run it from the project's virtual
environment. Stop Flask first. The source database is opened read-only.
The SQL password is requested privately and is never saved in this file.
"""

from contextlib import closing
from datetime import datetime
from getpass import getpass
from pathlib import Path
import re
import sqlite3
import sys

import pyodbc


SOURCE = Path.home() / "bce-legacy-app" / "instance" / "club_security.db"
SERVER = "bce-sql-server-077b16c4c60a.database.windows.net"
DATABASE = "club_security_db"
ADMIN_USER = "clubadmin"
DRIVER = "ODBC Driver 18 for SQL Server"


def source_user(row):
    """Validate the source without silently shortening or changing values."""
    user_id, username, password_hash, role, created_at = row
    if not isinstance(user_id, int) or not 1 <= user_id <= 2147483647:
        raise ValueError("A source user ID does not fit the Azure INT column.")
    for name, value, limit, nullable in (
        ("username", username, 80, False),
        ("password hash", password_hash, 255, False),
        ("role", role, 50, True),
    ):
        if value is None and nullable:
            continue
        if not isinstance(value, str):
            raise ValueError(f"User ID {user_id}: invalid {name} value.")
        if len(value.encode("utf-16-le")) // 2 > limit:
            raise ValueError(f"User ID {user_id}: {name} exceeds the Azure column size.")
    if created_at is not None:
        if not isinstance(created_at, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?", created_at
        ):
            raise ValueError(f"User ID {user_id}: unexpected creation-date format.")
        try:
            created_at = datetime.fromisoformat(created_at)
        except ValueError:
            raise ValueError(f"User ID {user_id}: invalid creation date.") from None
    return user_id, username, password_hash, role, created_at


def read_source(path=SOURCE):
    if not path.is_file():
        raise ValueError(f"SQLite database not found: {path}. Do not run init_db.py.")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        rows = source.execute(
            'SELECT id, username, password, role, created_at FROM "user" ORDER BY id'
        ).fetchall()
    if not rows:
        raise ValueError("SQLite contains no users. Check the source before migrating.")
    return [source_user(row) for row in rows]


def odbc_value(value):
    """Protect connection-string values containing semicolons or braces."""
    return "{" + value.replace("}", "}}") + "}"


def read_target(cursor, lock=False):
    query = "SELECT [id], [username], [password], [role], [created_at] FROM [dbo].[user]"
    if lock:
        query += " WITH (TABLOCKX, HOLDLOCK)"
    return [tuple(row) for row in cursor.execute(query + " ORDER BY [id]").fetchall()]


def copy_users(connection, users):
    """Copy and verify inside one transaction; stop on any existing differences."""
    cursor = connection.cursor()
    try:
        cursor.execute("SET XACT_ABORT ON;")
        source_by_id = {row[0]: row for row in users}
        existing = read_target(cursor, lock=True)
        for row in existing:
            if source_by_id.get(row[0]) != row:
                raise ValueError(
                    "Azure contains an extra or different user record. "
                    "No existing records were overwritten. Stop and review both databases."
                )
        existing_ids = {row[0] for row in existing}
        missing = [row for row in users if row[0] not in existing_ids]
        if missing:
            cursor.execute("SET IDENTITY_INSERT [dbo].[user] ON;")
            for row in missing:
                # ISO text plus an explicit SQL conversion preserves all six
                # SQLite microsecond digits across ODBC driver versions.
                created_text = row[4].isoformat(timespec="microseconds") if row[4] else None
                cursor.execute(
                    "INSERT INTO [dbo].[user] "
                    "([id], [username], [password], [role], [created_at]) "
                    "VALUES (?, ?, ?, ?, CONVERT(datetime2(6), ?, 126))",
                    (*row[:4], created_text),
                )
            cursor.execute("SET IDENTITY_INSERT [dbo].[user] OFF;")
        if read_target(cursor) != users:
            raise ValueError("The copied records did not match SQLite. Saving was stopped.")
        connection.commit()
        return len(missing)
    except BaseException:
        # A lost connection during commit can leave the outcome uncertain.
        # Re-running this script checks existing rows before inserting anything.
        try:
            connection.rollback()
        except pyodbc.Error:
            pass
        raise
    finally:
        # Closing the connection in main also clears session IDENTITY_INSERT state.
        try:
            cursor.close()
        except pyodbc.Error:
            pass


def main():
    if DRIVER not in pyodbc.drivers():
        raise ValueError(f"Install {DRIVER} on this Mac before running the migration.")
    users = read_source()
    print(f"Found {len(users)} users in SQLite database")
    print(f"Destination: {SERVER} / {DATABASE}")
    if not sys.stdin.isatty():
        raise ValueError("Run this file in Terminal so the password can be entered privately.")
    password = getpass("Enter the clubadmin SQL password from Step 2, then press Return: ")
    if not password:
        raise ValueError("No password entered. Nothing was migrated.")
    connection_string = (
        f"DRIVER={odbc_value(DRIVER)};SERVER=tcp:{SERVER},1433;"
        f"DATABASE={DATABASE};UID={ADMIN_USER};PWD={odbc_value(password)};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    print("Connecting and copying users. Please wait...")
    with closing(pyodbc.connect(connection_string, autocommit=False, timeout=30)) as connection:
        connection.timeout = 60
        inserted = copy_users(connection, users)
        with closing(connection.cursor()) as cursor:
            verified = read_target(cursor)
        if verified != users:
            raise ValueError("The saved data changed after the copy. Review it before continuing.")
        connection.rollback()  # End the final read-only verification transaction.
    if inserted:
        print(f"Successfully migrated {inserted} new users to Azure SQL Database")
    else:
        print("All users were already migrated. No duplicates were added.")
    print(f"Verification: {len(verified)} users now in Azure SQL")
    print("Verified: IDs, usernames, password hashes, roles, and creation dates match SQLite.")
    print("Step 6 complete: Data migrated from SQLite to Azure SQL.")
    print("Your original SQLite database was not changed.")


if __name__ == "__main__":
    try:
        main()
    except pyodbc.Error as error:
        state = str(error.args[0]) if error.args else "unknown"
        print(f"Migration stopped (SQLSTATE {state}).", file=sys.stderr)
        if state == "28000":
            print("Check the existing clubadmin SQL password from Step 2.", file=sys.stderr)
        elif state in {"08001", "08004", "08S01", "HYT00", "HYT01"}:
            print("Check internet access, the SQL server, and your current IP firewall rule.", file=sys.stderr)
        elif state == "42S02":
            print("The Azure user table is missing. Complete Step 5 first.", file=sys.stderr)
        elif state == "23000":
            print("A database rule rejected a record, such as a duplicate username.", file=sys.stderr)
        print("Success was not confirmed. Share this message, not your password.", file=sys.stderr)
        print("This script can be rerun safely after the problem is fixed.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, sqlite3.Error, OSError) as error:
        print(f"Migration stopped: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nMigration interrupted. Rerun the same script to check its status safely.", file=sys.stderr)
        sys.exit(1)
