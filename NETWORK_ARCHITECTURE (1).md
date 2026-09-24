# Project 4A: Network Architecture

Resource group: `bce-zero-trust-rg`  
Documentation date: September 24, 2026

## 1. How a request reaches my database

1. My browser connects over **HTTP port 80** to public IP `20.106.109.23`, owned by `bce-appgw-pip`.
2. Application Gateway `bce-appgw` receives the request through `http-listener`. The attached `bce-waf-policy` uses Microsoft Default Rule Set 2.2 in **Prevention** mode to inspect requests.
3. Routing rule `flask-rule` sends allowed requests to `flask-backend`. Backend setting `flask-https-settings` uses **HTTPS port 443**, public CA certificate validation, and the backend App Service hostname.
4. App Service `bce-flask-app-cedric-20260917` receives the request. Its main-site access restriction allows the gateway subnet through the `Microsoft.Web` service endpoint and denies unmatched traffic.
5. When the app needs SQL data, its outbound VNet integration uses `appsvc-integration-subnet`. The linked private DNS zone, `privatelink.database.windows.net`, provides the private address for the SQL server name.
6. SQL traffic reaches private endpoint `bce-sql-pe` at **10.1.2.4**, then Azure SQL server `bce-sql-server-077b16c4c60a` and database `club_security_db`. The app continues using the server's normal `database.windows.net` hostname. SQL public network access is disabled.

My active VNet is `bce-zero-trust-vnet-westus3` in **West US 3**, with address space `10.1.0.0/16`. The SQL database remains in **Central US**; its private endpoint is in the VNet's region.

| Subnet | Address range | Purpose |
|---|---|---|
| `appgw-subnet` | `10.1.4.0/24` | Application Gateway and the Microsoft.Web service endpoint |
| `appsvc-integration-subnet` | `10.1.3.0/26` | App Service outbound integration; delegated to Microsoft.Web/serverFarms |
| `db-subnet` | `10.1.2.0/24` | SQL private endpoint at 10.1.2.4 |

I kept the old empty `app-subnet` in the original East US VNet reserved for future labs. The active database NSG is `db-subnet-nsg-westus3`, attached to the active `db-subnet`. Its priority-100 rule allows TCP 1433 from `10.1.3.0/26` to `10.1.2.0/24`. I removed the obsolete SQL rule from the East US NSG and confirmed the custom SSH rule was already absent.

## 2. Why I used a private endpoint

The private endpoint gives Azure SQL a private IP inside my VNet. Private DNS lets the app find that address without changing the normal SQL hostname. I verified that SQL public access was disabled and that a direct SQL connection from my Mac was rejected. Private networking controls the connection path; the app still needs valid database authentication and permissions.

## 3. Private endpoint versus service endpoint

| Control | What it does in my project |
|---|---|
| SQL private endpoint | Gives SQL the private address 10.1.2.4. The primary SQL server's public network access is disabled. |
| Microsoft.Web service endpoint | Lets App Service identify traffic from appgw-subnet through its public service endpoint. It does not give App Service a private endpoint IP. |

App Service VNet integration handles **outbound** app traffic toward SQL. App Service access restrictions handle **inbound** traffic from the gateway. I confirmed that the direct App Service URL returned 403 while the gateway URL still worked.

## 4. What my WAF tests proved

I compared the same three attack patterns in Detection and Prevention modes.

| Test | Detection result | Prevention result |
|---|---|---|
| SQL injection pattern | HTTP 200 | Gateway HTTP 403 |
| Cross-site scripting pattern | HTTP 302 | Gateway HTTP 403 |
| Directory traversal query parameter | HTTP 200 | Gateway HTTP 403 |

My first traversal test produced HTTP 400 in both modes, so it did not prove WAF blocking. I replaced it with `/login?file=../../etc/passwd` and confirmed the 200-to-403 change. I also signed in and created a test user successfully in Prevention mode. These results demonstrate blocking of the three tested patterns while the tested normal actions worked; they do not prove that every possible attack is blocked. The policy remains in Prevention mode.

## 5. Emergency database access: break-glass procedure

For a future lab that requires SQL administration from my Mac, I will temporarily enable SQL public access for selected networks and allow only my current public IP. I will review existing firewall allowances, complete the required work, then disable SQL public access again and verify the setting. I will record the reason, opening time, closing time, and verification result in Jira each time I use this procedure. I do not need to reopen SQL public access to stop the gateway or write this document.

For production, an approved VPN or a managed jump host reachable through Bastion would provide a private administration path. Bastion itself provides access to the jump host; it is not a direct SQL client.

## 6. Known gaps and limits

- **Browser connection uses HTTP:** The browser-to-gateway connection has no TLS certificate. Gateway-to-App Service traffic uses HTTPS, but that does not encrypt the browser's HTTP connection.
- **No gateway subnet NSG:** This is allowed for this lab. My documented plan for a standard WAF v2 gateway NSG includes inbound TCP 65200-65535 from GatewayManager, AzureLoadBalancer traffic, and the configured listener ports from the internet.
- **No Bastion or VPN administration path:** Emergency SQL access currently depends on the temporary, documented break-glass procedure.
- **Private endpoint network policies are disabled:** The database NSG is attached and its SQL rule matches the current subnet addresses, but it does not currently filter the SQL private endpoint's traffic. Default NSG rules also remain, so the SQL allow rule alone does not establish exclusive access.

## 7. Running costs, stopping, and restarting

