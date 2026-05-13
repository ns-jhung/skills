# Per-source briefing templates

Each section gives a ready-to-adapt prompt for a `general-purpose` sub-agent. Replace `{QUERY}`, `{SYNONYMS}`, and `{WINDOW}` before dispatching. Every agent must be told to **report under 250 words with URLs on every hit**.

## Universal auth-fallback clause

Append this to EVERY briefing prompt (it applies to every source — see `../SKILL.md` → "Auth-required fallback"):

```
If you hit an auth error (missing token, 401/403, SSO/Teleport redirect, OAuth
expiry, login-page HTML), do NOT silently skip. Report exactly:
  skipped: needs <auth-method> — manual search: <manual-url-with-query-encoded>
Use the manual-search URL pattern listed in this source's section. Never invent
credentials, never try to bypass SSO, never guess session cookies.
```

---

## Jira

**CLI**: `~/.claude/plugins/cache/netskope/eng-skills/*/skills/jira/scripts/jira` (glob — agent should expand with `ls` first)
**Auth**: requires `ATLASSIAN_API_TOKEN`, `ATLASSIAN_EMAIL`, `ATLASSIAN_SITE=netskope` in env.
**Site**: https://netskope.atlassian.net
**Manual-search URL**: `https://netskope.atlassian.net/issues/?jql=text%20~%20%22{QUERY}%22`

**Prompt template**:
```
Search Netskope Jira for "{QUERY}" (synonyms: {SYNONYMS}). Use the jira CLI at
~/.claude/plugins/cache/netskope/eng-skills/*/skills/jira/scripts/jira — run
`ls` on that glob first to find the real path, then use `jira search` with a
JQL like: text ~ "{QUERY}" AND updated > -{WINDOW}d. Return up to 10 ranked
hits as: [KEY](https://netskope.atlassian.net/browse/KEY) — status, assignee,
one-line summary. If auth env vars are missing, report "skipped: needs
ATLASSIAN_API_TOKEN". Under 250 words.
```

---

## Confluence

**CLI**: `~/.claude/plugins/cache/netskope/eng-skills/*/skills/confluence/scripts/confluence`
**Auth**: same Atlassian env vars as Jira.
**Site**: https://netskope.atlassian.net/wiki
**Manual-search URL**: `https://netskope.atlassian.net/wiki/search?text={QUERY}`

**Prompt template**:
```
Search Netskope Confluence for "{QUERY}" (synonyms: {SYNONYMS}). Use the
confluence CLI at ~/.claude/plugins/cache/netskope/eng-skills/*/skills/confluence/scripts/confluence
— resolve the glob with `ls` first, then use `confluence search` (CQL:
text ~ "{QUERY}"). Return up to 8 ranked pages as:
[Title](https://netskope.atlassian.net/wiki/...) — space, last-updated,
one-line relevance. Under 250 words.
```

---

## Slack

**Tools**: Slack MCP plugin. Prefer these in order:
- `mcp__plugin_slack_slack__slack_search_public_and_private` — main search
- `mcp__plugin_slack_slack__slack_search_channels` — find the right channel
- `mcp__plugin_slack_slack__slack_read_thread` — drill into a promising hit

**Manual-search URL**: `https://netskope.slack.com/search/{QUERY}`

**Prompt template**:
```
Search Slack for "{QUERY}" (synonyms: {SYNONYMS}) in the last {WINDOW} days.
Use mcp__plugin_slack_slack__slack_search_public_and_private. Return up to 8
ranked hits as: [#channel · date](permalink) — author, one-line quote or
summary. Favor threads with replies over isolated messages. If a hit looks
like it has follow-up context, note "thread has N replies" so the caller
knows to drill in. Under 250 words.
```

---

## GitHub

**CLI**: `gh` (already installed at `/usr/bin/gh`)
**Scopes to search**: issues, PRs, code. Netskope org is typically `netskopeoss` for public and a private org for internal repos — agent should try both.
**Manual-search URL**: `https://github.com/search?q={QUERY}&type=issues` (swap `type=` for prs / code / commits)

**Prompt template**:
```
Search GitHub for "{QUERY}" across Netskope orgs. Run these in parallel:
  gh search issues "{QUERY}" --owner netskopeoss --limit 10
  gh search prs    "{QUERY}" --owner netskopeoss --limit 10
  gh search code   "{QUERY}" --owner netskopeoss --limit 10
Also try any private org the user has access to (check `gh api user/orgs`).
Return up to 12 ranked hits as: [repo#N](url) — type (issue/PR/code), state,
one-line relevance. Under 250 words.
```

---

## Artifactory

**CLI**: `jf` (JFrog CLI, at `/usr/local/bin/jf`)
**Web**: https://artifactory.netskope.io/ui/packages
**Manual-search URL**: `https://artifactory.netskope.io/ui/packages?name={QUERY}`

**Prompt template**:
```
Search Netskope Artifactory for packages matching "{QUERY}". Try:
  jf rt search "*{QUERY}*" --limit 20
If jf isn't configured (no server set), fall back to fetching
https://artifactory.netskope.io/ui/packages?name={QUERY} via WebFetch and
extracting package names + repo paths. Return up to 10 hits as:
[package-name](artifactory-url) — repo, version, size or last-modified.
If both approaches fail, report "skipped: jf not configured and web needs
SSO". Under 200 words.
```

---

## Budget guidance

When the user hasn't scoped tightly, limit total cost:
- 1 agent per source, in parallel → ~5 agents.
- Each capped at ~250 words and ~10 hits.
- If any source comes back with clearly-ranked top hits, the synthesized reply should surface 3-5 total, not all 50.
