---
name: resolve-ticket
description: Resolve a Netskope Jira ticket (Escalation, custom ticket, Bug, Nplan) by filling in its resolution fields (Resolution Category, Root Cause Analysis, Solution Provided) and transitioning it to Resolved. Use whenever the user gives a Jira/ENG ticket URL or key and asks to resolve it, close it, or fill in its resolution info — including phrases like "resolve this ticket", "fill in RCA for ENG-XXXXXX", or pastes a netskope.atlassian.net/browse/ENG-XXXXXX link. Covered issue types are listed in the skill's routing table; if a type isn't covered yet, say so rather than guessing field names.
disable-model-invocation: false
allowed-tools: Read Grep Glob AskUserQuestion Bash(gh pr view *) Bash(gh pr diff *) mcp__plugin_atlassian_atlassian__getJiraIssue mcp__plugin_atlassian_atlassian__getJiraIssueTypeMetaWithFields mcp__plugin_atlassian_atlassian__getJiraIssueRemoteIssueLinks mcp__plugin_atlassian_atlassian__getTransitionsForJiraIssue mcp__plugin_atlassian_atlassian__editJiraIssue mcp__plugin_atlassian_atlassian__transitionJiraIssue mcp__plugin_atlassian_atlassian__createIssueLink mcp__plugin_atlassian_atlassian__getIssueLinkTypes mcp__plugin_atlassian_atlassian__lookupJiraAccountId
---

# Resolve a Netskope ticket

Resolving a ticket at Netskope means filling in three resolution fields
(Resolution Category, Root Cause Analysis, Solution Provided), then
transitioning its status to Resolved. Which field keys, valid values, and
transition apply depends on the ticket's **issue type**.

## Workflow

1. **Fetch the issue.** Extract the key from the URL or text the user gave you
   (e.g. `https://netskope.atlassian.net/browse/ENG-1092541` → `ENG-1092541`),
   then fetch everything the rest of the workflow needs in one call — never
   `fields=["*all"]`, which returns a huge response:
   ```
   getJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX",
                fields=["issuetype","summary","description","comment","issuelinks",
                        "fixVersions","priority","labels","components","status",
                        "resolution","customfield_10200"])
   ```

2. **Load the reference for `fields.issuetype.name`:**

   | Issue type | Reference |
   |---|---|
   | Escalation | `references/escalation.md` |
   | Bug | `references/bug.md` |
   | Custom ticket, Nplan | not yet written — tell the user this type isn't covered yet instead of improvising field IDs |

   Read it, plus `references/common.md`, before anything else. Use only the
   matched type's reference — a wrong custom field ID silently writes the wrong
   field on a live ticket.

3. **Read the full ticket and any linked PR before drafting.** Never draft from
   just the summary or a skimmed description.

   - Engineers often leave the RCA/fix summary in a comment rather than a
     dedicated field, so don't stop at the description.
   - Look for linked PRs/commits (remote issue links, or PR links mentioned in
     comments) and **read the actual diff**, not just the PR title or commit
     message summary line — the code change is what confirms the real root
     cause, and a title can be misleading or incomplete.
   - Look for linked issues (e.g. a Bug this Escalation was cloned from, or a
     duplicate) that already has the RCA filled in.
   - Search the affected code/service (component field, summary, and
     description usually name the service — e.g. `swg-lookup-svc`) for the
     behavior described, if no PR is linked yet.

   Then draft the resolution field values. If this turns up nothing usable, say
   plainly what you could and couldn't determine rather than guessing.

4. **Confirm the drafted values with the user before writing anything.** Put the
   multiple-choice decisions (Resolution Category, Fix Version/s, and any
   type-specific selects the reference lists) in a single `AskUserQuestion` block
   as parallel questions, with human-readable option names — never raw IDs. For
   the long free-text fields (Root Cause Analysis, Solution Provided) show the
   drafted prose and ask for approve-or-edit. For fields with one obvious correct
   value, just set them and say briefly what you set.

   `fixVersions` must never be left empty or guessed — if step 1 showed it empty,
   it belongs in this block. Never call `editJiraIssue` before this checkpoint.

5. **Set the fields** — every field the reference lists, in one `editJiraIssue`,
   using its field keys and value shapes and the values the user confirmed.

6. **Get final go-ahead.** The transition is irreversible, so ask for an explicit
   yes via `AskUserQuestion`. Everything was already confirmed in step 4, so keep
   this to a compact go/no-go: the status change plus anything you defaulted
   without asking.

7. **Transition to Resolved.** Fetch the live transition list — IDs are
   workflow-specific and can differ per issue, so don't reuse one from memory or
   from a reference file without confirming it's still there:
   ```
   getTransitionsForJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX")
   ```
   Apply the transition the reference names:
   ```
   transitionJiraIssue(cloudId="netskope.atlassian.net", issueIdOrKey="ENG-XXXXXX", transitionId="<id>")
   ```
   If Jira rejects it, the validation errors are the authoritative required-field
   list: set what they name, re-confirm anything that needs a user decision, and
   retry until it succeeds. Some workflows enforce fields in batches, so a clean
   first error is not the complete list — see the type's reference. Don't force
   the transition through by inventing a value just to satisfy the screen.

## Adding a new issue type

See `references/adding-a-type.md`.