These are **public USD retail estimates checked September 24, 2026**, not my actual invoice. The estimate assumes one Linux B1 App Service worker, one primary Basic SQL database, one SQL private endpoint, one private DNS zone, and one Standard public IPv4 address. Monthly conversions use 730 hours.

| Resource | Gateway running | Gateway stopped |
|---|---:|---:|
| WAF v2 gateway, West US 3: fixed charge | $0.36/hour | $0/hour |
| WAF v2 capacity usage | $0.0144 per billed capacity unit-hour | $0/hour |
| Standard public IPv4, West US 3 | $0.005/hour | $0.005/hour |
| SQL private endpoint | $0.01/hour | $0.01/hour |
| Private DNS zone | $0.50/month | $0.50/month |
| Linux B1 App Service, West US 3 | $0.017/hour per worker | $0.017/hour per worker |
| SQL Basic database, Central US | $0.161/day | $0.161/day |
| **Known core subtotal, before usage charges** | **About $0.3994/hour** | **About $0.0394/hour** |

For example, one hour with one billed gateway capacity unit costs about **$0.4138** for this core configuration. Stopping the gateway removes its fixed and capacity charges; the other listed resources continue costing about **$28.76 per 730 hours**, before usage charges. Minimum autoscale instances set to 0 does not remove the gateway's fixed running charge.

The complete architecture total is this core subtotal **plus other resources and usage**: private endpoint processing, DNS queries, bandwidth and any cross-region transfer, Log Analytics, Key Vault, storage, and any additional databases or App Service workers. A secondary SQL server alone does not establish that a billable secondary database exists. Taxes, credits, discounts, and actual resource usage can change my bill. I can check actual spending in Azure Cost Management, filter to `bce-zero-trust-rg`, choose the project dates, and group by Resource.

### Stop between labs

In Mac Terminal running PowerShell:

```powershell
$resourceGroupName = "bce-zero-trust-rg"
$appgw = Get-AzApplicationGateway -Name "bce-appgw" -ResourceGroupName $resourceGroupName -ErrorAction Stop
Stop-AzApplicationGateway -ApplicationGateway $appgw -ErrorAction Stop | Out-Null
Get-AzApplicationGateway -Name "bce-appgw" -ResourceGroupName $resourceGroupName -ErrorAction Stop |
    Select-Object Name, OperationalState |
    Format-Table -AutoSize
```

I wait for **Stopped** before considering shutdown verified. With the gateway stopped and direct App Service access restricted, ordinary users cannot reach the app. This is intentional between lab sessions. I keep the gateway configuration and public IP for Project 4B. Updating a stopped gateway's configuration can start it again, so I check its state after any later changes.

### Restart for Project 4B — future use only

```powershell
$resourceGroupName = "bce-zero-trust-rg"
$appgw = Get-AzApplicationGateway -Name "bce-appgw" -ResourceGroupName $resourceGroupName -ErrorAction Stop
Start-AzApplicationGateway -ApplicationGateway $appgw -ErrorAction Stop | Out-Null
Get-AzApplicationGateway -Name "bce-appgw" -ResourceGroupName $resourceGroupName -ErrorAction Stop |
    Select-Object Name, OperationalState |
    Format-Table -AutoSize
```

After restarting, I check backend health and normal app access through the gateway before testing again.

## Project reflection

I learned that identity controls and network controls do different jobs. Identity controls decide who can sign in and what they are allowed to do. Network controls decide which connection paths can reach my app and database. A harmful SQL injection request can reach a public login page before a person signs in, so identity controls alone are not enough. My WAF blocked the tested SQL injection pattern, and my access restrictions prevented direct access around the gateway. Private SQL access and stopping the gateway between labs helped me manage both exposure and cost.

## Pricing and technical sources

- [Application Gateway billing and capacity units](https://learn.microsoft.com/en-us/azure/application-gateway/understanding-pricing)
- [Application Gateway stop/start behavior](https://learn.microsoft.com/en-us/azure/application-gateway/application-gateway-faq)
- [West US 3 gateway retail rates](https://prices.azure.com/api/retail/prices?%24filter=serviceName%20eq%20%27Application%20Gateway%27%20and%20armRegionName%20eq%20%27westus3%27%20and%20productName%20eq%20%27Application%20Gateway%20WAF%20v2%27&currencyCode=USD)
- [Linux B1 retail rate](https://prices.azure.com/api/retail/prices?%24filter=meterId%20eq%20%27f8431db9-1242-59b0-816d-f3566b5b0823%27&currencyCode=USD)
- [SQL Basic retail rate](https://prices.azure.com/api/retail/prices?%24filter=meterId%20eq%20%27cae64797-9ecf-4906-b517-6238c80c045f%27&currencyCode=USD)
- [Private endpoint retail rate](https://prices.azure.com/api/retail/prices?%24filter=meterId%20eq%20%27e6ab7238-e433-4fe0-a2b2-2b2564df2cdb%27&currencyCode=USD)
- [Private DNS zone retail rate](https://prices.azure.com/api/retail/prices?%24filter=meterId%20eq%20%270b608a26-f611-4232-8192-ce81b6b57194%27&currencyCode=USD)
- [Standard public IPv4 retail rate](https://prices.azure.com/api/retail/prices?%24filter=meterId%20eq%20%279c150bf9-2bad-430e-a53c-c213804f49ef%27&currencyCode=USD)
- [Private endpoint network policies](https://learn.microsoft.com/en-us/azure/private-link/disable-private-endpoint-network-policy)
- [App Service access restrictions](https://learn.microsoft.com/en-us/azure/app-service/app-service-ip-restrictions)

