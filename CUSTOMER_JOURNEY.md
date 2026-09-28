# BCE Club Customer Journey

**Author:** Cedric Titus  
**Trace:** `TRACE-VIP-0927`  
**Evidence reviewed:** September 28, 2026

I created the test member through the Application Gateway and traced the available records through the gateway, application, Key Vault, and database. The dashboard confirms that the member exists. The SQL audit identifies the app's managed identity and a committed transaction at the matching time, but it does **not** display the literal INSERT or the member's name. I preserve that limit rather than claim the logs show more than they do.

## 1. Eight-hop timeline

Log timestamps below are **UTC on September 28, 2026**. The signup minute, **00:26 UTC**, was **8:26 p.m. Eastern on September 27**. Hop numbers describe the architecture; the startup Key Vault request happened before the signup. Structural settings have no per-transaction timestamp.

| Hop | What happens | Evidence source | Observed time (UTC) | Security control |
|---|---|---|---|---|
| 1 | Browser connects to the public gateway. | Browser/dashboard observation; no packet-level log. | Signup observed at 00:26; exact connection time unavailable. | Untrusted edge; public listener is HTTP. |
| 2 | Gateway receives the signup; WAF checks it. | Gateway access log and matching firewall transaction ID. | Access: 00:26:24.000; WAF record: 00:27:04.837. | WAF Prevention; rule 920350 matched without blocking this signup. |
| 3 | Gateway forwards the request to the app. | `AppServiceHTTPLogs`, POST `/admin/create-user`. | 00:26:24.533. | HTTPS backend; App Service access restrictions. |
| 4 | App retrieves its connection details at startup. | Key Vault `SecretGet`, with the App Service identity. | Restart finished 00:21:48; retrieval 00:23:00.861. | Managed identity and Key Vault access permissions. |
| 5 | App reaches SQL through private networking. | Private DNS A record; SQL private client IP; external denial test. | DNS setting checked September 27; external test September 28. | Private endpoint/DNS; SQL public access disabled. |
| 6 | SQL processes a one-row operation and commits. | SQL audit, session 56; verified app identity. | One-row RPC: 00:26:24.403; commit: 00:26:24.504. | Entra managed identity; private connection; encrypted SQL connection configured. |
| 7 | Database stores data with encryption at rest. | Database TDE configuration: On / Encrypted. | Structural check September 27; no per-row encryption event. | Transparent Data Encryption (TDE). |
| 8 | Response returns and the member appears. | Gateway/app HTTP 302 and dashboard member row. | Gateway record 00:26:24.000; dashboard creation minute 00:26. | HTTPS app-to-gateway; browser leg remains HTTP. |

## 2. Evidence that connects the records

### Gateway, WAF, and application

- Test member: **TRACE-VIP-0927**, shown in the dashboard with creation time **2026-09-28 00:26**.
- My recorded client address: **108.253.215.48**.
- Signup route: **POST `/admin/create-user`**.
- Gateway response: **HTTP 302**, with **0.762 seconds** in `timeTaken_d`.
- Gateway transaction ID: **`705875f8-6cfc-af4e-a675-d6a86db9cd8b`**.
- The WAF record has that same transaction ID, client IP, and route. Its action is **Matched**, rule **920350**, message **“Host header is a numeric IP address.”** This is a rule match, not a blocked signup. The gateway/app responses and dashboard show that the request continued.
- App response: **HTTP 302**, with **698 milliseconds** in `TimeTaken`. The app's `CIp` also shows the original public client IP. It does not show a gateway-subnet address, so I do not use that field alone to prove the route.
- Earlier direct-access evidence, captured in Step 5, shows an App Service restriction result of **Denied** at **2026-09-25 20:45:40.975 UTC**, with the detail **“Denied by 0.0.0.0/0 rule.”** The earlier terminal test returned HTTP 403. These support the bypass control; they are separate tests, not part of the September 28 signup.

I correlate the gateway and WAF with their shared transaction ID. I correlate the app and SQL by the narrow time window, route, session, identity, and visible application result. No single end-to-end request ID is shown across all these sources. The WAF's later log timestamp is not a measurement of when its inspection occurred relative to the database commit. I do not subtract timestamps from different services to calculate gateway processing time.

### Startup and Key Vault

The app restart completed at **2026-09-28 00:21:48 UTC**. The successful **SecretGet** occurred at **2026-09-28T00:23:00.8613877Z**, before the member signup. Its result was **Success / OK**, and its caller IP was **20.125.64.146**.

The requested secret was **`sql-connection-passwordless`** in **`bce-kv-8573`**. The audit's managed-identity resource path identifies:

