---
name: netskope-search
description: Unified search across Netskope's knowledge sources — Jira, Confluence, Slack, GitHub, and Artifactory. Use when the user asks to look something up across "all the places", wants context on a term/incident/ticket/service, or says things like "search everywhere for X", "find anything about Y", "what do we know about Z". Delegates to parallel sub-agents so the main conversation stays uncluttered.
user_invocable: true
---

# Netskope unified search

This skill finds information about a topic across Netskope's internal systems by **delegating each source to a parallel sub-agent**. The main conversation only sees a synthesized summary with citations.

## When to invoke

- User asks an open-ended "where is X documented / discussed / tracked" question.
- User drops an unfamiliar term, service name, incident ID, CVE, or ticket reference and wants context.
- Debugging or on-call work where information is scattered across tools.

Do **not** invoke when the user points at a single source (e.g., "look up JIRA-123" → use `/jira` directly).

## Step 1 — Clarify the query

Before dispatching agents, briefly confirm:

1. **The search term(s)** — exact strings, service names, ticket IDs, error messages. Ask for synonyms if the term is ambiguous.
2. **Scope** — which sources to search. Default to all available (see the source list below). If the user already implied a subset (e.g., "check wiki and slack"), use just those.
3. **Time window** — default to "recent" (last 90 days) for Slack/Jira; "any time" for Confluence/GitHub/Artifactory. Override if the user specifies.

If the query is a single well-known ID (e.g., `DP-1234`, a GitHub PR URL), skip the clarification and fetch it directly.

## Step 2 — Dispatch parallel sub-agents

Launch one `general-purpose` Agent per source **in a single assistant turn** (multiple Agent tool-uses in one message) so they run concurrently. Each agent gets a self-contained prompt that:

- States the search term and any synonyms.
- Names the specific source and tool/CLI to use (see `references/sources.md`).
- Caps the response (e.g., "report under 250 words, include URLs for every hit").
- Asks for a ranked list of hits with one-line relevance explanations, not raw dumps.

**Important**: pass the exact CLI paths / MCP tool names to each agent — sub-agents start with no context about which skills are installed. See `references/sources.md` for the per-source briefing template.

## Step 3 — Main process synthesizes (do NOT delegate this)

Synthesis is the **main conversation's job** — it is the whole reason this skill exists. Sub-agents only gather raw hits; they don't see each other's output and can't cross-reference. Do not spawn yet another agent to "summarize" — you lose the cross-source links that make the answer useful.

Read every sub-agent's return, then produce a single response:

- **Summary** (2-4 sentences): what the query term actually *is*, synthesized from across sources — e.g., "NPLAN-5018 is a Phase-2 feature adding destination profile to URL lookup; R139 targeted; architectural pivot in Feb 2026." This is a claim you build from multiple sources, not a quote from one.
- **Per-source findings**: grouped by source, each bullet `[link](url) — one-line relevance`. Filter aggressively — if an agent returned 10 hits but only 3 are genuinely relevant, show 3.
- **Cross-source links**: call out when the same ticket/PR/person/date appears in multiple sources — that overlap is often the highest-signal insight and no single agent can see it. E.g., "PR #1352 (GitHub) implements ENG-932128 (Jira) which Ana flagged in Slack 2026-05-08."
- **Gaps**: sources that returned nothing OR were auth-blocked, each with its manual-search URL per the auth-fallback rule.
- **Suggested next step**: which 1-2 hits to open first, or what follow-up query would narrow the picture.

Rules:
- **Never forward raw agent output verbatim.** If you find yourself copy-pasting an agent's bullet list, you skipped the synthesis step.
- **Resolve contradictions**, don't just list them. If Jira says "R138" and Slack says "R139", look at dates — the newer one wins, say so.
- **Own the filtering**: agents rank within their source, but only the main process sees all sources and can say "this hit looks relevant in isolation but is noise given what the others returned."

## Sources

See `references/sources.md` for per-source briefing templates (exact CLIs, MCP tool names, URL patterns, auth notes). Currently covered:

- **Jira** — `/jira` CLI (Netskope Atlassian site)
- **Confluence** — `/confluence` CLI (`netskope.atlassian.net/wiki`)
- **Slack** — Slack MCP plugin (`mcp__plugin_slack_slack__*` tools)
- **GitHub** — `gh` CLI (issues, PRs, code search)
- **Artifactory** — `jf` CLI + `https://artifactory.netskope.io/ui/packages` web search

## Output discipline

- Keep the synthesized response scannable — links + one-line context, not prose walls.
- Always cite with URLs. A finding without a link is not useful.
- If a source's auth is missing (e.g., no `ATLASSIAN_API_TOKEN`), note it as "skipped: needs setup" rather than silently dropping it.

## Auth-required fallback (applies to every source)

Any source can fail on auth — missing API token, expired OAuth, SSO/Teleport redirect, Okta challenge, rate-limit-then-login, etc. The rule is the same everywhere:

1. **Sub-agent must not silently skip.** It reports `skipped: needs <auth-method>` (e.g., `needs ATLASSIAN_API_TOKEN`, `needs Teleport SSO`, `needs gh auth login`, `needs OAuth refresh`).
2. **Sub-agent must return a manual-search URL** with the query pre-filled whenever the source has a web UI (e.g., `https://netskope.atlassian.net/issues/?jql=text ~ "<QUERY>"`, `https://ui-prism.apps.netskope.io/?search=<QUERY>`, `https://github.com/search?q=<QUERY>`). URL-encode the query.
3. **The synthesized reply surfaces this in the Gaps section** as a concrete call-to-action: `🔐 <Source> needs <auth> — open [manual search](url) to check yourself.`
4. **Never invent credentials, guess session cookies, or try to bypass SSO.** If the user wants programmatic access to an auth-gated source, treat that as a separate setup conversation (point them at the relevant skill's setup section) — don't bundle it into the search itself.

Each per-source briefing in `references/sources.md` includes the manual-search URL pattern for that source so the agent always has one to hand back.
