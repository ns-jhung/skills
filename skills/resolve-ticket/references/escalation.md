# Resolving an Escalation ticket

Applies to Jira issue type **Escalation** (issue type id `11808`) in project **ENG**.

## Required fields

| Field name | Field key | Type |
|---|---|---|
| Resolution Category | `customfield_18214` | cascading select (category → sub-category) |
| Root Cause Analysis | `customfield_11701` | text area |
| Solution Provided | `customfield_18343` | text area |

### Resolution Category taxonomy

`customfield_18214` is a cascading select — pick one top-level category and,
for most categories, one child sub-category. Full allowed values:

- **Bug** → `Fixed` | `Won't Do` | `Cannot Reproduce`
- **Content Issue** → `NS Content Issue` | `OEM Content Issue`
- **Customer Side Issue** → `Wrong Setup Issue/Config Issue` | `Manual Cleanup (customer initiated)`
- **Documentation Issue** → `Product Documentation` | `SOP/Runbook/TOI/Debug instructions`
- **Feature Flag Change** → `NA`
- **Infra Issue** → `Network` | `Database` | `System` | `Capacity`
- **Netskope Customer Config** → `Config Issue` | `Config Cleanup` | `DB Cleanup`
- **No Response from Customer** → `NA` | `Auto-Resolved`
- **Not Enough Data to Conclude** → `NA`
- **Works as Designed** → `External Factor - Do Nothing` | `NS Product - Do Nothing` | `Support needed review/info from Eng for analysis` | `Netskope Vendor - Bug` | `Netskope Vendor - Other` | `Candidate for Feature Enhancement` | `Candidate for New Feature`

If you're unsure this list is still current, re-fetch it rather than trusting
this file blindly:

```
getJiraIssueTypeMetaWithFields(cloudId="netskope.atlassian.net", projectIdOrKey="ENG", issueTypeId="11808")
```

This response is large (~70k lines). Don't read it whole — search within it
(e.g. `grep -n "Resolution Category"` on the saved tool-result file) for just
the `Resolution Category`, `Root Cause Analysis`, and `Solution Provided`
field blocks.

## Setting the fields

Use `editJiraIssue` with the cascading select expressed as `{value, child: {value}}`.

`customfield_11701` and `customfield_18343` are Jira textareas that reject plain
strings — even with `contentFormat: "markdown"` on the call — with `Operation
value must be an Atlassian Document`. Pass full Atlassian Document Format (ADF)
objects instead:

```
editJiraIssue(
  cloudId="netskope.atlassian.net",
  issueIdOrKey="ENG-XXXXXX",
  fields={
    "customfield_18214": {"value": "Bug", "child": {"value": "Fixed"}},
    "customfield_11701": {
      "type": "doc", "version": 1,
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "<root cause analysis text>"}]}]
    },
    "customfield_18343": {
      "type": "doc", "version": 1,
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "<solution provided text>"}]}]
    }
  }
)
```

## Transitioning to Resolved

After the three fields are set, transition the issue. Fetch the live
transition list rather than hardcoding an ID — it's workflow-specific and can
vary by issue:

```
getTransitionsForJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX")
```

Look for the transition named `Resolved` (commonly id `51` on this workflow,
but confirm from the live list). That transition has `hasScreen: true`,
meaning Jira expects the three fields above to already be populated — if you
transition before setting them, Jira rejects it with a validation error naming
the missing field(s).

```
transitionJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX", transitionId="51")
```

### Extra workflow rule when Resolution Category is "Bug → Fixed"

If `customfield_18214` is set to `Bug` / `Fixed`, the transition also requires
at least one **issue link of type "is blocked by" or "is cloned by"** pointing
to an issue whose **issue type is literally `Bug`** (not Story, not Escalation)
and whose status is Closed/Done. Jira's error message doesn't say which linked
ticket is wrong, only that the requirement isn't met:

```
If Resolution Category is "Bug - Fixed", please link at least one (is blocked by/is cloned by)
Bug type ticket and ensure that all the (is blocked by/is cloned by) linked tickets are in
Closed/Done status.
```

Before assuming a link is missing entirely, check existing links first — a
"relates to" link, or a link to a ticket that isn't actually issue type `Bug`
(e.g. a Story tracking the same fix), does not satisfy this rule even though
it looks related. Fetch `getJiraIssue(..., fields=["issuelinks"])`, check each
linked issue's `issuetype.name` and `status.name`, and if none qualifies, find
or ask which ticket is the actual Bug-type fix record before creating a new
"is blocked by" link with `createIssueLink` (`inwardIssue` = the Bug ticket,
`outwardIssue` = this issue, `type` = `Blocks`).

Creating or changing issue links is a structural edit beyond the three
resolution fields — confirm with the user before adding one, the same way you
confirm the field values in step 5 of the main workflow.
