---
name: swg-lookup-svc-deploy-ticket
description: Create the ENG "Deployment" Jira ticket for a swg-lookup-svc production release (modeled on ENG-1151426). Finds the version to ship (latest swg-lookup-svc release tag), diffs it against the version currently running on NPE stg01, collects the Jira tickets from every human-authored PR in that range (skipping cicd-bot / bot PRs), then creates the ticket and links each one as "relates to". Use whenever the user wants to open, file, draft, or prepare a swg-lookup-svc deployment / release / deploy ticket, asks "what's going out in the next swg-lookup-svc release", or says things like "create the deploy ticket for lookup-svc" — even if they don't name the version.
disable-model-invocation: false
allowed-tools: Bash(bash -ic *) Read AskUserQuestion
---

# Create a swg-lookup-svc deployment ticket

All Jira / GitHub / kubectl work goes through
`${CLAUDE_PLUGIN_ROOT}/skills/swg-lookup-svc-deploy-ticket/run.py`. Run it via
`bash -ic '...'` so `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` from `~/.bashrc`
are loaded (`~/.bashrc` early-returns in non-interactive shells). Discard the
harmless "no job control" stderr noise with `2>/dev/null`.

## Workflow

1. **Collect.**
   ```bash
   bash -ic 'python3 ${CLAUDE_PLUGIN_ROOT}/skills/swg-lookup-svc-deploy-ticket/run.py collect' 2>/dev/null
   ```
   It prints JSON:
   - `latest_tag` — latest swg-lookup-svc GitHub release; this is the version to deploy.
   - `stg01_version` — the tag on the swg-lookup-svc deployment in `swg-lookup-mp`
     on stg01 (`~/.nsk/stork-stg01-mp-iad0-nc4.yaml`, refreshed via `nsk` first).
     stg01 tracks the last released version, so it is the baseline.
   - `prs` — every non-bot commit in `stg01_version...latest_tag` (squash-merged
     PRs; bot authors — GitHub `Bot` type plus logins matching `is_bot()`, e.g.
     `cicd-bot` — are counted in `skipped_bot_prs` and dropped).
   - `tickets` — unique ticket keys from those PR titles, in merge order,
     validated against Jira; keys that don't resolve land in
     `dropped_invalid_tickets` instead.

   If `latest_tag == stg01_version` there is nothing new to ship — tell the user
   and stop. If kubectl still fails, point the user at
   `eng-skills:setup-k8s-access`.

2. **Show the draft and confirm.** Creating a ticket and adding links is visible
   to the whole team, so show before writing:
   - Summary `[swg-lookup-svc] deploy <latest_tag>` and the version range.
   - A table of included PRs (number, author, title, tickets), the bot-skip
     count, and any `dropped_invalid_tickets`.
   - Flag any PR with no ticket key — it can't be linked, so the user may want
     to add one by hand.
   - The prod deploy date (`YYYY-MM-DD`), i.e. the day of Batch 1 and 2. All
     other event dates are derived from it via the `EVENTS` offsets in run.py.
     Jira rejects a Deployment ticket without planned dates, so if the user
     hasn't given it, ask — never guess.

   Ask the user to confirm, or to add/remove tickets or change the version.

3. **Create.**
   ```bash
   bash -ic 'python3 ${CLAUDE_PLUGIN_ROOT}/skills/swg-lookup-svc-deploy-ticket/run.py create --version <tag> --tickets <K1,K2,...> --date <YYYY-MM-DD>' 2>/dev/null
   ```
   The date sets each region's planned start/end from the batch hours in
   `BATCH_REGIONS` (batch time UTC+8, 1h window).
   The Dependencies section @-mentions the owner (assignee, else reporter) of
   every linked ticket other than the caller, asking them to fill in any
   deployment dependency their change needs.
   Add `--dry-run` first if the user wants to see the exact payload. The script
   creates the issue with one "Relates" link per ticket in the same request (the
   Deployment validator rejects a create without links), so it either succeeds
   with all links or creates nothing. Report the new ticket URL and the number
   of links.

## What the ticket contains

Modeled on ENG-1151426, minus the parts the user doesn't want copied:

- **Not included:** the "Tickets" list in the description
  (tickets are issue links instead).
- **Description:** Action Items, Dependencies (linked-ticket owners tagged to
  fill it in, above an "N/A" bullet they replace), an Events table (rows and
  date offsets from `EVENTS`), Deployment Info (Version, Jenkins jobs,
  Monitoring dashboard, Maintenance window page), and a trailing `cc @…` line
  (`CC_LIST`).
- **Fields:** Component URL Security (URLSec), Assignee = the caller, and the
  remaining defaults set in `create()` (Deployment Type, Datacenters,
  Customer/Service Impact, Business hours, Release Version, Engineering VP,
  Story Points).

If a batch's pops, the event offsets, or a default field value changes: the
schedule constants (`EVENTS`, `BATCH_REGIONS`, `DATACENTERS`, `planned_dates`)
live in `${CLAUDE_PLUGIN_ROOT}/skills/swg-lookup-svc-common/schedule.py`, shared
with `swg-lookup-svc-update-deploy-ticket` — edit there, not in `run.py`.
Field IDs and the remaining create-only defaults stay in `create()`.

After the deploy runs (via `swg-lookup-svc-deploy`), use
`swg-lookup-svc-update-deploy-ticket` to reschedule, re-version, or comment on
this ticket.
