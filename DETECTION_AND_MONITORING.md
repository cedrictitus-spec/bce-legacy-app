# BCE Club: Detection and Monitoring

**Author:** Cedric Titus  
**Project:** 4B — Detection and Monitoring  
**Evidence reviewed:** September 28, 2026  
**Subscription:** Azure subscription 1  
**Resource group:** `bce-zero-trust-rg`

I collect security logs in one place, search them for suspicious activity, and use alert rules to flag events that need attention. I traced the creation of test customer `TRACE-VIP-0927` through the available logs and checked the app identity and private SQL access. After the trace, I verified `bce-appgw` was **Stopped** again on September 28. This document separates verified results from remaining evidence gaps.

## 1. Where my logs go

My central Log Analytics workspace is **`bce-security-logs` in East US**. Its verified workspace retention setting is **30 days**. The resources sending data can be in different regions from the workspace.

| Source | Enabled categories or collection | Destination and evidence |
|---|---|---|
| Application Gateway `bce-appgw` | `ApplicationGatewayAccessLog` and `ApplicationGatewayFirewallLog` | Diagnostic setting `appgw-to-logs` sends logs to `bce-security-logs`; WAF events were queried in `AzureDiagnostics`. `ApplicationGatewayPerformanceLog` was not enabled. |
| App Service `bce-flask-app-cedric-20260917` | `AppServiceHTTPLogs` and `AppServiceIPSecAuditLogs` | Both tables returned records in `bce-security-logs`: login requests and a denied direct-access attempt. |
| Key Vault `bce-kv-8573` | `AuditEvent` | A successful `SecretGet` at September 28, 00:23:00.8613877 UTC retrieved `sql-connection-passwordless`. The audit identity identifies the managed identity of `bce-flask-app-cedric-20260917`. The secret value is not included in this document. |
| Primary SQL server `bce-sql-server-077b16c4c60a` / `club_security_db` | SQL auditing to Log Analytics, with `SQLSecurityAuditEvents` enabled | `AzureDiagnostics` returned SQL events for the app database user at the signup time, including an operation affecting one row and a completed commit in session 56. The literal INSERT and customer value are not visible in the captured statement text. |
| Azure subscription activity | `Administrative` | Subscription diagnostic setting `activity-to-logs` routes events to `AzureActivity` in `bce-security-logs`. Successful tag and diagnostic-setting writes appeared. |

The secondary SQL server is separate. Its Defender auditing recommendation is not evidence that primary-server auditing is disabled. Other App Service diagnostic categories have not been established by the evidence summarized here.

## 2. My five most useful KQL queries

I run these in **bce-security-logs > Logs**. These examples use seven days so they include the September 25–28 lab evidence when run during the project; for later review I select the actual lab dates. A row records an event, not automatically a successful attack.

### Query 1 — Which requests did the WAF block?

This shows the source IP, requested path, rule, and reason for blocked WAF events.

```kql
AzureDiagnostics
| where TimeGenerated > ago(7d)
| where Category == "ApplicationGatewayFirewallLog"
| where action_s == "Blocked"
| project TimeGenerated, clientIp_s, requestUri_s, ruleId_s, Message
| sort by TimeGenerated desc
```

### Query 2 — When was the login form submitted?

This finds login POST requests, but HTTP status alone does not tell me whether a password was correct.

```kql
AppServiceHTTPLogs
| where TimeGenerated > ago(7d)
| where CsMethod == "POST"
| where CsUriStem contains "login"
| project TimeGenerated, CIp, CsUriStem, ScStatus, TimeTaken
| sort by TimeGenerated desc
```

### Query 3 — Was direct access to App Service denied?

This shows requests rejected by App Service access restrictions, including attempts to bypass the gateway.

```kql
AppServiceIPSecAuditLogs
| where TimeGenerated > ago(7d)
| where Result =~ "Denied"
| project TimeGenerated, CIp, Result, Details
| sort by TimeGenerated desc
```

### Query 4 — What activity reached Key Vault?

This shows the vault operation and outcome; I look specifically for `SecretGet` when checking secret retrieval.

```kql
AzureDiagnostics
| where TimeGenerated > ago(7d)
| where ResourceType == "VAULTS"
| project TimeGenerated, OperationName, ResultType, CallerIPAddress
| sort by TimeGenerated desc
```

### Query 5 — Who changed the Azure environment?

