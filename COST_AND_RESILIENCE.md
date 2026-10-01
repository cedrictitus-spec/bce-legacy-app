# COST AND RESILIENCE

**BCE Project 5A - Part 6 | October 1, 2026 | USD**

This document combines my cost model, recovery test, and recommendations. Prices are estimates; tested results and unverified items are identified below. Subscription IDs, resource IDs, addresses, and credentials are omitted from this public document.

## 1. Cost model: all three scenarios

These figures come from my saved September 30 Azure Pricing Calculator estimates. The comparison uses East US pricing, 730 hours for a full month, Basic SQL, and the same small lab workload. Actual deployed resources span multiple regions, so this is a normalized comparison, not my invoice.

| Monthly line item | 1: Gateway always on | 2: Gateway for 40 lab hours | 3: No gateway or its public IP |
|---|---:|---:|---:|
| Application Gateway WAF v2 | $273.31 | $14.98 | $0.00 |
| App Service B1 Linux | $12.41 | $12.41 | $12.41 |
| Two Azure SQL Basic databases | $9.79 | $9.79 | $9.79 |
| One private endpoint with modeled traffic | $7.32 | $7.32 | $7.32 |
| Standard public IP | $3.65 | $3.65 | $0.00 |
| Private DNS | $0.50 | $0.50 | $0.50 |
| Key Vault | $0.03 | $0.03 | $0.03 |
| Storage | $0.13 | $0.13 | $0.13 |
| Azure Monitor | $4.95 | $4.95 | $4.95 |
| **Calculator monthly total** | **$312.10** | **$53.76** | **$35.14** |
| **Annual: monthly total x 12** | **$3,745.20** | **$645.12** | **$421.68** |

Totals use calculator precision; rounded service rows can differ from the total by $0.01. Annual figures consistently use the displayed monthly total x 12. Scenario 2's 40 gateway hours are a runtime assumption, separate from my 40 estimated labor hours.

The gateway model uses one capacity unit. Monitor includes $4.50 for three five-minute log alerts plus a $0.45 time-series allowance; this is a pricing assumption, not measured alert billing. Log ingestion assumes about 3 GB/month within the shared 5 GB allowance, with no extra retention charge. Other small-operation and storage assumptions match Part 3. Growth can increase these costs.

Scenario 2 saves **$258.34/month** versus continuous operation and suits the lab. The app's gateway entry point is unavailable while stopped. Scenario 3 saves **$276.96/month**, but removing the gateway also requires reviewing app access restrictions and replacing or accepting the lost request inspection. It is not the production recommendation.

## 2. WAF justification

I recommend keeping the WAF gateway running continuously for a live club. Its modeled cost is **$273.31/month or $3,279.72/year**, and it inspects web requests before they reach the application. My lab produced blocked-request evidence, but that does not prove every attack will be stopped. The club handles member information, so an incident could damage both operations and trust. That makes the expense reasonable for production, subject to the client's budget approval.

This price covers the gateway and modeled WAF capacity together; it is not a separately measured WAF license premium. A WAF does not replace secure code, access controls, encryption, or backups. For my lab, stopping the gateway between sessions is the cost-saving choice. Frontend HTTPS/certificate work and a production go-live remain outside the completed lab scope, as stated in PROJECT_QUOTE.md.

## 3. Right-sizing recommendations

| Resource | Recommendation and reason | Monthly figure / savings |
|---|---|---|
| App Service plan | Keep one Linux B1 instance. It supports the VNet integration used for private SQL access; Free/Shared would not preserve that feature. No evidence justifies a larger tier. | Keep **$12.41**; **$0** immediate savings. |
| Standard public IP | Keep the stable IP while the gateway will be restarted for demonstrations. Release it only if the gateway is permanently removed and the address is no longer needed. | Keep **$3.65**; permanent release saves **$3.65**. Stopping alone does not release it. |
| Azure SQL | Keep Basic, with 5 DTUs and 2 GB per database, for the small lab workload. Keep the second Basic database in the proposed DR budget; its replication still needs verification. | Two databases **$9.79**; **$0** immediate savings. |
| Log Analytics retention | Keep the observed 30-day workspace setting, within the included 31-day Analytics Logs retention period. No longer retention requirement was supplied. | **$0** extra retention in this model; **$0** immediate savings. The $4.95 Monitor allowance remains. |

