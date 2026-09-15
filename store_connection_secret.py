"""Project 2B: privately validate the SQL password, then save it in Key Vault.

Run in the VS Code terminal with venv active: python3 store_connection_secret.py
This reads SQL data only. Re-running creates a new version of the vault secret.
"""

from contextlib import closing
import getpass
import hmac
import sys
import warnings

from azure_connection import (
    DATABASE, DRIVER, SECRET_NAME, SQL_ADMIN, VAULT_NAME,
    Project2BError, build_connection_string, make_secret_client, safe_error,
)


def read_password():
    if not sys.stdin.isatty():
        raise Project2BError("TERMINAL_REQUIRED: Run this script in the VS Code terminal so the password stays hidden.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(f"Enter the existing {SQL_ADMIN} SQL password, then press Return: ")
        except getpass.GetPassWarning:
            raise Project2BError("HIDDEN_INPUT_UNAVAILABLE: Password entry was canceled; use the VS Code terminal.") from None


def validate_sql(connection_string):
    import pyodbc

    if DRIVER not in pyodbc.drivers():
        raise Project2BError("DRIVER_MISSING: Install Microsoft's ODBC Driver 18 before continuing.")
    with closing(pyodbc.connect(connection_string, timeout=30, autocommit=True)) as connection:
        connection.timeout = 30
        with closing(connection.cursor()) as cursor:
            row = cursor.execute("SELECT DB_NAME(), COUNT_BIG(*) FROM [dbo].[user];").fetchone()
    if row is None or row[0] != DATABASE:
        raise Project2BError("WRONG_DATABASE: The connection did not reach club_security_db.")
    if row[1] < 1:
        raise Project2BError("NO_USERS: The database has no users. Check Project 2A's migration first.")
    return int(row[1])


def main():
    stored = False
    try:
        password = read_password()
        connection_string = build_connection_string(password)
        del password
        print("Checking the SQL connection. Please wait...")
        count = validate_sql(connection_string)
        print(f"SQL validation passed: {DATABASE}; {count} users found.")
        print("Saving the connection secret to Key Vault. Please wait...")
        with make_secret_client() as client:
            result = client.set_secret(
                SECRET_NAME,
                connection_string,
                content_type="ODBC connection string",
            )
            stored = True
            version = result.properties.version
            if not version:
                raise Project2BError("VERSION_MISSING: The vault write returned no version; verification is incomplete.")
            check = client.get_secret(SECRET_NAME, version=version)
            if check.value is None or not hmac.compare_digest(
                check.value.encode("utf-8"), connection_string.encode("utf-8")
            ):
                raise Project2BError("SECRET_MISMATCH: The stored secret did not match; verification failed.")
        del connection_string
        print(f"Vault: {VAULT_NAME}")
        print(f"Secret: {SECRET_NAME}")
        print(f"Version: {version}")
        print("Verification passed: the stored secret matches the validated connection.")
        print("The password and connection secret were not displayed or saved in a local file.")
        print("Step 3 complete: the connection secret is stored and verified in Key Vault.")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nCanceled. No SQL data was changed.", file=sys.stderr)
        return 130
    except Exception as exc:
        print("ERROR: " + safe_error(exc), file=sys.stderr)
        if stored:
            print("A secret version was saved, but its read-back verification did not finish.", file=sys.stderr)
        else:
            print("Secret storage was not confirmed. No SQL data was changed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
