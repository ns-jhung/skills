# Shared resolution conventions

Applies to every issue type. Both `escalation.md` and `bug.md` point here.

## The three resolution fields

| Field name | Field key | Type |
|---|---|---|
| Resolution Category | `customfield_18214` | cascading select (category → sub-category) |
| Root Cause Analysis | `customfield_11701` | text area (ADF) |
| Solution Provided | `customfield_18343` | text area (ADF) |

## Resolution Category taxonomy

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

Treat this list as authoritative. Only re-fetch it if `editJiraIssue` rejects
your value as invalid — the response below is ~70k lines, so grep the saved
tool-result file rather than reading it:

```
getJiraIssueTypeMetaWithFields(cloudId="netskope.atlassian.net", projectIdOrKey="ENG", issueTypeId="<id>")
```

## Setting the fields

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

Other value shapes: select / radio-button fields take `{"value": "<option label>"}`
or `{"id": "<option id>"}` — prefer `id` when you already have it, since it
avoids label-typo rejections. Multiselect fields take an array of those objects.
`fixVersions` takes `[{"name": "<version name>"}]` or `[{"id": "<version id>"}]`.
Single-user-pickers take `{"accountId": "<accountId>"}`.

## Fix Version naming

Version names follow a `<major>.0.0` convention: a bare release number is
rejected with `Version name '142' is not valid`, while `142.0.0` is accepted. If
the user gives you a bare number, try `<number>.0.0` before reporting failure.
