# Access Review - BCE Project 3B

Reviewer: Cedric Titus
Review date: [Enter the date]
Subscription: Azure subscription 1
Subscription ID: 384e2164-2fc0-4a70-8d96-77352d6c829b
Evidence: Portal screenshots and access_review_assignments.csv

## What I reviewed

I checked Azure role assignments in the portal and with PowerShell.
I reviewed each assignment returned by the script, including its scope.

This export covers Azure resource permissions. It does not list
Microsoft Entra administrator roles, SQL database permissions,
or roles someone is only eligible to activate through PIM.

## Assignment 1

- Holder and Object ID: [Copy from the CSV]
- Role: [Copy the role]
- Scope: [Copy the complete scope]
- Role Assignment ID: [Copy from the CSV]
- Conditions: [Record any conditions, or None]

1. Who or what holds this permission?
   [Your answer]

2. What does the role allow?
   [Your answer based on the role's permissions]

3. Why is it needed?
   [Explain the actual task it supports]

4. Could a smaller role or narrower scope work?
   [Name the alternative, or explain why the current access fits]

Decision: [Keep, recommend reducing, or investigate further]

## Manual app registration

App registration: bce-club-security-app
Purpose: Learning evidence from Project 3A.
Current application design: App Service uses its managed identity.

Decision: Keep temporarily for instructor review.
Review again: [Enter a date after grading]

Credentials and API permissions checked: [Record what you found]
Related service principal and activity checked: [Record what you found]

Before removal, confirm that no application or automation depends on it.

## My administrator access

Azure subscription roles: [Record what the export shows]
Microsoft Entra role: Global Administrator, shown in the Entra portal.

Subscription-wide access needs a written reason for this lab.
For production, I would use limited permissions for daily work
and approved, temporary elevation for administrative tasks.

## Three production improvements

1. Replace routine permanent Owner access with limited daily roles.
   Use PIM for approved, time-limited elevation when needed.

2. Keep the application's secrets in a dedicated vault and give its
   managed identity only Key Vault Secrets User on that vault.

3. Remove unused app registrations, credentials, and unnecessary
   assignments after checking dependencies. Repeat the review regularly.
   # Access Review - BCE Project 3B

Reviewer: Cedric Titus
Subscription: Azure subscription 1
Subscription ID: 384e2164-2fc0-4a70-8d96-77352d6c829b
Evidence: access_review_assignments.csv and project screenshots

## Review scope

The PowerShell export contains five Azure role-assignment records.
This report reviews each record and recommends improvements.

The CSV preserves the assignment identifiers and full scopes.
Matching display names do not prove that two records belong to
the same underlying identity.

This export covers Azure resource permissions. It does not include
all Microsoft Entra administrator roles, SQL database permissions,
or roles that are only eligible for activation through PIM.

## Assignment 1 - Owner record 1

- Who holds it?
  A user displayed as Cedric Titus.

- What does it allow?
  Management of resources and access assignments throughout the
  subscription.

- Why is it needed?
  Subscription administration and assigning access supported the
  lab setup. Permanent Owner access is broader than routine work needs.

- Could narrower access work?
  Use roles limited to the project resource group for routine work.
  Use approved, temporary administrative access when necessary.

Scope: Entire subscription.
Decision: Recommend reducing standing administrative access.

## Assignment 2 - Owner record 2

- Who holds it?
  Another assignment record displayed as Cedric Titus.

- What does it allow?
  The same subscription-wide resource and access-management powers
  provided by the Owner role.

- Why is it needed?
  A separate need for this second record has not been established.

- Could narrower access work?
  Investigate whether this represents a different identity or an
  unnecessary assignment. Retain only the access actually required.

Scope: Entire subscription.
Decision: Investigate before changing either Owner assignment.

Follow-up: Compare ObjectId, RoleAssignmentId, Scope, and Conditions
for both Owner records in the CSV. Matching names alone do not
establish that an assignment should be removed.

## Assignment 3 - Advisor Reviews Contributor

- Who holds it?
  A user displayed as Cedric Titus.

- What does it allow?
  Viewing Advisor reviews and handling associated recommendations.
  The role also includes certain deployment and alert-management
  permissions.

- Why is it needed?
  No task requiring this assignment has been identified in this lab.

- Could narrower access work?
  If only viewing reviews is required, consider Advisor Reviews Reader.
  If the role is unnecessary, recommend removing the assignment.

Scope: Key Vault bce-kv-8573.
Decision: Investigate the purpose and remove it if unnecessary.

## Assignment 4 - Key Vault Secrets Officer

- Who holds it?
  A user displayed as Cedric Titus.

- What does it allow?
  Managing secrets, including reading, creating, changing, and deleting
  them. It does not grant permission to manage role assignments.

- Why is it needed?
  Creating and managing the connection-string secrets supported
  the lab setup.

- Could narrower access work?
  If only reading secrets is needed afterward, Key Vault Secrets User
  is narrower. Temporary administrative access is another option.

Scope: Key Vault bce-kv-8573.
Decision: Review whether ongoing secret-management access is needed.

## Assignment 5 - Key Vault Secrets User

- Who holds it?
  The managed identity of bce-flask-app-cedric-20260917.

- What does it allow?
  Reading secret values and metadata in the assigned vault.

- Why is it needed?
  The application retrieves its passwordless SQL connection string
  from Key Vault.

- Could narrower access work?
  The role provides the required read access. Vault scope also permits
  reading other secrets in that vault, so a dedicated application
  vault would help limit access in production.

Scope: Key Vault bce-kv-8573.
Decision: Keep the application's read role at the vault scope required
by the lab. Do not broaden it to the resource group or subscription.

## Manual app registration

App registration: bce-club-security-app

The deployed application uses its App Service managed identity.

Decision: Retain the manual app registration temporarily as evidence
for instructor review.

Review owner: Cedric Titus.
Review trigger: After instructor grading.

Before removal, verify credentials, API permissions, the related
enterprise application, sign-in activity, and dependencies.
These checks have not been established by the role-assignment export.

## My administrator access

The export shows two subscription-scoped Owner records displayed
as Cedric Titus.

The Entra portal also showed Global Administrator. That is a separate
directory role and is not included in this Azure role-assignment export.

Production administration should use limited daily permissions and
approved, time-limited elevation when higher access is needed.

## Three production improvements

1. Reduce standing administrative access.
   Investigate both Owner records, use limited roles for daily work,
   and use Privileged Identity Management for temporary elevation
   where licensing permits.

2. Remove unnecessary access after checking dependencies.
   Investigate the Advisor Reviews Contributor assignment and review
   the manual app registration after grading. Remove unused
   assignments, identities, and credentials when confirmed unnecessary.

3. Limit the application's secret access.
   Keep its managed identity on Key Vault Secrets User and use a
   dedicated application vault so it cannot read unrelated secrets.

## Review conclusion

The application has the expected Key Vault read role.
The broad human administrative access, second Owner record, and
unexplained Advisor assignment require follow-up.

This review documents recommendations. It does not claim that all
recommended changes or follow-up investigations have been completed.