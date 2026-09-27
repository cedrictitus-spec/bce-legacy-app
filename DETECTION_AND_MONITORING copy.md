# BCE Club: Detection and Monitoring

**Author:** Cedric Titus  
**Project:** 4B — Detection and Monitoring  
**Evidence reviewed:** September 27, 2026  
**Subscription:** Azure subscription 1  
**Resource group:** `bce-zero-trust-rg`

I collect security logs in one place, search them for suspicious activity, and use alert rules to flag events that need attention. I stopped `bce-appgw` after testing and verified that its operational state was **Stopped**. This document separates verified results from remaining evidence gaps.

## 1. Where my logs go

My central Log Analytics workspace is **`bce-security-logs` in East US**. Its verified workspace retention setting is **30 days**. The resources sending data can be in different regions from the workspace.

| Source | Enabled categories or collection | Destination and evidence |
|---|---|---|
| Application Gateway `bce-appgw` | `ApplicationGatewayAccessLog` and `ApplicationGatewayFirewallLog` | Diagnostic setting `appgw-to-logs` sends logs to `bce-security-logs`; WAF events were queried in `AzureDiagnostics`. `ApplicationGatewayPerformanceLog` was not enabled. |
| App Service `bce-flask-app-cedric-20260917` | `AppServiceHTTPLogs` and `AppServiceIPSecAuditLogs` | Both tables returned records in `bce-security-logs`: login requests and a denied direct-access attempt. |
| Key Vault `bce-kv-8573` | `AuditEvent` | Key Vault events appeared in `AzureDiagnostics` in the central workspace. The captured `VaultGet` success demonstrates vault activity; it does not prove a secret retrieval. |
| Primary SQL server `bce-sql-server-077b16c4c60a` / `club_security_db` | SQL auditing to Log Analytics, with `SQLSecurityAuditEvents` enabled | PowerShell confirmed auditing was enabled and directed to `bce-security-logs`. This configuration check alone does not prove a particular INSERT was captured. |
| Azure subscription activity | `Administrative` | Subscription diagnostic setting `activity-to-logs` routes events to `AzureActivity` in `bce-security-logs`. Successful tag and diagnostic-setting writes appeared. |

The secondary SQL server is separate. Its Defender auditing recommendation is not evidence that primary-server auditing is disabled. Other App Service diagnostic categories have not been established by the evidence summarized here.

## 2. My five most useful KQL queries

I run these in **bce-security-logs > Logs**. These examples use seven days so they include the September 25–27 lab evidence when run during the project; for later review I select the actual lab dates. A row records an event, not automatically a successful attack.

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
| Missing named customer trace | I do not yet have a correlated gateway POST, App Service POST, startup SecretGet, and SQL audit event proving `TRACE-VIP-0927` across the observable stages. | Complete the evidence table in `CUSTOMER_JOURNEY.md` using real results. Do not reuse unrelated hunt timestamps as if they were one transaction. |
| Alert email delivery | A verified address does not establish that an alert email arrived. | Resolve the action-group test error and capture the real alert email before marking notification testing complete. |

My app's managed identity accesses **Key Vault**. The documented database connection still uses **SQL credentials stored in that vault**; I have not demonstrated passwordless managed-identity authentication to SQL. App Service's logged client IP may be the original caller, so I do not treat that field alone as proof of the network route. The private endpoint's network policies were disabled in the earlier network verification, so I do not claim the attached database NSG filters that endpoint.

## 5. Defender for Cloud triage

I reviewed **25 recommendation rows, covering 22 distinct recommendation titles**. Foundational CSPM was on and the paid Defender plans were off. Secure Score displayed **N/A**; I recorded that result instead of inventing a score. The detailed recommendation-by-recommendation answers are in my Step 8 Defender review and its exported recommendation list.

These are decisions and proposed actions, not a claim that the recommendations were remediated. Effort ranges are planning estimates.

| Finding or group | My decision and reason | Money and effort if addressed |
|---|---|---|
| Security contact, high-severity email, and owner email notifications | Agree. These are Defender notification settings, separate from my Azure Monitor action group. | No expected separate charge for changing the contact settings; about 10–20 minutes to configure and check. |
| Secondary SQL auditing and Entra administrator | Agree; assess the secondary server separately from the primary before changing it. | Configuration effort about 20–45 minutes, plus any audit-log ingestion/storage. |
| Entra-only authentication on either SQL server | Defer until clients and administrative access have been migrated and tested. The app still depends on SQL credentials. | About 1–3 hours or more for migration/testing; verify any related licensing or service costs. Enabling it prematurely could break access. |
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