```text
/subscriptions/384e2164-2fc0-4a70-8d96-77352d6c829b/resourcegroups/bce-zero-trust-rg/providers/Microsoft.Web/sites/bce-flask-app-cedric-20260917
```

This is evidence of secret retrieval by the app's managed identity. It is a startup dependency, not a new secret retrieval for each signup. I have not included the secret's value or any access token in this document.

### SQL operation and identity

The audit records are in **`AzureDiagnostics`**, category **`SQLSecurityAuditEvents`**. The matching group uses:

| Field | Observed value |
|---|---|
| Database | `club_security_db` |
| Database user | `bce-flask-app-cedric-20260917` |
| SQL client IP | `10.1.3.62` |
| SQL session ID | `56` |
| One-row operation | `RPC COMPLETED`, affected rows `1`, at `00:26:24.403` |
| Commit | `TRANSACTION COMMIT COMPLETED` at `00:26:24.504` |
| App managed-identity object ID | `9f276e6a-dc78-428f-8d94-248f4dfd5156` |
| App managed-identity application ID | `e3efe82f-4f86-4b7d-bd85-c6561d6c76ff` |
| Tenant ID | `7baeb1ee-fc9a-45ac-8c81-0f55a5147c4b` |

The SQL login is the application ID followed by `@` and the tenant ID. I retrieved the App Service's identity and looked up its service principal; the returned **AppId matches the SQL login prefix**. This demonstrates that the audited SQL activity used the app's managed identity. The object ID and application ID are different identifiers for that same identity, so they should not be compared as though they must be identical.

The recorded client address, **10.1.3.62**, is inside the app integration subnet **10.1.3.0/26**. The SQL private endpoint is **10.1.2.4**. Those are the connection's client and destination addresses, respectively; they are not expected to match.

**Evidence limit:** The one-row RPC's displayed statement is masked-looking text beginning `*password`; it is not a readable INSERT containing `TRACE-VIP-0927`. Its timing, session, app identity, subsequent commit, and dashboard result support the correlation, but do not independently identify the exact inserted row. I do not infer why the statement is obscured. The later rollback record follows a separate read after the commit and does not by itself show that the signup was undone. Audit success flags alone are also not proof that an entire business operation succeeded.

This trace does not enumerate all SQL role memberships. I therefore do not claim that the identity has only `db_datareader` and `db_datawriter`, or that it can never perform a schema change, solely from these audit records.

### Private DNS, public-access denial, and encryption

The private DNS zone **`privatelink.database.windows.net`** contains an A record mapping **`bce-sql-server-077b16c4c60a`** to **`10.1.2.4`**. This is structural DNS evidence; it is not a log of the application's individual DNS lookup.

On September 28, I tested from my Mac outside the VNet:

- PowerShell reported **`PublicNetworkAccess : Disabled`** for the primary SQL server.
- `nslookup` resolved the normal SQL hostname through its public DNS aliases to **`20.40.228.130`**, rather than the private endpoint address.
- A single `sqlcmd` network probe using deliberately nonexistent credentials was rejected with **“Connection was denied because Deny Public Network Access is set to Yes.”** The probe did not create a user or change any Azure settings. This explicit network denial, together with the configuration result, demonstrates that this public connection was blocked.

A public DNS answer does not mean that public database access is allowed. The private DNS record, app subnet source in SQL audit, and public-access denial support the intended private database path. The database TDE page separately showed **On** and **Encrypted**. TDE protects data at rest; the earlier SQL connection configuration provides encryption in transit. Neither is a separate per-row encryption event in this trace.

## 3. The customer's journey in plain language

I acted as the club administrator and added a test member named TRACE-VIP-0927 through the club's gateway. The dashboard shows the member was created at 8:26 p.m. Eastern on September 27. To the person using the site, this was one form submission followed by a page showing the new member. The public entrance still uses HTTP, so it needs HTTPS before this lab handles real customer passwords or personal information.

The request reached the gateway, where the web application firewall checked it. One rule noticed that I used a numeric IP address instead of a website name. That rule matched, but the signup continued to the app. The matching transaction ID connects the gateway record to the firewall record, and the app recorded the same signup route. Earlier testing also showed that a direct attempt to skip the gateway was denied.

Before this signup, I restarted the application so I could observe how it retrieved its connection details. At startup, the app used its Azure-managed identity to read the passwordless connection secret from Key Vault. The vault recorded the app's exact resource name and a successful retrieval. This happened once during startup, which explains why the secret request appears a few minutes before the member was created.

The app then connected to SQL through the private network. The database recorded the app's managed identity and its private client address, along with a one-row operation followed by a commit at the signup time. I verified the identity by matching its application ID with the SQL audit login. The exact INSERT text and member name were not visible in the audit, so I explain this as a correlation supported by the dashboard, not a literal record of the member's full data. The database's encryption setting also showed that stored data was encrypted.

