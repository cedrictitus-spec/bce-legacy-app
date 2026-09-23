# Access Review - BCE Club Security Migration
$ErrorActionPreference = "Stop"

$expectedSubscriptionId = "384e2164-2fc0-4a70-8d96-77352d6c829b"
$context = Get-AzContext

if (-not $context -or -not $context.Subscription) {
    throw "Sign in with Connect-AzAccount, then run this script again."
}

if ($context.Subscription.Id -ne $expectedSubscriptionId) {
    throw "Wrong subscription. Run: Set-AzContext -SubscriptionId $expectedSubscriptionId"
}

$subscriptionId = $context.Subscription.Id
$subscriptionScope = "/subscriptions/$subscriptionId"

$assignments = @(
    Get-AzRoleAssignment -DefaultProfile $context -ErrorAction Stop |
        Sort-Object Scope, RoleDefinitionName, DisplayName
)

Write-Host "=== ACCESS REVIEW ===" -ForegroundColor Cyan
Write-Host "Subscription: $subscriptionId"
Write-Host "Reviewed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
Write-Host "Assignments returned: $($assignments.Count)"

Write-Host "`n--- ALL ROLE ASSIGNMENTS ---" -ForegroundColor Yellow
$assignments |
    Select-Object DisplayName, ObjectType, RoleDefinitionName, Scope |
    Format-Table -AutoSize -Wrap

Write-Host "`n--- DIRECTLY SUBSCRIPTION-SCOPED ---" -ForegroundColor Yellow
$assignments |
    Where-Object { $_.Scope -eq $subscriptionScope } |
    Select-Object DisplayName, ObjectType, RoleDefinitionName |
    Format-Table -AutoSize -Wrap

Write-Host "`n--- SELECTED HIGH-PRIVILEGE ROLES ---" -ForegroundColor Red
$assignments |
    Where-Object {
        $_.RoleDefinitionName -in @(
            "Owner",
            "Contributor",
            "User Access Administrator",
            "Role Based Access Control Administrator"
        )
    } |
    Select-Object DisplayName, ObjectType, RoleDefinitionName, Scope |
    Format-Table -AutoSize -Wrap

Write-Host "`n--- SERVICE PRINCIPALS AND MANAGED IDENTITIES ---" -ForegroundColor Yellow
$assignments |
    Where-Object { $_.ObjectType -eq "ServicePrincipal" } |
    Select-Object DisplayName, RoleDefinitionName, Scope |
    Format-Table -AutoSize -Wrap

$csvPath = Join-Path $PSScriptRoot "access_review_assignments.csv"

$assignments |
    Select-Object DisplayName, SignInName, ObjectType, ObjectId,
        RoleDefinitionName, RoleDefinitionId, Scope, RoleAssignmentId,
        Condition, ConditionVersion |
    Export-Csv -Path $csvPath -NoTypeInformation -Encoding utf8

Write-Host "`nSaved: $csvPath" -ForegroundColor Green
