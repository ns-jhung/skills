# Resolving a Bug ticket

Applies to Jira issue type **Bug** (issue type id `1`) in project **ENG**.

See `references/common.md` for the three resolution fields, the Resolution
Category taxonomy, the standard Resolve screen fields, the ADF `editJiraIssue`
call shape, and the Fix Version naming convention.

Bug uses the standard Resolve screen plus the fields below, and requires the
three resolution fields. Set everything in one `editJiraIssue`, then transition
once. Some of these don't appear in `getJiraIssueTypeMetaWithFields` at all — so
this list, not metadata, is the reference for what to set.

## Additional fields

| Field name | Field key | Type / allowed values |
|---|---|---|
| Resolution | `resolution` (system) | Must be `Fixed` if a PR is attached to the ticket (checked automatically). If the PR was declined instead, add label `PR-declined` and use any resolution other than `Fixed`. |
| Fix Version/s | `fixVersions` (system) | As `common.md`, and additionally cannot be `TBD` or `NA` unless the issue has label `no-code` or `no_code`. |
| Bug Classification | `customfield_16637` | select: `Feature Issue (Feature never known to have worked)` / `Regression (A previously working feature is broken)` / `SaaS App Change (Vendor application changes that results in traffic or API change)` |
| Fix Description | `customfield_12500` | text area (ADF) |
| Sub-Component | `customfield_15000` | Use **`NA`** — option id `21484`, i.e. `[{"id": "21484"}]`; if rejected, re-derive it per `references/adding-a-type.md`. The error text itself says to select `NA` when the component has no applicable sub-component, so don't hunt the list for an approximate match. |
| Where Bug should have been caught | `customfield_16643` | select: `Build` / `Requirement Review` / `Design Review` / `Code Review` / `Unit Test` / `Functional Test` / `Component Integration Test` / `Regression Test` / `E2E Integration Test` / `Solution Test` / `Scale and Performance Test` / `Pre-Prod Validation` / `Security Scans` / `Post Deployment Validation` / `CI Tool` / `Other`. Picking `Other` also requires `customfield_33598` (free-text reason). |
| Where in the Development stage did the bug get introduced | `customfield_16635` | select: `Requirement` / `Design` / `Coding` |

Not every priority enforces every field, but setting them all is harmless — so
set them all rather than trying to predict which ones this ticket needs.

## Transitioning to Resolved

The standard transition — see `references/common.md`. Bug's rejection messages
look like *"Please update the Sub-Component field…"* or *"Please enter a value
for the field \"Where bug should have been caught\"…"*.
