# Shared resolution conventions

Every issue type reference points here. The call shapes and Fix Version rules
below apply to all of them; the three resolution fields and their taxonomy apply
only to types whose reference says so.

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

## The standard Resolve screen

Most ENG types share these fields and this transition; the type's own reference
says whether it uses this screen, and lists what it adds, drops, or overrides.

| Field name | Field key | Type / allowed values |
|---|---|---|
| Fix Version/s | `fixVersions` (system) | Cannot be empty. Never guess or reuse Affects Version — ask the user. |
| QA | `customfield_10200` | single-user-picker. If empty, default to **Michael Lee** (`minweil@netskope.com`, accountId `712020:9e8b8f52-1fe7-4a95-bba7-db644537d687`) without asking. If that accountId is rejected, re-resolve it with `lookupJiraAccountId`. |
| Fix Dev Tested | `customfield_12502` | radio buttons: `Yes` (id `10503`) / `No` (id `10504`). Not `customfield_12501`, an unrelated field that sits next to it numerically. |
| Fix QA Test Recommendations | `customfield_12503` | text area (ADF) |
| Sub-Component | `customfield_15000` | multiselect, hundreds of options — see the type's reference for which option to pick. `NA` is id `21484`. |
| Involves Feature Flags or Configurations? | `customfield_35098` | radio buttons: `Yes` (id `71610`) / `No` (id `71611`) |

### Transitioning to Resolved

Look for **"Resolve Issue"** (commonly id `5` on this workflow, but confirm from
the live list — the standard "Close Issue" transition, commonly id `761`, is a
different, later step, not the one this skill targets). It has `hasScreen: true`.

Metadata under-reports what's enforced: fields report `required: false` while the
transition validator rejects them as missing — so trust the type's field list,
not the metadata.

If Jira still rejects the transition, the error names what's missing as prose
rather than field keys, and the wording differs in case and phrasing from the
real field names — match on substring. If the field it asks for isn't in the
type's tables, that reference is out of date: tell the user which field Jira
asked for, and see `references/adding-a-type.md` for how to look up its field
key and option ids.

## Fix Version naming

Version names follow a `<major>.0.0` convention: a bare release number is
rejected with `Version name '142' is not valid`, while `142.0.0` is accepted. If
the user gives you a bare number, try `<number>.0.0` before reporting failure.
