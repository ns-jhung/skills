# Adding a new issue type, or fixing a stale field list

Maintainer notes — not needed to resolve a ticket.

## Adding a type

1. `getJiraIssue` on a real example of that type to get its `issuetype.id`.
2. `getJiraIssueTypeMetaWithFields(cloudId, projectIdOrKey, issueTypeId)` for the
   field list — this response is large, so search it for field names like
   "Resolution Category" / "Root Cause" / "Solution" rather than reading it whole.
3. `getTransitionsForJiraIssue` on the example issue to find the Resolved
   transition and confirm whether it has a screen (i.e. requires fields set first).
   Metadata under-reports `required`, so also attempt the transition on a real
   ticket and record which fields the validation errors name.
4. Look up those fields with the recipe below.
5. Write `references/<type>.md` covering only what differs from
   `references/common.md` — if the type uses the standard Resolve screen, say so
   and list only its additions and overrides — following the shape of
   `references/bug.md`, and add a row to the routing table in `SKILL.md` step 2.
   The routing table is the only registry; don't enumerate types anywhere else.

## Looking up a field key or option id

Also the fix when a type's reference is missing a field Jira asked for. Some
fields appear nowhere except the transition-screen metadata:

```
getTransitionsForJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX",
                           transitionId="<resolve transition id>", expand="transitions.fields")
```

That response is hundreds of KB and will be spilled to a file. Don't read it
whole — dump one compact line per field, plus `allowedValues` for the field(s)
you actually need, in the same pass:

```
python3 -c "
import json; d=json.load(open('<saved-file>'))
target = {'<field-id-you-need>'}  # leave empty to just list every field
for t in d['transitions']:
    for fid,f in (t.get('fields') or {}).items():
        vals = f.get('allowedValues') or []
        print(fid, f['name'], f.get('required'), len(vals))
        if fid in target:
            for v in vals: print(' ', v.get('id'), v.get('value') or v.get('name'))
"
```

A lighter first pass — the edit-screen metadata is much smaller than the
transition-screen one and lists most fields (name + `allowedValues` id/value)
without the transitionId dance:

```
curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  "https://netskope.atlassian.net/rest/api/3/issue/ENG-XXXXXX/editmeta" -o editmeta.json
python3 -c "
import json; d=json.load(open('editmeta.json'))
for k,v in d.get('fields',{}).items():
    print(k, '|', v.get('name',''))
    for o in v.get('allowedValues',[]): print('   ', o.get('id'), '=', o.get('value'))
"
```

Note the workflow's error prose doesn't always use the real field name — e.g.
"Bug Origin" / "Detection Point" map to "Where Bug was found" / "Where in the
Development stage did the bug get introduced", not to any field literally named
Origin or Detection. Match on meaning, not substring, before concluding a field
is missing from the list.

Add the result to the type's reference table so the next run doesn't need this
lookup.