This shows write and delete operations, their callers, and their recorded status so I can compare them with approved work.

```kql
AzureActivity
| where TimeGenerated > ago(7d)
| where OperationNameValue contains "write"
    or OperationNameValue contains "delete"
| project TimeGenerated, Caller, OperationNameValue,
          ResourceGroup, ActivityStatusValue
| sort by TimeGenerated desc
| take 50
```

## 3. Alert rules and what I do when they fire

The three saved rules use workspace `bce-security-logs` and action group **`bce-security-alerts`**, which contains the **`security-email`** email notification. The saved overviews show the rules enabled. The intended schedule is evaluation every **5 minutes** over a **15-minute** lookback; the overview screenshots alone do not independently verify the evaluation frequency.

| Rule | Severity | What fires it | My response |
|---|---|---|---|
| WAF blocking multiple requests from single IP | 2 — Warning | Intended trigger: more than five distinct blocked gateway transactions from one IP during the last 15 minutes, returning at least one query row. The visible saved query deduplicates by client IP and transaction ID; its final threshold line is outside the screenshot, while the description states the threshold. | Check IP, paths, rule IDs, transaction IDs, and whether the traffic was my test. Investigate unexpected traffic and legitimate requests blocked by mistake; do not disable protection simply to clear the alert. |
| Key Vault access denied | 1 — Error | A vault event reports `Forbidden` or HTTP 403 during the last 15 minutes, returning at least one row. | Identify the calling identity and requested operation. Check whether a legitimate app lost its permission or an unauthorized identity attempted access; investigate before granting new access. |
| RBAC role assignment created or modified | 1 — Error | A successful `Microsoft.Authorization/roleAssignments/write` event during the last 15 minutes. | Check the caller, recipient, role, and scope against an approved change. Investigate and revoke unauthorized access through the incident process. This rule does not cover role-assignment deletion. |

The row-count condition is **Table rows, Count, greater than 0**. A WAF rule match is not always a blocked request, and a blocked request is not evidence that data was stolen.

**Test result:** Eight test requests returned HTTP 403, and a fired WAF alert was previously captured in Azure. The email address is verified, but the supplied action-group test screenshot reports an error/Unknown result. I have not verified receipt of the actual alert email. Email delivery remains an open issue; I do not claim end-to-end notification testing is complete.

## 4. Detection gaps

Naming these gaps helps me explain what my monitoring can and cannot prove.

| Gap | What I cannot prove from the current logs | Decision and next improvement |
|---|---|---|
| Application authentication outcomes | A login POST with HTTP 200 or 302 does not reliably identify a successful or failed login. | Add structured application events for success/failure, a safe user identifier, time, and request ID. Never log passwords, tokens, or connection strings. |
| Network flow logging deferred | I do not have flow records showing every allowed or denied network connection. | Deferred for this cost-controlled lab. Evaluate supported VNet flow logging and its collection, storage, and analysis costs before a production rollout. |
| Entra sign-in export unavailable in this lab | The workspace does not contain the intended Entra sign-in telemetry under the current licensing/setup. | Record this limitation and evaluate licensing and diagnostic export before relying on identity monitoring. It does not mean Entra has no sign-in records anywhere. |
| Browser to internet edge | My Azure workspace does not observe the customer's device or the full connection before it reaches the gateway. | Limited visibility is acceptable for a lab, but the HTTP listener is not acceptable for real credentials in production. Add browser-to-gateway HTTPS and, where justified, client-side monitoring. |
| Managed-identity token acquisition | Current workspace evidence does not show the app's internal token-acquisition exchange. | Accept this visibility limitation for the lab. Use Key Vault audit events to verify the consuming identity, and assess additional identity/platform telemetry for production. |
| DNS resolution inside the VNet | A private DNS A record proves configuration, not every runtime lookup by the app. | Accept temporarily for the lab with private DNS configuration and connectivity checks. Consider resolver logging or targeted app diagnostics when troubleshooting or production requirements justify it. |
| SQL statement detail and end-to-end request IDs | The trace links the signup by time, path, identity, SQL session, and the dashboard result. The captured SQL statement text does not expose the literal INSERT or `TRACE-VIP-0927`, and there is no shared request ID across every service. | Keep the correlation limits in `CUSTOMER_JOURNEY.md`. Add a safe application request ID and business-event log that links the customer action to the database operation without recording credentials or sensitive values. |
| Alert email delivery | A verified address does not establish that an alert email arrived. | Resolve the action-group test error and capture the real alert email before marking notification testing complete. |

