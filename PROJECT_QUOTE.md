# PROJECT QUOTE

**BCE Project 5A - Part 5 | September 30, 2026 | USD**

## Scope delivered

This quote covers the club-security application built in the five-week training project:

- Azure networking, Flask app hosting, and sample database migration to Azure SQL.
- Database encryption, encrypted app-to-SQL connections, managed identity, Key Vault, and limited permissions.
- Private SQL access, gateway/WAF protection, app access restrictions, logs, three alerts, and a populated dashboard.
- A restore drill, evidence exports, documentation, cost analysis, and a proposed recovery plan.

## Migration price: $2,600

**40 estimated hours x $65/hour = $2,600.** My total includes debugging, corrections, and documentation completed to date. The phase allocation is approximate; I did not time each phase separately. Additional work would add hours if required.

I chose the lower end of the instructor's $65-$95 range because this is my first full cloud project and I am still building experience.

## Monthly run cost: Scenario 1

- **Application Gateway WAF v2, continuously running: $273.31/month.**
- **All other modeled Azure services: $38.79/month.**
- **Total infrastructure: $312.10/month; $3,745.20/year.**

The WAF cost is shown separately for the client's decision. This production model keeps it running; removing it would require reviewing the security design.

**Management assumption:** 1-3 hours/month at $65 = **$65-$195/month** for limited routine reviews and administration. At 2 hours, management is $130 and the combined monthly cost is **$442.10**. This is a planning allowance, not guaranteed support coverage.

## Recommended disaster recovery

Recommend **Basic active geo-replication plus seven-day point-in-time restore**. The **$9.79/month SQL pair is already included** above. Proposed database targets: **one-hour RTO and 15-minute RPO**, requiring business approval and testing. The restore drill did not verify replication or failover.

Excluded additions: a secondary private endpoint, if needed, is **$7.32/month** (infrastructure becomes **$319.42/month**). Four-week LTR is an optional **$0.20/month** estimate: four assumed 2 GB backups at the modeled LRS rate of $0.025/GB-month. Actual backup size affects the charge.

## Three-year total cost of ownership (TCO)

**$2,600 migration + $11,235.60 infrastructure + $2,340-$7,020 management = $16,175.60-$20,855.60.** Middle estimate: **$18,515.60**. Assumes unchanged prices and usage for 36 months; excludes tax, inflation, growth, and the DR additions above.

Legacy hardware, hosting/power, maintenance, and licensing costs are **unknown: no records or quotes were supplied**. Savings and a numerical mainframe range cannot be verified. Unknown does not mean zero.

Unpriced benefits: adding modern tools, database encryption and controlled access, and an audit trail absent from the legacy scenario.

## Explicitly out of scope

- Mainframe replacement/decommissioning, license procurement, and production data conversion.
- Production go-live, frontend HTTPS/certificates, and final readiness testing.
- New features, 24/7 monitoring, incident response, or guaranteed recovery times.
- Full regional application recovery, tested failover, and optional DR deployment.
- Penetration testing, compliance certification, and management beyond the allowance.

## Basis of estimate

Sources: my 40-hour estimate; Part 3 Scenario 1 calculator evidence (September 30, East US, 730 hours/month); Part 4 DR recommendation. Actual resources span multiple regions. Annual cost = monthly quote x 12; this estimate is not an Azure invoice.
