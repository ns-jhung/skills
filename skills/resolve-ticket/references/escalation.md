# Resolving an Escalation ticket

Applies to Jira issue type **Escalation** (issue type id `11808`) in project **ENG**.

## Required fields

The three resolution fields only — see `references/common.md` for their keys,
the Resolution Category taxonomy, and the ADF `editJiraIssue` call shape.

## Transitioning to Resolved

Look for the transition named `Resolved` (commonly id `51` on this workflow, but
confirm from the live list). It has `hasScreen: true`, so the three fields must
already be populated or Jira rejects the transition naming the missing field(s).

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

Before assuming a link is missing entirely, check the existing links — a
"relates to" link, or a link to a ticket that isn't actually issue type `Bug`
(e.g. a Story tracking the same fix), does not satisfy this rule even though
it looks related. Check each linked issue's `issuetype.name` and `status.name`
in the `issuelinks` you already fetched; if none qualifies, find or ask which
ticket is the actual Bug-type fix record before creating a new "is blocked by"
link with `createIssueLink` (`inwardIssue` = the Bug ticket, `outwardIssue` =
this issue, `type` = `Blocks`).

Creating or changing issue links is a structural edit beyond the resolution
fields — confirm with the user first, like any other field value.
