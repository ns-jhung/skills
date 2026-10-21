---
name: swg-lookup-svc-update-deploy-ticket
description: Update an existing ENG "Deployment" Jira ticket in place — reschedule the prod deploy date (recalculates every region's planned start/end), change the release version, add or remove "relates to" ticket links, or post a status comment. The user must provide the ticket key; ask for it if they haven't. Use whenever the user wants to update, edit, reschedule, or change a swg-lookup-svc / ENG deployment ticket, says things like "update the deploy ticket", "push ENG-XXXXXX to next Tuesday", "add ENG-YYYYYY to the deployment ticket", or "comment on the deploy ticket that batch 2 is done" — but NOT to create one (use swg-lookup-svc-deploy-ticket) or resolve one (use resolve-ticket).
disable-model-invocation: false
allowed-tools: Bash(bash -ic *) Read AskUserQuestion
---

# Update a swg-lookup-svc deployment ticket

All Jira work goes through
`${CLAUDE_PLUGIN_ROOT}/skills/swg-lookup-svc-update-deploy-ticket/run.py`. Run it via
`bash -ic '...'` so `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` from `~/.bashrc`
are loaded (`~/.bashrc` early-returns in non-interactive shells). Discard the
harmless "no job control" stderr noise with `2>/dev/null`.

This skill only updates Deployment-type tickets. If `show` reports a different
issuetype, stop and tell the user rather than writing deployment fields onto an
unrelated ticket.

## Workflow

1. **Get the ticket key.** The user must provide it (e.g. `ENG-1151426` or a
   `netskope.atlassian.net/browse/...` URL). If they haven't, ask — never
   search for or guess the ticket.

2. **Show the current state.**
   ```bash
   bash -ic 'python3 ${CLAUDE_PLUGIN_ROOT}/skills/swg-lookup-svc-update-deploy-ticket/run.py show <KEY>' 2>/dev/null
   ```
   Prints the summary, status, release version, current planned dates per
   region, and existing "relates to" links — the baseline for the diff you'll
   confirm next.

3. **Confirm before writing.** Editing a live ticket is visible to the whole
   team, so show the user exactly what will change (old value → new value,
   links added/removed, comment text) and ask them to confirm. Add `--dry-run`
   if they want to see the exact payload.

4. **Update.**
   ```bash
   bash -ic 'python3 ${CLAUDE_PLUGIN_ROOT}/skills/swg-lookup-svc-update-deploy-ticket/run.py update <KEY> [--date YYYY-MM-DD] [--version TAG] [--add-tickets K1,K2] [--remove-tickets K3] [--comment "TEXT"]' 2>/dev/null
   ```
   Flags combine freely; pass only what the user asked for.

   - `--date` is the prod deploy date (day of Batch 1 and 2). The script
     recalculates every region's planned start/end from `BATCH_REGIONS` in
     `swg-lookup-svc-common/schedule.py` — the same batch hours and UTC+8
     window used when the ticket was created — so a reschedule stays
     consistent with the original schedule. If the user hasn't given a date,
     ask; never guess.
   - `--version` rewrites both the Release Version field and (if it follows the
     standard `[swg-lookup-svc] deploy <tag>` shape) mention that the summary
     still names the old version — offer to update it by hand via the Jira UI
     or a follow-up request, since summary edits are deliberately not automated
     here.
   - `--add-tickets` / `--remove-tickets` manage the "Relates" links the
     deployment validator cares about.
   - `--comment` posts a plain-text status comment.

5. **Report** the ticket URL and a one-line summary of what changed.

## Updating related tickets

When the user also asks to update the *linked* tickets (e.g. add a comment to
each related ticket, or mark them as shipped in this release), repeat this
same flow per linked key — `show` first, confirm, then `update --comment ...`
— after the user confirms the list. Never fan out writes to tickets the user
didn't explicitly name or approve.
