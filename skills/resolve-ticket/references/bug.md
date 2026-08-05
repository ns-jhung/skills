# Resolving a Bug ticket

Applies to Jira issue type **Bug** (issue type id `1`) in project **ENG**.

See `references/common.md` for the three resolution fields, the Resolution
Category taxonomy, the ADF `editJiraIssue` call shape, and the Fix Version
naming convention.

Bug tickets require roughly a dozen fields beyond those three. Set every field
below in one `editJiraIssue`, then transition once. Some of them don't appear in
`getJiraIssueTypeMetaWithFields` at all, and several report `required: false`
while being hard-enforced by the transition validator — so this list, not
metadata, is the reference for what to set.

## Additional fields

| Field name | Field key | Type / allowed values |
|---|---|---|
| Resolution | `resolution` (system) | Must be `Fixed` if a PR is attached to the ticket (checked automatically). If the PR was declined instead, add label `PR-declined` and use any resolution other than `Fixed`. |
| Fix Version/s | `fixVersions` (system) | Cannot be empty, `TBD`, or `NA` unless the issue has label `no-code` or `no_code`. Never guess or reuse Affects Version — ask the user. |
| QA | `customfield_10200` | single-user-picker. If empty, default to **Michael Lee** (`minweil@netskope.com`, accountId `712020:9e8b8f52-1fe7-4a95-bba7-db644537d687`) without asking. If that accountId is rejected, re-resolve it with `lookupJiraAccountId`. |
| Bug Classification | `customfield_16637` | select: `Feature Issue (Feature never known to have worked)` / `Regression (A previously working feature is broken)` / `SaaS App Change (Vendor application changes that results in traffic or API change)` |
| Fix Description | `customfield_12500` | text area (ADF) |
| Fix Dev Tested | `customfield_12502` | radio buttons: `Yes` / `No`. Not `customfield_12501`, an unrelated field that sits next to it numerically. |
| Fix QA Test Recommendations | `customfield_12503` | text area (ADF) |
| Sub-Component | `customfield_15000` | multiselect, hundreds of options. Use **`NA`** — option id `21484`, i.e. `[{"id": "21484"}]`; if rejected, re-derive it with the parse snippet below. The error text itself says to select `NA` when the component has no applicable sub-component, so don't hunt the list for an approximate match. |
| Where Bug should have been caught | `customfield_16643` | select: `Build` / `Requirement Review` / `Design Review` / `Code Review` / `Unit Test` / `Functional Test` / `Component Integration Test` / `Regression Test` / `E2E Integration Test` / `Solution Test` / `Scale and Performance Test` / `Pre-Prod Validation` / `Security Scans` / `Post Deployment Validation` / `CI Tool` / `Other`. Picking `Other` also requires `customfield_33598` (free-text reason). |
| Where in the Development stage did the bug get introduced | `customfield_16635` | select: `Requirement` / `Design` / `Coding` |
| Involves Feature Flags or Configurations? | `customfield_35098` | radio buttons: `Yes` / `No` |

Not every priority enforces every field, but setting them all is harmless — so
set them all rather than trying to predict which ones this ticket needs.

## Transitioning to Resolved

Look for **"Resolve Issue"** (commonly id `5` on this workflow, but confirm from
the live list — the standard "Close Issue" transition, commonly id `761`, is a
different, later step, not the one this skill targets). It has `hasScreen: true`.

Setting every field above should let the transition succeed on the first
attempt. If Jira still rejects it, the error names what's missing — but as prose,
not field keys: *"Please update the Sub-Component field…"*, *"Please enter a
value for the field \"Where bug should have been caught\"…"*. The wording differs
in case and phrasing from the real field names, so match on substring, set the
field, and report what was missing so this reference can be updated.

For a field not in the table above, get its key and option ids from the
transition-screen metadata — the only place some of them appear:

```
getTransitionsForJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX",
                           transitionId="5", expand="transitions.fields")
```

That response is hundreds of KB and will be spilled to a file. Don't read it
whole — dump one compact line per field and pick out what you need:

```
python3 -c "
import json; d=json.load(open('<saved-file>'))
for t in d['transitions']:
    for fid,f in (t.get('fields') or {}).items():
        print(fid, f['name'], f.get('required'), len(f.get('allowedValues') or []))
"
```