My app's managed identity accesses **Key Vault and Azure SQL**. Its verified application ID, `e3efe82f-4f86-4b7d-bd85-c6561d6c76ff`, matches the SQL audit login prefix; its separate service-principal object ID is `9f276e6a-dc78-428f-8d94-248f4dfd5156`. SQL records the database user as `bce-flask-app-cedric-20260917` and client address as `10.1.3.62`, within the app integration subnet. This replaces the earlier draft's assumption that this app still used a SQL password.

On September 28 at about 13:19 Eastern, `Get-AzSqlServer` reported **PublicNetworkAccess: Disabled**. A lookup from my Mac returned the public address `20.40.228.130`, while the private DNS record maps the server to `10.1.2.4`. A connection attempt from my Mac using deliberately nonexistent test credentials was rejected with **"Connection was denied because Deny Public Network Access is set to Yes."** That explicit network-denial message confirms the public connection was blocked; it was not merely a wrong-password result. The private DNS record and this external check do not provide a log of the app's actual DNS lookup.

App Service's HTTP log records the original client address `108.253.215.48`, so I do not treat that field alone as proof of the network route. The private endpoint's network policies were disabled in the earlier network verification, so I do not claim the attached database NSG filters that endpoint.

### Customer trace evidence

The dashboard shows `TRACE-VIP-0927` created on **September 28, 2026 at 00:26 UTC**. The startup secret retrieval at 00:23:00.8613877 UTC happened before the signup; I do not claim the app fetched the secret again for each customer request.

| Recorded stage | Evidence | What it establishes |
|---|---|---|
| Gateway request | September 28, **00:26:24.000 UTC**; `/admin/create-user`; HTTP 302; `timeTaken` **0.762 seconds**; transaction `705875f8-6cfc-af4e-a675-d6a86db9cd8b` | The gateway handled the customer-creation request and returned a redirect. |
| WAF evaluation | Same transaction ID and path; rule **920350**; **Matched**; “Host header is a numeric IP address”; log time **00:27:04.837 UTC** | The WAF recorded a rule match for this request. Matched is not Blocked, and the later log timestamp does not mean the WAF processed the request after SQL. |
| App Service request | **00:26:24.533 UTC**; POST `/admin/create-user`; HTTP 302; **698 milliseconds** | The application handled the matching route and returned a redirect. |
| SQL operation and commit | Session **56**; one-row RPC event at **00:26:24.403 UTC**, followed by **TRANSACTION COMMIT COMPLETED at 00:26:24.504 UTC**; database user is the app and client IP is `10.1.3.62` | The session records a one-row operation and commit at the signup time. Together with the dashboard, this supports the customer trace; the visible SQL statement does not independently identify the inserted customer. |

These timestamps are recorded by different services. I use the gateway transaction ID to join gateway and WAF records, and time, path, app identity, SQL session, and the dashboard result for the other stages. I do not subtract different services' timestamps to claim an exact network delay.

## 5. Defender for Cloud triage

I reviewed **25 recommendation rows, covering 22 distinct recommendation titles**. Foundational CSPM was on and the paid Defender plans were off. Secure Score displayed **N/A**; I recorded that result instead of inventing a score. The detailed recommendation-by-recommendation answers are in my Step 8 Defender review and its exported recommendation list.

These are decisions and proposed actions, not a claim that the recommendations were remediated. Effort ranges are planning estimates.