These are cost decisions, not claims that every resource can be made cheaper without losing a required feature.

## 4. DR analysis and recommendation

Disaster recovery (DR) has different costs depending on how quickly the database must return:

| Option on Basic SQL | Modeled cost | Main tradeoff |
|---|---|---|
| Seven-day point-in-time restore (PITR) | $0 extra backup storage | Restores earlier data after deletion or bad changes; restore duration varies. |
| Long-term retention (LTR) | $0.025/GB-month at the modeled LRS rate | Older full backups; four assumed 2 GB weekly copies cost $0.20/month. |
| Geo-redundant backup / geo-restore | $0 extra PITR storage in DTU pricing; the restored database is billed | Requires GRS/GZRS backups. Recovery and potential data loss can be minutes to hours. Actual backup redundancy was not verified. |
| Active geo-replication | About $4.90 for a second Basic database; $9.79 for the pair | A ready replica offers faster DB recovery. Forced failover can lose changes not yet replicated. |
| Auto-failover group | Same second-database cost; no separate replication-transfer fee | Microsoft-managed automatic failover has at least a one-hour grace period plus response time. |

All five options are available on Basic; none requires an upgrade just to use it. Basic PITR is limited to seven days. Longer PITR retention requires a higher tier, while LTR provides older full backups instead.

I recommend **Basic active geo-replication plus seven-day PITR**. The **$9.79 SQL pair is already included** in Scenario 1. Microsoft documents database failover typically under 60 seconds for active geo-replication/customer-managed failover, but detecting the outage, reconnecting the app, and checking data add time. The existing second database is not proof that replication or failover works; that recovery path remains unverified.

For private access, a secondary endpoint, if needed, adds **$7.32/month**, bringing Scenario 1 infrastructure to **$319.42/month**. Network, DNS, authentication, and app recovery must also work. This is a database proposal, not proven recovery of the whole application across regions.

The accepted lab gap is a bad change discovered after seven days. Replication can copy bad changes, and the PITR history eventually expires. Four-week LTR could add older recovery points for approximately **$0.20/month** under the size assumption above. Actual storage determines the charge. This extends historical recovery, not a 15-minute RPO across all four weeks. A live club must approve its required history. Both optional additions are excluded from the base TCO.

## 5. RTO and RPO with business reasoning

- **RTO: one hour proposed.** RTO is how long the club can tolerate being down. A four-hour outage on a busy night could stop member check-in and lose business, so I propose restoring database service within one hour.
- **RPO: 15 minutes proposed.** RPO is how much recent data the club can tolerate losing. Fifteen minutes limits how much recent information staff might need to reconstruct.

These are proposed database targets for the club to approve and for a recovery test to validate. They are not an agreed SLA or a guarantee from the restore drill.

## 6. Measured versus documented restore time

| Measure | Documentation / expectation | My September 29 test |
|---|---|---|
| Database restore | No fixed Basic duration. Size, activity, and restore demand matter; large or busy databases can take several hours. | **6 minutes 26 seconds**, timed with my stopwatch. |
| Restore plus data check | Database restore guidance does not include all navigation, checks, and application recovery. | **About 17-18 minutes**, from 11:20:12 a.m. EDT to roughly 11:37-11:38 a.m. EDT. |
| Recovery point | Log backups run approximately every 10 minutes; that is not a guaranteed business RPO. | I chose **September 29, 14:12 UTC / 10:12 a.m. EDT**. This selected older point does not measure backup lag or actual data loss. |

