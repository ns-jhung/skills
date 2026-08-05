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
   `references/common.md`, following the shape of `references/bug.md`, and add a
   row to the routing table in `SKILL.md` step 2.

## Looking up a field key or option id

Also the fix when a type's reference is missing a field Jira asked for. Some
fields appear nowhere except the transition-screen metadata:

```
getTransitionsForJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX",
                           transitionId="<resolve transition id>", expand="transitions.fields")
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

Then re-run for just the field you want, printing `allowedValues` to get the
option ids. Add the result to the type's reference table so the next run doesn't
need this lookup.