All figures below are **USD**, read from the September 27, 2026 screenshots. They are a dated snapshot, not final invoices.

| Item | Recorded value | Evidence and meaning |
|---|---:|---|
| September month-to-date actual cost | **$31.57** | Azure subscription 1 Overview; also matches the supplied Cost Analysis total. |
| Most expensive individual resource | **bce-appgw — $23.12** | Subscription Overview, Costs by resource. |
| September month-end forecast | **$35.80** | Subscription Overview and Cost Analysis. A forecast is an estimate, not a spending cap. |
| Azure Monitor month-to-date actual | **$0.16** | Service breakdown in supplied Cost Analysis. It is a partial-month monitoring cost, not a full-month rate. |
| Three alert rules, full-month estimate | **$4.50/month** | Each saved rule overview estimates $1.50/month; 3 × $1.50 = $4.50. This assumes unchanged configurations. |
| Additional log ingestion/retention and other monitoring usage | **Not separately quantified from these screenshots** | Add any applicable usage charges to the alert estimate. The evidence does not support claiming these are zero. |
| Remaining trial credit | **$168.43** | Subscription Overview banner. |
| Credit expiry displayed | **“in 3 days”** | Shown on September 27: approximately September 30, 2026. The exact expiry date/time is not shown in this screenshot. |

My current documented **monthly monitoring estimate is $4.50 for the alert rules, plus applicable log and notification charges**. My measured monitoring spend so far is $0.16. Because the rules were created recently and I have not measured a stable monthly log volume, I do not extrapolate that partial-month amount into a misleading full-month total. For a firmer estimate I will review the workspace's Usage and estimated costs and Azure Monitor/Log Analytics billing meters at the same subscription scope.

The service chart lists Application Gateway at $23.11 while the subscription resource card lists `bce-appgw` at $23.12. I use the resource card for the most-expensive-resource figure and preserve the displayed values rather than silently changing one.

**Evidence correction still needed:** The supplied cost charts are scoped to the billing account “Cedric Titus.” The professor asked for subscription scope. I need to replace the two charts with September actual-cost views scoped to **Azure subscription 1**, grouped first by Service name and then by Resource. The subscription Overview already supports the three headline figures above.

**Shutdown:** PowerShell returned `bce-appgw`, `bce-zero-trust-rg`, **Stopped**. Stopping the gateway stops its gateway billing, but other resources, including its separately billed public IP, may continue to incur charges. I will start the gateway only for further testing or the presentation, then stop and verify it again.

**Credit follow-up:** I need to post the verified credit-expiry information in the class Discord. If only the relative banner is available, I will report its exact wording and capture date and label September 30 as approximate, rather than claiming an exact expiry time.

## Evidence and remaining completion checks

My planned Step 9 submission has five screenshots:

1. `Step9_Gateway_Stopped.png` — verified Stopped.
2. `Step9_Cost_By_Service.png` — replace with subscription-scoped view.
3. `Step9_Cost_by_Resource.png` — replace with subscription-scoped view.
4. `Step9_Credit_Expiry.png` — balance and three-day expiry warning visible.
5. `Step9_Detection_And_Monitoring.png` — capture the completed document in VS Code preview.

I still need to complete the real transaction timeline in `CUSTOMER_JOURNEY.md`, save both Markdown files in `bce-legacy-app`, commit and push those two files, and attach the evidence/repository link in Jira. A list of screenshot filenames is an index; it is not the monitoring documentation itself. The customer-trace side project has its own evidence requirements beyond these five Step 9 screenshots.

## Technical references

- [Azure Monitor costs and usage](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/cost-usage)
- [Azure Monitor pricing](https://azure.microsoft.com/en-us/pricing/details/monitor/)
- [Log Analytics data retention](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure)
- [Cost Analysis scope, views, and forecasts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/quick-acm-cost-analysis)
- [Application Gateway stop/start behavior](https://learn.microsoft.com/en-us/azure/application-gateway/application-gateway-faq)
- [Application Gateway billing components](https://learn.microsoft.com/en-us/azure/application-gateway/understanding-pricing)
