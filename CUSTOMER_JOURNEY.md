# BCE Club Customer Journey

**Status: Architecture documented; named transaction trace evidence still required.**

Prepared September 27, 2026. This document describes the configuration and evidence already reviewed in my project. It does **not** claim that I have completed the required `TRACE-VIP-0927` transaction trace. I must add the real transaction evidence before treating this document as complete.

## 1. What I am tracing

The planned customer transaction is an administrator adding one new club member with the username **TRACE-VIP-0927** through the Application Gateway. I will record the exact creation time and match that event across the gateway, application, and SQL audit logs. I will separately identify the Key Vault secret retrieval around the application's restart, because the application retrieves its connection string at startup rather than for every signup.

| Project component | My configuration |
|---|---|
| Resource group | `bce-zero-trust-rg` |
| Public entry point | `http://20.106.109.23`, Application Gateway `bce-appgw` |
| Web application firewall | `bce-waf-policy`, Prevention mode |
| Application | `bce-flask-app-cedric-20260917` |
| Key Vault | `bce-kv-8573`; secret `database-connection-string` |
| Database | `club_security_db` on `bce-sql-server-077b16c4c60a` |
| Active virtual network | `bce-zero-trust-vnet-westus3`, `10.1.0.0/16` |
| Gateway subnet | `appgw-subnet`, `10.1.4.0/24` |
| Application integration subnet | `appsvc-integration-subnet`, `10.1.3.0/26` |
| SQL private endpoint | `bce-sql-pe`, `10.1.2.4`, in `db-subnet` (`10.1.2.0/24`) |
| Central log workspace | `bce-security-logs` |

## 2. Eight-hop timeline

The entries below distinguish the known route from missing evidence for this specific transaction. **“Not captured” is an outstanding task, not a timestamp.** I will use UTC for collected log timestamps and record the time zone of my browser test.

| Hop | What happens | Log or other evidence | Timestamp for the named trace | Security control and evidence limit |
|---|---|---|---|---|
| 1 | The browser connects to the gateway's public IP over HTTP port 80. | No collected browser-to-edge telemetry. | Not available in collected telemetry; record the browser test time separately. | This is an untrusted connection and currently has no browser-to-gateway TLS. |
| 2 | Application Gateway receives the request and the WAF evaluates it before forwarding allowed traffic. | `AzureDiagnostics`, category `ApplicationGatewayAccessLog`; correlate relevant firewall records in `ApplicationGatewayFirewallLog` if present. | Not captured — record the matching signup POST timestamp. | WAF Prevention mode is configured. Existing blocked-attack records do not establish what happened to this signup. A normal request need not create a firewall rule event. |
| 3 | The gateway forwards the allowed request over HTTPS port 443 to the Flask application. | `AppServiceHTTPLogs`; record the matching route, method, status, and timestamp. | Not captured — match the signup request to Hop 2. | App Service access restrictions allow the gateway subnet through the `Microsoft.Web` service endpoint. Existing direct-access denial evidence supports that control, but does not identify this transaction. |
| 4 | At application startup, the app uses its managed identity to retrieve the database connection string from Key Vault. | A successful `SecretGet` event in Key Vault audit logs, including the caller identity, around the restart time. | Not captured — collect the restart time and matching `SecretGet` timestamp separately from the signup. | Managed identity and Key Vault permissions protect secret retrieval. The previously reviewed `VaultGet` event does not prove a secret was retrieved. The token exchange itself is not in the collected logs. |
| 5 | Private DNS resolves the SQL server hostname to the SQL private endpoint. | Private DNS A record for the SQL server and its VNet link; the configured address is `10.1.2.4`. | No per-lookup timestamp in the collected telemetry; record when the configuration evidence was checked. | Private DNS, App Service outbound VNet integration, the SQL private endpoint, and disabled SQL public access support the private route. Configuration alone does not record this particular DNS lookup. |
| 6 | The app sends the member's database write through the private endpoint over the encrypted SQL connection. | SQL audit event containing the matching INSERT and actual principal, result, and client address. | Not captured — record the matching SQL audit timestamp. | My documented app uses SQL credentials from Key Vault. I must report the principal shown in the audit event, not assume that SQL used the app's managed identity. |
| 7 | Azure SQL stores the data with Transparent Data Encryption (TDE) enabled. | SQL database TDE setting; retain the configuration screenshot. | No separate per-row TDE event; record the configuration check time. | TDE protects stored database data. A TDE setting is structural evidence, not a timestamp proving this member was inserted. |
| 8 | The app returns the result through the gateway and the browser displays the member. | Screenshot of the member in the dashboard, correlated with the gateway and app response records. | Not captured — record the observed result and matching response evidence. | The return path uses HTTPS between app and gateway, but the gateway-to-browser leg remains HTTP. An HTTP success code alone does not prove that the database write succeeded. |

## 3. The journey in plain language

In this planned test, I act as the club administrator and add a member named TRACE-VIP-0927. I open the club application through the gateway's public address, sign in, and submit the new member form. I record the time so I can find the same action in the logs. The first connection is currently plain HTTP, which means this lab still needs HTTPS on its public entrance before it is suitable for real customer information.

