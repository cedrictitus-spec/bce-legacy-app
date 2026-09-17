# Club Security App: Identity Architecture

Project 3A | Jira: BCE-GOVCLOUD-005

## 1. What identity does my app have, and who created it?

My App Service, `bce-flask-app-cedric-20260917`, has a system-assigned managed identity. I turned its identity setting On, and Azure created the identity for me.

This is like an ID card for my app. Azure manages its sign-in credentials. The identity belongs to this app and is deleted if I delete the app.

## 2. How are the three identity types different?

| Item | Simple meaning | What I inspected in the portal |
|---|---|---|
| App registration | The plan that describes an application. | `bce-club-security-app` under App registrations. |
| Service principal | The application's identity inside my organization's directory. It can receive permissions. | The account opened through the registration's Managed application in local directory link. |
| Managed identity | A special service principal whose credentials Azure manages. | My web app under Enterprise applications, filtered to Managed Identities. |

My web app's managed identity is separate from the service principal for `bce-club-security-app`.

## 3. Why is managed identity safer than a stored password?

I inspected Certificates & secrets without creating a client secret. A client secret expires, and someone must replace it before it expires. Its value is shown only when it is created, so it must be stored carefully if it is used.

With managed identity, I do not copy an app password into code or settings. Azure manages and replaces the identity's credentials for me. This reduces the chance of leaking a password or forgetting to replace one.

## 4. What can the database user do?

I created the user `bce-flask-app-cedric-20260917` in `club_security_db` and assigned these roles:

- `db_datareader`: Read data from all user tables and views in this database.
- `db_datawriter`: Add, change, and delete rows in all user tables in this database.

These two roles do not give the user permission to change table structures, drop tables, create database users, or access other databases. I did not grant `db_owner`.

These are the roles required for this lab. They cover all user tables; a production app may need permissions limited to fewer tables or actions.

## 5. What still needs to be fixed?

The App Service setting `DATABASE_CONNECTION_STRING` still contains the SQL username and password. Azure encrypts app settings when storing them, but people with the required permissions can reveal the value. The standard Reader role alone cannot reveal it.

My existing Flask code from Project 2B still retrieves a password-based SQL connection string from Key Vault, `bce-kv-8573`. Turning on managed identity did not change how that code signs in.

In Project 3B, I need to update and test the app so it uses managed identity to sign into Azure SQL. Then I need to remove the password-based connection setting from App Service. The identity setup alone does not prove that the app is using passwordless sign-in.

## 6. Where would I check this setup in six months?

My resources are in `bce-zero-trust-rg`. My SQL server is `bce-sql-server-077b16c4c60a`, and my database is `club_security_db`.

| What I want to check | Where I would look in the Azure portal |
|---|---|
| My app's identity status and Object ID | App Services > `bce-flask-app-cedric-20260917` > Settings > Identity > System assigned. |
| The manual app registration | Microsoft Entra ID > App registrations > `bce-club-security-app` > Overview. |
| The manual registration's service principal | That app registration > Overview > Managed application in local directory. |
| My managed identity in the directory | Microsoft Entra ID > Enterprise applications > All applications > Application type: Managed Identities > my web app. |
| Client secrets and expiration dates | App registrations > `bce-club-security-app` > Certificates & secrets. |
| The SQL Entra administrator | SQL servers > `bce-sql-server-077b16c4c60a` > Settings > Microsoft Entra ID. |
| The database user and its roles | SQL databases > `club_security_db` > Query editor (preview). Sign in with Entra and run the Step 5 user and role checks. |
| The remaining password-based app setting | My App Service > Settings > Environment variables > App settings > `DATABASE_CONNECTION_STRING`. |
| The SQL connection secret from Project 2B | Key vaults > `bce-kv-8573` > Secrets > `database-connection-string`. |

For this lab, I used my own account as the SQL Entra administrator. In production, I would use a security group so administrator access can be managed through group membership.
