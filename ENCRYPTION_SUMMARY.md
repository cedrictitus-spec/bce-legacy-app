# Club Security Database Encryption Strategy

**Project:** BCE Project 2B — Encryption at Rest and in Transit  
**Prepared:** September 13, 2026  
**Purpose:** Document how I protect stored data, database connections, and passwords.

## My Setup

| Item | My configuration |
| --- | --- |
| Application | Local Flask app in `~/bce-legacy-app` |
| Database | `club_security_db` |
| SQL server | `bce-sql-server-077b16c4c60a.database.windows.net` |
| SQL server region | Central US |
| Resource group | `bce-zero-trust-rg` |
| Key Vault | `bce-kv-8573` |
| Connection secret | `database-connection-string` |
| SQL driver | ODBC Driver 18 for SQL Server |
| Local website | `http://127.0.0.1:5001` |
| Last confirmed user count | Four: admin, security_manager, staff, and testuser |

## At Rest: Protecting Stored Data

I enabled Transparent Data Encryption (TDE) on `club_security_db`. My PowerShell output showed `State: Enabled` and the server's encryption protector showed `Type: ServiceManaged`.

TDE encrypts the database files, transaction logs, and associated backups while they are stored. It helps protect against someone reading stolen storage without the required keys. Azure manages the TDE protector for this setup. The database connection secret in my own Key Vault is a separate item. [Microsoft: TDE](https://learn.microsoft.com/en-us/azure/azure-sql/database/transparent-data-encryption-tde-overview)

TDE allows authorized database users to read information through SQL. It does not encrypt my original local SQLite file.

## In Transit: Protecting Database Traffic

I configured the connection from Flask to Azure SQL with these settings:

| Setting | What it does |
| --- | --- |
| `Encrypt=yes` | Requires encryption for the database connection. |
| `TrustServerCertificate=no` | Checks the server certificate to help confirm the connection reaches the correct server. |
| Minimum TLS version: `1.2` | Requires TLS 1.2 or newer; the Step 7 read-back result still needs to be attached. |

Minimum TLS is a server connection setting. The SQL firewall separately controls allowed IP addresses. [Microsoft: connection settings](https://learn.microsoft.com/en-us/azure/azure-sql/database/connectivity-settings)

My browser connects to Flask over local HTTP at `127.0.0.1:5001`. This project has not added HTTPS to the website. The TLS settings above protect the connection from my app to Azure SQL.

## Application-Level Protection

### User passwords

My app uses Werkzeug's `generate_password_hash()` to create salted password hashes before saving them. It uses `check_password_hash()` during login. The migration preserved the existing hashes. Hashing is a one-way check, not reversible encryption. [Werkzeug: password helpers](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash)

### Database connection secret

I stored the connection string in Azure Key Vault as `database-connection-string`. The storage script checked the SQL connection and read back the saved secret version successfully. It displayed confirmation without displaying the password or full connection string.

My `app.py` calls `get_database_url()` from `azure_connection.py` before SQLAlchemy starts. That helper retrieves the connection string from Key Vault at startup using my Azure CLI sign-in. The database password is not hardcoded in `app.py` or supplied through an environment variable in this implementation. The app uses the retrieved password in memory to connect.

Key Vault permissions control who can read the secret. My developer account has the Key Vault Secrets Officer role scoped to this vault. SQL query echo and Flask debug mode are disabled for this lab.

## Defense in Depth: Several Protections Working Together

| Protection | Where it helps |
| --- | --- |
| Password hashing | Protects saved user passwords before they are written to SQL. |
| TLS and certificate validation | Protects information traveling from Flask to Azure SQL. |
| TDE | Protects Azure SQL files while stored. |
| Key Vault and access permissions | Protects the saved database connection secret. |
| SQL firewall and authentication | Controls network access and requires a valid database login. |

The `AllowLocalMachine` firewall rule allows one public IP address. Devices sharing that public IP also share that network allowance, but still need database credentials.

## My Verification Record

The completed items below are supported by the screenshots reviewed for this project. The final SQL-query results and minimum-TLS read-back still need to be recorded here.

- [x] Step 1: TDE showed `Enabled`; the protector showed `ServiceManaged`.
- [x] Step 2: Connection preview showed Driver 18, `Encrypt=yes`, and `TrustServerCertificate=no`, with the password hidden.
- [x] Step 3: The Key Vault connection secret was saved and its value was verified by read-back.
- [x] Step 4: Flask was configured to retrieve its database URL from Key Vault.
- [x] Step 5: Login worked and the dashboard displayed all four users.
- [x] Step 6: Attach SQL results showing `is_encrypted = 1`, `encryption_state = 3`, `encrypt_option = TRUE`, and the user list.
- [x] Step 7: Attach the server output showing `MinimalTlsVersion: 1.2`.
- [x] Step 8: Save this document in the project folder and attach its VS Code screenshot to Jira.

I will mark the remaining boxes only after checking the corresponding results. The `sqlcmd` value `encrypt_option = TRUE` describes that SQL session. To check a connection opened through Flask's configuration, the project also includes `verify_encryption.py`.

## Classroom Setup and Future Deployment

This lab uses the SQL administrator account. Before a real deployment, I would give the app a database identity with only the permissions it needs, use a managed identity to read Key Vault, replace the Flask session-key placeholder, and add website HTTPS. These are future improvements, not completed features of this project.

## Certification Alignment

My assignment connects this practice with these learning areas:

- **AZ-104:** Azure resource configuration, access control, and application connectivity.
- **AZ-500:** Data protection, secret management, TLS, and security verification.

These are learning connections, not a complete list of current exam objectives.

## What I Learned

I learned that encryption at rest protects saved information, while encryption in transit protects information traveling to my database. I learned how Key Vault keeps my database password out of my app's code. I also learned that password hashing and encryption do different jobs. I learned to save proof of my settings instead of assuming they worked.

## Step 8 Summary

I wrote down how my app and database protect information. This gives me a clear record of my settings and the checks I need to show.