The request first reaches the web application firewall, which checks traffic for patterns associated with attacks. Allowed traffic continues to the application over HTTPS. The application's access restrictions are intended to prevent someone from skipping the gateway and visiting the application directly. My earlier tests recorded blocked attack patterns and a denied direct-access attempt, but I still need to collect the records for this particular member signup.

The application also needs permission to retrieve its database connection details. At startup, it uses its Azure-managed identity to request the connection string from Key Vault. This avoids placing the connection string directly in the application's settings or source code, but the connection string still contains SQL credentials in my current implementation. I need a successful SecretGet event showing the caller to demonstrate that retrieval; it may occur before the member signs up because the app keeps the connection details after startup.

When the application writes the member record, private DNS helps it find the database's private address, 10.1.2.4. The application's network integration provides the route to the SQL private endpoint, and public database access is disabled. The SQL connection is encrypted, and TDE protects the stored database data. The audit log must show the actual database principal and write result; I cannot substitute an assumption that the application used managed identity for SQL authentication.

Finally, the application sends the result back through the gateway and the new member should appear in the dashboard. I will connect that visible result to the matching gateway, app, and SQL evidence using the recorded time, request details, and the distinctive member name where it appears. These are separate records, so matching timestamps alone will not prove a complete transaction. Until I collect and compare them, this document is an architecture description and a prepared trace record rather than a completed customer trace.

## 4. Three telemetry gaps

| Gap | What I cannot currently see | Is this acceptable? | What I would improve |
|---|---|---|---|
| Browser to the internet edge | My Azure logs do not show the browser's connection setup or everything that happens before the request reaches the gateway. | Temporarily acceptable as a visibility limit in a controlled lab. The separate lack of public HTTPS is not acceptable for real passwords or customer data. | Add HTTPS with a valid certificate at the gateway and redirect HTTP. Use approved browser timing or client monitoring when troubleshooting requires it, without collecting passwords. |
| Managed-identity token exchange | The collected logs do not expose the app's internal token acquisition exchange. | Acceptable for this lab if I can verify the app identity, its permissions, and successful or denied access at Key Vault. I still need the specific SecretGet evidence for this trace. | Review available identity and application diagnostics, record safe token-acquisition success/failure metadata if needed, and correlate it with Key Vault audit events. Never log access tokens or secrets. |
| DNS resolution inside the VNet | The collected logs have no per-request record proving which DNS answer the app used. | Temporarily acceptable for this small lab when the private DNS record, VNet link, private connectivity, and disabled public SQL access are verified. It limits diagnosis of DNS failures. | Add a documented DNS lookup from the application environment and evaluate suitable DNS monitoring before enabling additional paid services. |

## 5. Where an attacker has the best opportunity

The clearest demonstrated weakness in my current configuration is **Hop 1, the browser-to-gateway HTTP connection**. An attacker able to intercept or alter that connection could target credentials, session information, or submitted data. This opportunity depends on their network position; it does not mean every internet user can read the traffic.

The WAF at Hop 2 can reject some malicious request patterns, and the app restrictions make a direct gateway bypass harder. **Neither control encrypts the HTTP connection or makes stolen credentials safe.** My main corrective action is to configure HTTPS on the gateway with a valid certificate and redirect HTTP, then verify secure session handling. The private SQL endpoint and Key Vault permissions protect other parts of the journey but do not repair the exposed browser connection.

## 6. Interpretation limits I will preserve

- Managed identity is documented for **Key Vault access**. My current database connection uses **SQL credentials from the vault**; a passwordless SQL identity has not been demonstrated.
- Existing App Service HTTP results showed a public client address in `CIp`. I will record the actual value and will not require a gateway-private address or use that field alone as proof of the route.
- I will not subtract raw timestamps from different services and label the difference “gateway processing time.” Event timing and logging behavior differ. I will use documented duration fields and preserve their units.
- The signup name may not appear in gateway or app access logs because a form body is not necessarily recorded. Parameterized SQL may also omit literal values. I will correlate the available fields and state any remaining uncertainty.
- A missing WAF rule event does not by itself prove that a normal request was allowed. I will use the corresponding gateway/app records and the application result.
- Prior attack screenshots, a successful `VaultGet`, or a successful login are not evidence of the required named signup transaction.

## 7. What remains before I call this complete

1. Record the application restart time and the exact time the named member is created through the gateway; save the dashboard confirmation.
2. Collect the matching gateway access and app HTTP results. Collect relevant WAF events if any, and explain if the normal request produced none.
3. Collect a successful Key Vault **SecretGet** event with its actual caller identity around startup.
4. Collect the SQL audit record for the member write, preserving the actual principal, timestamp, result, and any correlation limit.
5. Save the private DNS A record and TDE configuration evidence, then replace the missing transaction timestamps in the timeline with the observed values.
6. Review the narrative against the collected results, screenshot the completed timeline, and commit this file with `DETECTION_AND_MONITORING.md`. If the gateway was restarted for the trace, stop it again and verify **Stopped**.

**Completion statement withheld:** I have documented the known architecture and visibility limits. I will report the end-to-end trace as complete only after adding the required transaction evidence.