| Finding or group | My decision and reason | Money and effort if addressed |
|---|---|---|
| Security contact, high-severity email, and owner email notifications | Agree. These are Defender notification settings, separate from my Azure Monitor action group. | No expected separate charge for changing the contact settings; about 10–20 minutes to configure and check. |
| Secondary SQL auditing and Entra administrator | Agree; assess the secondary server separately from the primary before changing it. | Configuration effort about 20–45 minutes, plus any audit-log ingestion/storage. |
| Entra-only authentication on either SQL server | The app now demonstrates managed-identity authentication to the primary SQL server. Defer enforcing Entra-only authentication until other clients and administrative access are checked and tested; the app trace does not prove all clients have migrated. | About 1–3 hours or more to review remaining clients and test access; verify any related licensing or service costs. Enabling it prematurely could break an unreviewed client. |
| Secondary SQL private endpoint and public-access removal | Agree with private access, but first confirm why the secondary is retained and what depends on it. | Private endpoint, data processing, and possibly DNS add ongoing cost; allow 30–90 minutes plus testing. |
| Key Vault private access and firewall restrictions | Agree; defer until App Service connectivity and management access can be tested safely. | Firewall configuration itself has no separate expected fee; private endpoints and related services add cost. About 30–90 minutes. |
| Key Vault deletion/purge protection | Agree for production; account for the lab's eventual teardown and retention constraints. | About 10–20 minutes to review and configure. Storage/service costs may continue during retained lifetime; protection cannot simply be switched off later. |
| Storage private access and VNet restrictions | Agree where needed; verify the account's clients before restricting them. | Private endpoints and data processing may add cost; about 30–90 minutes depending on clients. |
| Storage Shared Key authorization | Agree with migration toward identity-based access; defer disabling it until dependent clients and SAS usage are checked. | About 30–90 minutes or more to inspect and migrate dependencies; related service costs depend on the solution. |
| Paid Defender CSPM, App Service, Azure SQL, Key Vault, Resource Manager, Storage, and SQL vulnerability-assessment recommendations | Defer to comply with the professor's free-tier-only requirement. I accept the additional detection gaps for this lab; existing logs are not a substitute for every paid protection. | Recurring charges depend on the plan and resources. Review current pricing and get budget approval before enabling; allow time to configure and validate. |

I also accept the HTTP gateway listener only as a temporary lab exception. I would require HTTPS before handling real club-member credentials or personal data.

## 6. Retention: compliance and cost

My verified workspace setting is **30 days**. That supports recent lab troubleshooting and investigations without choosing a long retention period by default. Individual tables can have different retention settings or service defaults, so this is not a statement that every table deletes data on exactly day 30.

Longer retention gives investigators more history, but it can increase storage/query costs and the amount of personal information retained. For production I would agree on the required period with the business, security, and compliance owners, then set retention by log type. I have not established a specific legal retention requirement for this lab.

For Analytics tables, Microsoft includes 31 days of retention in the ingestion price; reducing retention below that allowance does not automatically save money. I would use longer-term retention only where the business need justifies the cost, restrict access to logs, and avoid collecting secrets in the first place.

## 7. Actual spending and monthly monitoring estimate

All figures below are **USD**. The latest cost screenshots were captured on **September 28, 2026**, scoped to **Azure subscription 1**, for **September 2026**, using **Actual cost**. Both requested groupings, Service name and Resource, are present. These figures are dated snapshots, not final invoices; the credit evidence remains dated September 27.

| Item | Recorded value | Evidence and meaning |
|---|---:|---|
| September month-to-date actual cost | **$40.31** | September 28 subscription-scoped Cost Analysis, visible in both views. |
| Most expensive individual resource | **bce-appgw; exact September 28 resource charge not displayed** | The resource chart identifies the gateway as the largest contributor. The last separately verified resource amount was **$23.12 on September 27**; it is not the current amount. A resource table or tooltip is needed for the latest exact charge. |
| Application Gateway service total | **$30.70** | September 28 Service name breakdown. This is a service-level total, not an independently displayed resource-level amount. |
| September month-end forecast | **$44.59** | September 28 Cost Analysis. A forecast is an estimate, not a spending cap. |
| Azure Monitor month-to-date actual | **$0.30** | September 28 Service name breakdown. It is a partial-month monitoring cost, not a full-month rate. |
| Three alert rules, full-month estimate | **$4.50/month** | Each saved rule overview estimates $1.50/month; 3 × $1.50 = $4.50. This assumes unchanged configurations. |
| Additional log ingestion/retention and other monitoring usage | **Not separately quantified from these screenshots** | Add any applicable usage charges to the alert estimate. The evidence does not support claiming these are zero. |
| Trial credit in September 27 snapshot | **$168.43** | Subscription Overview banner captured September 27; not a verified September 28 balance. |
| Credit expiry displayed | **“in 3 days”** | Shown on September 27: approximately September 30, 2026. The exact expiry date/time is not shown in this screenshot. |

