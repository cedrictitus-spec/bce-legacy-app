"""Project 2B: verify encryption using the real Flask app's SQLAlchemy engine.

Run with venv active: python3 verify_encryption.py
Use the lab SQL administrator account; Azure SQL Basic restricts these DMVs.
This script only reads data. It does not initialize or migrate the database.
"""

import json
import sys

from azure_connection import DATABASE, Project2BError, safe_error


def inspect_connection(connection):
    """Use a single live connection for every encryption check."""
    name = connection.exec_driver_sql("SELECT DB_NAME();").scalar_one()
    if name != DATABASE:
        raise Project2BError("WRONG_DATABASE: Flask is not connected to club_security_db.")
    at_rest = connection.exec_driver_sql(
        "SELECT is_encrypted FROM sys.databases WHERE name = DB_NAME();"
    ).scalar_one()
    key_state = connection.exec_driver_sql(
        "SELECT encryption_state FROM sys.dm_database_encryption_keys WHERE database_id = DB_ID();"
    ).scalar_one_or_none()
    transport = connection.exec_driver_sql(
        "SELECT encrypt_option FROM sys.dm_exec_connections WHERE session_id = @@SPID;"
    ).scalars().all()
    count = connection.exec_driver_sql("SELECT COUNT_BIG(*) FROM [dbo].[user];").scalar_one()
    users = connection.exec_driver_sql(
        "SELECT [username], [role] FROM [dbo].[user] ORDER BY [id];"
    ).all()
    return {
        "database": name,
        "is_encrypted": at_rest,
        "encryption_state": key_state,
        "transport": transport,
        "count": count,
        "users": users,
    }


def display_and_check(result):
    print(f"Database: {result['database']}")
    at_rest_label = int(result["is_encrypted"]) if isinstance(result["is_encrypted"], (bool, int)) else result["is_encrypted"]
    print(f"is_encrypted: {at_rest_label} (expected 1)")
    print(f"encryption_state: {result['encryption_state']} (expected 3 = encrypted)")
    print("Current Flask SQL connection encrypt_option: " + ", ".join(str(x) for x in result["transport"]))
    print(f"User count: {result['count']}")
    print("Users (passwords and password hashes are not selected):")
    for username, role in result["users"]:
        print(f"  {json.dumps(username, ensure_ascii=True)} | {json.dumps(role, ensure_ascii=True)}")
    if result["is_encrypted"] != 1 or result["encryption_state"] != 3:
        raise Project2BError("TDE_NOT_READY: Encryption at rest is not fully confirmed. Check Step 1's TDE status.")
    if not result["transport"] or any(str(x).upper() != "TRUE" for x in result["transport"]):
        raise Project2BError("TLS_NOT_CONFIRMED: The current Flask database connection is not confirmed encrypted.")
    if result["count"] < 1:
        raise Project2BError("NO_USERS: No migrated users were found. Check Project 2A's migration.")
    if result["count"] != len(result["users"]):
        raise Project2BError("DATA_CHANGED_DURING_CHECK: Stop other app activity and run this read-only check again.")


def main():
    try:
        # Import here so configuration/import failures get a safe error message.
        from app import app, db

        with app.app_context():
            engine = db.engine
            if engine.dialect.name != "mssql":
                raise Project2BError("WRONG_ENGINE: Flask still uses a different database. Finish Step 4's app.py change.")
            # Never print engine.url: its ODBC query parameter contains the secret.
            with engine.connect() as connection:
                result = inspect_connection(connection)
            display_and_check(result)
        print("PASS: TDE is active and the Flask app's database connection is encrypted.")
        print("No SQL data was changed. This check does not test browser-to-Flask HTTPS.")
        print("Step 6 complete: encryption verified through the Flask configuration.")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nCanceled. No SQL data was changed by this verification script.", file=sys.stderr)
        return 130
    except Exception as exc:
        print("ERROR: " + safe_error(exc), file=sys.stderr)
        print("Encryption verification is incomplete.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
