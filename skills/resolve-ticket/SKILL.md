---
name: resolve-ticket
description: Resolve a Netskope Jira ticket (Escalation, custom ticket, Bug, Nplan) by filling in its resolution fields (Resolution Category, Root Cause Analysis, Solution Provided) and transitioning it to Resolved. Use whenever the user gives a Jira/ENG ticket URL or key and asks to resolve it, close it, or fill in its resolution info — including phrases like "resolve this ticket", "fill in RCA for ENG-XXXXXX", or pastes a netskope.atlassian.net/browse/ENG-XXXXXX link. Currently covers Escalation and Bug issue types; other issue types (custom ticket, Nplan) are being added — if asked about one not yet covered, say so rather than guessing field names.
disable-model-invocation: false
allowed-tools: Read Grep Glob AskUserQuestion Bash(gh pr view *) Bash(gh pr diff *) mcp__plugin_atlassian_atlassian__getJiraIssue mcp__plugin_atlassian_atlassian__getJiraIssueTypeMetaWithFields mcp__plugin_atlassian_atlassian__getJiraIssueRemoteIssueLinks mcp__plugin_atlassian_atlassian__getTransitionsForJiraIssue mcp__plugin_atlassian_atlassian__editJiraIssue mcp__plugin_atlassian_atlassian__transitionJiraIssue mcp__plugin_atlassian_atlassian__createIssueLink mcp__plugin_atlassian_atlassian__getIssueLinkTypes mcp__plugin_atlassian_atlassian__lookupJiraAccountId
---

# Resolve a Netskope ticket

Resolving a ticket at Netskope means two things: filling in its three
resolution fields (Resolution Category, Root Cause Analysis, Solution
Provided), then transitioning its status to Resolved. Which field keys, valid
values, and transition apply depends on the ticket's **issue type** — this
skill routes to a per-type reference so each type's quirks (field IDs,
cascading-select taxonomies, transition names) live in one place and can be
extended independently.

## Workflow

1. **Identify the issue.** Extract the issue key from the URL or text the user
   gave you (e.g. `https://netskope.atlassian.net/browse/ENG-1092541` → `ENG-1092541`).

2. **Fetch the issue and determine its type.**
   ```
   getJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX")
   ```
   The default field set includes `issuetype` — you don't need `fields=["*all"]`
   for this step, and asking for `*all` risks a huge response. Look at
   `fields.issuetype.name`.

3. **Load the reference for that issue type:**

   | Issue type | Reference |
   |---|---|
   | Escalation | `references/escalation.md` |
   | Bug | `references/bug.md` |
   | Custom ticket, Nplan | not yet written — tell the user this type isn't covered yet instead of improvising field IDs |

   Read the matched reference file before doing anything else — it has the
   exact field keys, allowed values, and transition details for that type.
   Guessing custom field IDs from memory is a common way to silently corrupt
   the wrong field on a real ticket, so don't skip this step even if the type
   looks familiar from a previous session.

4. **Read the full ticket and any linked PR before drafting anything.** This
   is a hard prerequisite, not an optional fallback — never draft the
   resolution fields from just the summary or a skimmed description.

   - Fetch the full description and all comments — `getJiraIssue(...,
     fields=["comment"])` if they weren't already included. Engineers often
     leave the RCA/fix summary in a comment rather than a dedicated field, so
     don't stop at the description.
   - Look for linked PRs/commits (remote issue links, or PR links mentioned in
     comments) and **read the actual diff**, not just the PR title or commit
     message summary line — the code change is what confirms the real root
     cause, and a title can be misleading or incomplete.
   - Look for linked issues (e.g. a Bug this Escalation was cloned from, or a
     duplicate) that already has the RCA filled in.
   - Search the affected code/service (component field, summary, and
     description usually name the service — e.g. `swg-lookup-svc`) for the
     behavior described, if no PR is linked yet.

   Only after this reading is done, draft the content for the three
   resolution fields (names may vary slightly by type, but the reference will
   confirm): what category the resolution falls into, what the root cause
   was, and what solution was provided.

   Only surface a question to the user if this investigation turns up
   nothing usable (e.g. no linked PR, no comments, code doesn't show an
   obvious cause) — at that point say plainly what you could and couldn't
   determine, rather than guessing.

5. **Show the drafted values to the user and get explicit confirmation before
   writing anything.** List all three fields plainly (field name → proposed
   value, using the human-readable option names, not raw IDs) so the user can
   catch a wrong category or a root cause that missed the point. Only proceed
   to step 6 once the user confirms or edits the draft — never call
   `editJiraIssue` on the first pass without this checkpoint.

6. **Set the fields**, using the field keys and value shapes from the type's
   reference file, with the values as confirmed (or corrected) by the user.

7. **Check Fix Version/s before resolving.** If the `fixVersions` field is
   empty, stop and ask the user which version to set rather than resolving
   without one or guessing a value.

8. **Check the QA field before resolving.** `QA` (`customfield_10200`, a
   single-user-picker) is common across issue types. If it's empty, default it
   to **Michael Lee** (`minweil@netskope.com`,
   accountId `712020:9e8b8f52-1fe7-4a95-bba7-db644537d687`) — no need to ask
   the user first, unlike Fix Version/s above.

9. **Get final user confirmation before resolving.** Before calling the
   Resolved transition, show the user everything that is about to be set or
   has been set — the three resolution fields (as confirmed in step 5), the
   Fix Version/s value, the QA default (if applied), and any other
   type-specific required field from the reference file — and get explicit
   go-ahead. This is a distinct checkpoint from step 5: step 5 confirms the
   drafted resolution content, this step confirms the full set of field
   changes right before the irreversible transition call. Only proceed to the
   next step once the user confirms.

10. **Transition the issue to Resolved.** Fetch the live transition list for
   this issue — transition IDs are workflow-specific and can differ per issue,
   so don't reuse one from memory or from the reference file without
   confirming it's still there:
   ```
   getTransitionsForJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX")
   ```
   Find the transition named `Resolved` (the reference file may note a common
   ID as a hint) and apply it:
   ```
   transitionJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX", transitionId="<id>")
   ```
   If Jira rejects the transition citing a missing field, that means an
   earlier step didn't actually set everything the workflow screen requires —
   go back, set the missing field, and retry. Don't force the transition
   through by inventing a value just to satisfy the screen.

## Adding a new issue type

When covering a new type (custom ticket, Bug, Nplan, etc.), the pattern is:

1. `getJiraIssue` on a real example of that type to get its `issuetype.id`.
2. `getJiraIssueTypeMetaWithFields(cloudId, projectIdOrKey, issueTypeId)` to get
   the field list — this response is large, so search it for field names like
   "Resolution Category" / "Root Cause" / "Solution" rather than reading it whole.
3. `getTransitionsForJiraIssue` on the example issue to find the Resolved
   transition and confirm whether it has a screen (i.e. requires fields set first).
4. Write a new `references/<type>.md` following the shape of `references/escalation.md`,
   and add a row to the table in step 3 above.