The original database and restored copy each showed **7 rows in dbo.user**. I deleted the test copy afterward. Matching counts are not proof that every stored value matched. The 17-18 minute figure includes navigation and is approximate because I stopped the stopwatch after the restore. I did not switch the live app to the restored copy or test regional failover. The small lab restore was faster than the hours larger restores can require, but it does not establish a full application RTO or RPO.

## 7. Three-year TCO

My migration quote is **40 estimated hours x $65/hour = $2,600**, including debugging, corrections, and documentation completed to date. The rate is the lower end of the instructor's range because I am still building experience. The phase allocation in Part 5 is approximate; I did not time each phase separately.

| Three-year cost | Low: 1 management hour/month | Middle: 2 hours/month | High: 3 hours/month |
|---|---:|---:|---:|
| Migration labor | $2,600.00 | $2,600.00 | $2,600.00 |
| Scenario 1 infrastructure: $312.10 x 36 | $11,235.60 | $11,235.60 | $11,235.60 |
| Routine management at $65/hour | $2,340.00 | $4,680.00 | $7,020.00 |
| **Total** | **$16,175.60** | **$18,515.60** | **$20,855.60** |

Management is a planning allowance for limited routine administration, not 24/7 support or measured staffing. Prices and usage are held constant for 36 months. Taxes, inflation, growth, optional DR additions, and work beyond the quote are excluded.

No mainframe hardware, hosting/power, specialist maintenance, or licensing records were supplied. Those costs remain **unknown, not zero**, so I cannot claim a verified mainframe total, numerical range, or savings. The comparison requires: hardware refresh within the period + 36 x monthly hosting/power + 3 x annual maintenance + 3 x annual licensing. At the middle estimate, Azure is cheaper only if the comparable legacy cost exceeds **$18,515.60**.

Value outside both cost columns includes the ability to add modern tools, database encryption and controlled access, and an audit trail absent from the legacy scenario. I have not invented dollar values for those benefits or the legacy system's inability to add capability.

## 8. Subscription upgrade decision

I upgraded to pay-as-you-go so the environment would remain available after the trial credit expired. That let me finish checking controls, preserve evidence, and keep the environment for the presentation. The upgrade avoided losing access before the project was documented; it did not make future usage free.

I saved a **$25 monthly budget** with email alerts at **50%, 80%, and 100%**. These thresholds correspond to $12.50, $20, and $25. A budget sends warnings; it is not an automatic spending cap. Even the approximately **$38.79/month** modeled baseline with the gateway stopped is above that alert budget for a full month.

The shutdown screenshot confirms the gateway was **Stopped on October 1 at approximately 11:54 a.m. EDT / 15:54 UTC**. This is the verification time, not an exact stopwatch measurement of shutdown. Stopping it controls gateway cost while other resources, including the retained public IP, can keep billing. The production quote still uses continuous WAF operation; the lab shutdown does not change that assumption.

## Evidence and references

Evidence: saved Part 3 calculator screenshots; Part 4 restore notes and DR analysis; Part 5 quote; subscription upgrade/budget screenshots; and the October 1 gateway-stop screenshot. Portal screenshots and billing exports containing identifiers are retained in the project evidence archive rather than embedded here.

- [App Service VNet integration requirements](https://learn.microsoft.com/en-us/azure/app-service/overview-vnet-integration)
- [Azure Monitor pricing](https://azure.microsoft.com/en-us/pricing/details/monitor/)
- [SQL DTU tiers and Basic limits](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-dtu)
- [Automated SQL backups and costs](https://learn.microsoft.com/en-us/azure/azure-sql/database/automated-backups-overview)
- [SQL restore timing](https://learn.microsoft.com/en-us/azure/azure-sql/database/recovery-using-backups)
- [SQL business continuity and recovery targets](https://learn.microsoft.com/en-us/azure/azure-sql/database/business-continuity-high-availability-disaster-recover-hadr-overview)
- [Failover group policies](https://learn.microsoft.com/en-us/azure/azure-sql/database/failover-group-sql-db)
- [SQL database and replication pricing](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/)
- [Azure budgets and alerts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)
