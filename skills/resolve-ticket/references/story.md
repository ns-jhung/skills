# Resolving a Story ticket

Applies to Jira issue type **Story** (issue type id `7`) in project **ENG**.

Uses the standard Resolve screen — see `references/common.md` for those fields,
the transition, the ADF `editJiraIssue` call shape, and the Fix Version naming
convention.

**Story does not use the three resolution fields** from `common.md` — no Root
Cause Analysis, no Solution Provided, no cascading Resolution Category. Ignore
that taxonomy for this type; Story has its own flat **Resolution Categories**
field, listed below. Setting the Escalation/Bug fields on a Story writes fields
that aren't on the screen and won't satisfy the transition.

## Required fields

The standard Resolve screen fields are all enforced here, with these additions
and overrides. Set everything in one `editJiraIssue`, then transition once.

| Field name | Field key | Type / allowed values |
|---|---|---|
| Resolution | `resolution` (system) | select: `Fixed` (id `1`) / `Duplicate` (id `3`) / `Won't Do` (id `10000`). Use `Fixed` for a Story that shipped. |
| Sub-Component | `customfield_15000` | Pick the option matching the ticket's **component** — e.g. component `URL Security (URLSec)` → `URLSec-Categorization` (id `17719`). A sibling/blocking ticket on the same component is the fastest source for the right id. Fall back to `NA` (id `21484`) only when the component genuinely has no applicable sub-component. |
| Fix QA Test Recommendations | `customfield_12503` | Must be real verification steps — **`NA` is not acceptable**, even though closed sibling tickets sometimes contain it. Write what QA should actually check: the observable behavior, the trigger condition, and the expected result for each item in the Story's scope. |

## Other fields on the Resolve screen

Present on the screen but not enforced. Set them when the ticket gives you a
clear answer; don't invent values to fill them.

| Field name | Field key | Type / allowed values |
|---|---|---|
| Resolution Categories | `customfield_16151` | select (flat, **not** cascading): `User Error / Customer Education / FAD` (`11942`) / `Documentation` (`11943`) / `Regression` (`11944`) / `Performance` (`12654`) / `Functionality Not Currently Supported` (`11945`) / `Functionality Enhanced / New Feature` (`11946`) / `Other` (`11994`). A delivered Story is usually `Functionality Enhanced / New Feature`. |
| Release Note | `customfield_24133` | select: `For Customer` (`27592`) / `For Internal Use` (`27593`) / `Not Required` (`27594`) |
| Release Note Description | `customfield_16130` | text area (ADF) |
| TOI Required | `customfield_16173` | select: `Y` (`11995`) / `N` (`11996`) |
| Feature flag fields | — | `customfield_35098` (Yes `71610` / No `71611`) gates the rest: Flag Type `customfield_35099` (`Tenant Feature Flag` `71612` / `Staged Config` `71613` / `Tenant Feature Flag + Staged Config` `71614` / `Other` `71615`), Default State for Tenant Flag `customfield_35100` (`71616`/`71617`) / Staged Config `customfield_35103` (`71626`/`71627`) / Other `customfield_35104` (`71628`/`71629`) — each Enable/Disable — and Flag Details `customfield_35105` (ADF). Only fill when the ticket states the flag. |

## Transitioning to Resolved

The standard transition — see `references/common.md`. Only `resolution` reports
`required: true` in the screen metadata; every other required field above
reports `required: false` while being enforced by the validator.