My current documented **monthly monitoring estimate is $4.50 for the alert rules, plus applicable log and notification charges**. My measured Azure Monitor spend so far is $0.30. Because the rules were created recently and I have not measured a stable monthly log volume, I do not extrapolate that partial-month amount into a misleading full-month total. For a firmer estimate I will review the workspace's Usage and estimated costs and Azure Monitor/Log Analytics billing meters at the same subscription scope.

Other visible September 28 service totals are **SQL Database $5.75**, **Azure App Service $1.87**, and **Virtual Network $1.61**. The service and resource charts now meet the requested subscription scope. To finish recording the three requested headline amounts, I still need the exact current cost beside `bce-appgw` in a resource table or tooltip; I will not substitute the service card without verifying it.

**Shutdown:** After restarting the environment for the customer trace, I stopped the gateway again. PowerShell showed `bce-appgw` with operational state **Stopped** in the screenshot captured September 28 at about 13:16 Eastern; the exact stop-completion second was not recorded. Stopping the gateway stops its gateway billing, but other resources, including its separately billed public IP, may continue to incur charges. I will start the gateway only for further testing or the presentation, then stop and verify it again. The September 28 cost snapshot was captured after the shutdown check, but it is not a verified final bill for all gateway usage through shutdown.

**Credit follow-up:** I need to post the verified credit-expiry information in the class Discord. If only the relative banner is available, I will report its exact wording and capture date and label September 30 as approximate, rather than claiming an exact expiry time.

## Evidence and remaining completion checks

My planned Step 9 submission has five screenshots:

1. `Step9_Gateway_Stopped.png` — replace the earlier shutdown image with the September 28 verification after the customer trace.
2. `Step9_Cost_By_Service.png` — September 28 subscription-scoped view showing $40.31 actual cost and $44.59 forecast.
3. `Step9_Cost_by_Resource.png` — subscription-scoped resource view; use a table or tooltip that also shows the exact `bce-appgw` cost.
4. `Step9_Credit_Expiry.png` — balance and three-day expiry warning visible.
5. `Step9_Detection_And_Monitoring.png` — capture the completed document in VS Code preview.

The customer trace now has evidence for the observable application stages, with its limits recorded above and in `CUSTOMER_JOURNEY.md`. The remaining submission work is to record the exact latest `bce-appgw` resource charge, save the revised Markdown files and KQL queries in `bce-legacy-app`, capture the two document previews, commit and push the revisions, and attach the evidence and repository link in Jira. Earlier drafts were already pushed; they need these trace updates. A list of screenshot filenames is an index; it is not the monitoring documentation itself. The customer-trace side project has its own evidence requirements beyond these five Step 9 screenshots.

## Reflection

I expect a blocked web attack to leave a source IP, requested path, WAF rule, and timestamp in the gateway logs. I would use my blocked-request query to inspect those records and the WAF burst alert to flag repeated blocked requests from one IP. I would check the Key Vault access-denied alert if someone tried to read a secret without permission. I would use the role-assignment alert to investigate an unexpected grant of Azure access. I could miss repeated wrong passwords in the application because its HTTP logs do not clearly record whether each login succeeded or failed. I would close that gap by adding safe application login events and testing an alert against repeated failures.

## Break-glass log

On **September 28, 2026 at about 13:19 Eastern**, I verified that the primary SQL server's public network access was **Disabled**, and the connection test explicitly reported that public access was denied. The final check used read-only configuration and DNS commands plus a connection attempt with nonexistent test credentials; it did not change Azure configuration or enable public SQL access.

**Historical status: unknown.** On September 28, I could not confirm whether I temporarily re-enabled SQL public access earlier in the project. I therefore cannot provide reliable enable/disable times or a reason for a past exception, and I do not claim that no exception occurred. The verified current state is Disabled, with the external connection blocked. This is a gap in my change record; future emergency access changes should record the reason, approval, start time, and restoration time when they happen.

## Technical references

- [Azure Monitor costs and usage](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/cost-usage)
- [Azure Monitor pricing](https://azure.microsoft.com/en-us/pricing/details/monitor/)
- [Log Analytics data retention](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure)
- [Cost Analysis scope, views, and forecasts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/quick-acm-cost-analysis)
- [Application Gateway stop/start behavior](https://learn.microsoft.com/en-us/azure/application-gateway/application-gateway-faq)
- [Application Gateway billing components](https://learn.microsoft.com/en-us/azure/application-gateway/understanding-pricing)
