# Adding a new issue type

Maintainer notes — not needed to resolve a ticket.

1. `getJiraIssue` on a real example of that type to get its `issuetype.id`.
2. `getJiraIssueTypeMetaWithFields(cloudId, projectIdOrKey, issueTypeId)` for the
   field list — this response is large, so search it for field names like
   "Resolution Category" / "Root Cause" / "Solution" rather than reading it whole.
3. `getTransitionsForJiraIssue` on the example issue to find the Resolved
   transition and confirm whether it has a screen (i.e. requires fields set first).
   Add `expand="transitions.fields"` to see fields that don't appear in the
   issue-type metadata at all. Metadata under-reports `required`, so also attempt
   the transition on a real ticket and record the validation errors.
4. Write `references/<type>.md` covering only what differs from
   `references/common.md`, following the shape of `references/bug.md`, and add a
   row to the routing table in `SKILL.md` step 2.