The application returned its response through the gateway and the new member appeared in the dashboard. The gateway recorded 0.762 seconds for the request, while the app recorded 698 milliseconds for its processing. My Mac's later attempt to connect directly to SQL was rejected because public access was disabled. After collecting the evidence, I stopped the gateway again and verified Stopped, leaving the results available for review without keeping the gateway running.

## 4. Three telemetry gaps

| Gap | What is missing | Is it acceptable, and what would I improve? |
|---|---|---|
| Browser to the internet edge | The collected Azure logs do not show the customer's connection setup before arrival at the gateway. | Acceptable as a limited lab visibility gap. Public HTTP is a separate risk that I would fix with HTTPS before using real data. Approved browser timing or client monitoring could help with troubleshooting. |
| Managed-identity token exchange | The collected logs do not expose the app's internal token acquisition. | Acceptable for this lab because the consuming Key Vault and SQL events identify the app. Production investigation may need additional identity/platform telemetry. I would never log tokens or secrets. |
| DNS lookup inside the VNet | No event records the individual DNS answer used by this app request. | Temporarily acceptable with the private A record, private SQL client address, and verified public-access denial. An app-side DNS diagnostic or suitable resolver monitoring would improve troubleshooting. |

An additional correlation limit is that the exact member INSERT and one shared request ID across all services are unavailable. I would add structured application events with a safe request ID and success/failure outcome, without logging passwords or full sensitive database statements. This would make future customer traces and incident investigations clearer.

## 5. Where an attacker has the best opportunity

The clearest weakness demonstrated in this lab is **Hop 1: the HTTP connection from the browser to the gateway**. An attacker positioned to intercept or alter that traffic could target credentials, session information, or submitted data. This depends on the attacker's network position; it does not mean any internet user can automatically read the connection.

The WAF can reject some malicious requests, App Service restrictions prevent some attempts to bypass the gateway, and SQL private access blocks direct public database connections. **None of those controls encrypts the browser's HTTP traffic.** There is currently no demonstrated control that fully stops interception on that leg. My corrective action is gateway HTTPS with a valid certificate, HTTP redirection, and secure session handling before handling real customer data. Identity and private networking remain useful protections elsewhere in the journey, but do not remove this weakness.

## 6. Evidence files and final handoff

| Evidence | Screenshot to retain |
|---|---|
| Restart with UTC time | `SideProject_Part1_Restart.png` — corrected version showing 00:21:48 |
| Created test member | `SideProject_Part2_Trace_User.png` |
| Gateway access | `SideProject_Hop2_GatewayAccess.png` |
| Matching WAF transaction | `SideProject_Hop2_WAF.png` |
| App signup request | `SideProject_Hop3_AppService.png` |
| Earlier direct-access denial | `Step5_Hunt5.png` — reuse the existing Denied result |
| Startup secret retrieval | `SideProject_Hop4_KeyVault.png` — expanded identity/secret version |
| Private DNS A record | `SideProject_Hop5_PrivateDNS.png` |
| Public SQL denial | `SideProject_Hop5_PublicAccess_Check.png` |
| SQL operation and commit | `SideProject_Hop6_SQL_Audit.png` |
| Identity-to-SQL match | `SideProject_App_Identity.png` — version showing DisplayName, Id, and AppId |
| TDE | `SideProject_Hop7_TDE.png` |
| Gateway stopped after testing | `Step9_Gateway_Stopped.png` — September 28 version |
| Completed timeline | `SideProject_Customer_Journey.png` — capture the preview after saving this revision |

The names above are the intended submission names; some original uploads have duplicate-number suffixes. The prior bypass screenshot is supplementary control evidence and has its own September 25 timestamp.

**Remaining handoff:** Save this revision and `DETECTION_AND_MONITORING.md` in the project, add `SECURITY_QUERIES.kql`, capture the timeline preview, and commit/push the updates. Attach the required evidence and repository link in the project Jira task. The SQL statement-visibility limit remains documented; I do not claim a literal named INSERT screenshot is available.

## Technical references

- [Application Gateway monitoring reference and duration units](https://learn.microsoft.com/en-us/azure/application-gateway/monitor-application-gateway-reference)
- [App Service HTTP log fields](https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/appservicehttplogs)
- [Azure SQL audit fields and their meaning](https://learn.microsoft.com/en-us/azure/azure-sql/database/audit-log-format?view=azuresql)
- [SQL public-network access and connection-denial behavior](https://learn.microsoft.com/en-us/azure/azure-sql/database/connectivity-settings?view=azuresql)
