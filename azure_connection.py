"""Project 2B: get the SQL connection secret from Azure Key Vault.

Keep this file beside app.py. Use get_database_url() BEFORE SQLAlchemy(app).
Use `python3 azure_connection.py --preview` for a safe, offline screenshot.
The connection secret and the URL returned by this module must not be logged.
"""

import argparse
import re

TENANT_ID = "7baeb1ee-fc9a-45ac-8c81-0f55a5147c4b"
SUBSCRIPTION_ID = "384e2164-2fc0-4a70-8d96-77352d6c829b"
VAULT_NAME = "bce-kv-8573"
VAULT_URL = f"https://{VAULT_NAME}.vault.azure.net"
SECRET_NAME = "database-connection-string"
SERVER = "bce-sql-server-077b16c4c60a.database.windows.net"
DATABASE = "club_security_db"
SQL_ADMIN = "clubadmin"
DRIVER = "ODBC Driver 18 for SQL Server"


class Project2BError(RuntimeError):
    """Only static, safe error codes and instructions belong in this error."""


def odbc_value(value):
    """Quote one ODBC value; a closing brace inside it must be doubled."""
    if not isinstance(value, str) or "\x00" in value:
        raise Project2BError("INVALID_VALUE: A connection value is not valid text.")
    return "{" + value.replace("}", "}}") + "}"


def build_connection_string(password):
    """Return a secret ODBC string. Never print this with a real password."""
    if not isinstance(password, str) or not password:
        raise Project2BError("EMPTY_PASSWORD: Enter your existing SQL password.")
    return (
        f"Driver={odbc_value(DRIVER)};"
        f"Server={odbc_value('tcp:' + SERVER + ',1433')};"
        f"Database={odbc_value(DATABASE)};"
        f"Uid={odbc_value(SQL_ADMIN)};"
        f"Pwd={odbc_value(password)};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )


def safe_error(exc):
    """Summarize errors without including raw SDK messages or credentials."""
    if isinstance(exc, Project2BError):
        return str(exc)
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "MISSING_DEPENDENCY: Activate venv and install this project's Python packages."
    error = getattr(exc, "orig", None) or exc
    args = getattr(error, "args", ())
    state = args[0] if args and isinstance(args[0], str) else ""
    if re.fullmatch(r"[A-Z0-9]{5}", state):
        if state == "28000":
            hint = "Check the SQL administrator password."
        elif state.startswith("08") or state in ("HYT00", "HYT01"):
            hint = "Check the SQL server address, current IP firewall rule, and network."
        elif state in ("IM002", "01000"):
            hint = "Check that ODBC Driver 18 and unixODBC are installed."
        elif state.startswith("42"):
            hint = "Check the user table and SQL administrator permissions."
        else:
            hint = "Check the SQL connection setup before trying again."
        return f"SQLSTATE {state}: {hint}"
    status = getattr(error, "status_code", None)
    if status == 403:
        return "HTTP 403: Check Key Vault secret permissions and its network access rules."
    if status == 404:
        return "HTTP 404: Check the vault name and whether the connection secret exists."
    if status == 401 or type(error).__name__ in (
        "CredentialUnavailableError", "ClientAuthenticationError"
    ):
        return "AZURE_SIGN_IN: Complete the guide's az login browser sign-in, then retry."
    name = type(error).__name__
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name):
        name = "Error"
    return f"{name}: The operation failed. Share this error label, not a password or connection string."


def make_secret_client():
    from azure.identity import AzureCliCredential
    from azure.keyvault.secrets import SecretClient

    credential = AzureCliCredential(
        tenant_id=TENANT_ID,
        process_timeout=30,
    )

    return SecretClient(
        vault_url=VAULT_URL,
        credential=credential,
        connection_timeout=15,
        read_timeout=30,
        retry_total=2,
        logging_enable=False,
    )
    


def get_database_url():
    """Retrieve the secret at app startup; return an unprinted SQLAlchemy URL."""
    try:
        from sqlalchemy.engine import URL

        with make_secret_client() as client:
            secret = client.get_secret(SECRET_NAME)
        if not secret.value:
            raise Project2BError("EMPTY_SECRET: Store the connection secret before starting Flask.")
        return URL.create("mssql+pyodbc", query={"odbc_connect": secret.value})
    except Exception as exc:
        raise Project2BError(safe_error(exc)) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Show an offline example with a hidden password.")
    args = parser.parse_args()
    if not args.preview:
        parser.error("Use --preview. Flask imports get_database_url() directly.")
    print("Encrypted connection settings (offline preview):")
    print(build_connection_string("[HIDDEN]"))
    print("This is an example. No password was retrieved and no Azure connection was made.")


if __name__ == "__main__":
    main()
