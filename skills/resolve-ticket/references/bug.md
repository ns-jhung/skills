# Resolving a Bug ticket

Applies to Jira issue type **Bug** (issue type id `1`) in project **ENG**.

## Required fields

| Field name | Field key | Type |
|---|---|---|
| Resolution Category | `customfield_18214` | cascading select (category → sub-category) — same taxonomy as Escalation, see `references/escalation.md` |
| Root Cause Analysis | `customfield_11701` | text area (ADF) |
| Solution Provided | `customfield_18343` | text area (ADF) |

These three are the same "resolution fields" described in the main `SKILL.md`
workflow. Bug tickets additionally enforce a longer list of workflow-specific
required fields on the Resolved transition itself — discovered by attempting
the transition and reading the validation errors it returns, not from static
metadata (some of these fields, e.g. `customfield_12502`, don't appear in
`getJiraIssueTypeMetaWithFields` at all; they only show up via
`getTransitionsForJiraIssue(..., expand="transitions.fields")` for the specific
transition).

### System field

| Field name | Field key | Notes |
|---|---|---|
| Resolution | `resolution` (system field, not custom) | Set via `editJiraIssue(fields={"resolution": {"name": "Fixed"}})`. Must be `Fixed` if a PR is attached to the ticket (checked automatically) — if the PR was declined instead, add label `PR-declined` and use any resolution other than `Fixed`. |

### Conditionally-required fields (Resolved transition, resolution = Fixed)

These are only enforced when resolving as **Fixed**. Confirmed present when
priority is Critical (likely applies to Blocker too — not yet confirmed for
other priorities):

| Field name | Field key | Type / allowed values |
|---|---|---|
| Fix Version/s | `fixVersions` (system field) | Must be a real version — cannot be empty, "TBD", or "NA" unless the issue has label `no-code` or `no_code`. **Always ask the user which version to set** — never guess or reuse the Affects Version value, per the main workflow's Fix Version rule. |
| Bug Classification | `customfield_16637` | select: `Feature Issue (Feature never known to have worked)` / `Regression (A previously working feature is broken)` / `SaaS App Change (Vendor application changes that results in traffic or API change)` |
| Fix Description | `customfield_12500` | text area (ADF) |
| Fix Dev Tested | `customfield_12502` | **radio buttons**: `Yes` / `No`. Not to be confused with `customfield_12501`, an unrelated field that sits next to it numerically. |
| Fix QA Test Recommendations | `customfield_12503` | text area (ADF) |

Jira validates these in batches — fixing the first error surfaced can reveal a
second, unrelated batch of missing fields (this happened when discovering this
list: Fix Version + RCA + Bug Classification errors cleared to reveal the QE
Fields Tab batch above). Don't assume one clean error message is the complete
list; retry the transition after each fix and keep reading errors until it
succeeds.

## Setting the fields

Same ADF requirement as Escalation for textarea fields — see
`references/escalation.md` for the exact `editJiraIssue` call shape. Select /
radio-button fields take `{"value": "<option label>"}`; `fixVersions` takes
`[{"id": "<version id>"}]` or `[{"name": "<version name>"}]`.

## Transitioning to Resolved

Fetch the live transition list — don't hardcode:

```
getTransitionsForJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX")
```

Look for **"Resolve Issue"** (commonly id `5` on this workflow, but confirm
from the live list — the standard "Close Issue" transition, commonly id
`761`, is a different, later step, not the Resolved transition this skill
targets). It has `hasScreen: true`.

```
transitionJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX", transition={"id": "5"})
```

If Jira rejects it, read every error message in the response — set the named
fields and retry. Repeat until it succeeds; don't stop after the first
error message looks resolved, since later batches only surface once earlier
ones clear.
