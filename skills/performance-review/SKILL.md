---
name: performance-review
description: Draft the Netskope performance review (quarterly self-assessment) from Jira tickets assigned to the user that were resolved/closed in a given quarter. Use whenever the user asks to write, draft, or prepare their quarterly review, quarterly self-assessment, performance review, or quarterly summary from their Jira tickets — including phrases like "write my quarterly review", "draft my Q3 review", "performance review from my tickets". Requires a quarter input (e.g. "2026Q3"). Output is a dark-mode HTML file under ~/netskope/note/performence/ answering the standard 3 review questions in bullet points.
disable-model-invocation: false
allowed-tools: Read Write AskUserQuestion Bash(~/.claude/plugins/eng-skills@netskope/skills/jira/scripts/jira *) Bash(~/.claude/plugins/cache/netskope/eng-skills/*/skills/jira/scripts/jira *)
---

# Quarterly performance review drafter

Drafts the standard Netskope quarterly self-review — the 3 questions about
achievements, growth, and support — from the user's resolved Jira tickets, as a
dark-mode HTML file in `~/netskope/note/performence/` (note the spelling; the
directory is the user's existing convention).

## Workflow

1. **Parse the quarter.** The user gives a quarter like `2026Q3` or `Q3 2026`
   (also accept `last quarter`, resolved against today's date). Convert to a
   date range: Q1 = 01-01–03-31, Q2 = 04-01–06-30, Q3 = 07-01–09-30,
   Q4 = 10-01–12-31. If the user hasn't given a quarter, ask — don't default
   to the current quarter, since reviews are usually written for the quarter
   that just ended.

2. **Fetch the tickets** with the jira CLI (setup documented in the `jira`
   skill — if it fails with auth errors, point the user there):
   ```bash
   jira search "assignee = currentUser() AND statusCategory = Done AND resolutiondate >= YYYY-MM-DD AND resolutiondate <= YYYY-MM-DD ORDER BY resolutiondate ASC" 100
   ```
   `resolutiondate` (not `updated` or `resolved`) is what pins a ticket to the
   quarter it was actually finished in. If the result is empty or suspiciously
   small, say so and confirm the range with the user before going further.

   **`jira search` silently caps at 100 results** — a busy quarter can exceed
   that, and truncating drops real work. When it returns exactly 100,
   paginate with the raw API until `isLast`:
   ```bash
   jira get "search/jql?jql=<url-encoded JQL>&maxResults=100&fields=summary,labels[&nextPageToken=<token>]"
   ```

   **Filter out auto-generated noise before grouping.** X-ray scan-defect
   tickets (summary starts with `[Xray Scan Defect in`, label
   `AUTO_GENERATED_JIRA_BY_XRAY_SCAN`), auto-created CM feature-flag tickets
   (label `ff-cli-created`), and similar bot/filed-by-automation tickets are
   bulk process artifacts, not review-worthy contributions — exclude them
   from the ticket list entirely rather than summarizing them as a bullet.
   Also exclude tickets that were **auto-closed by the FF automation** —
   detect them by a linked `CM-` ticket (check `linked_issues` on each kept
   ticket); e.g. an ENG XFF/http2 config ticket that the feature-flag
   automation resolved is process noise, not a contribution.

2b. **Fetch merged PRs and commits** for the same window. Jira tickets miss
   work that never got a ticket (small fixes, repo scaffolding) and hide the
   actual code footprint; PRs fill both gaps. `gh search prs` covers the
   private `netSkope` org:
   ```bash
   gh search prs --author @me --merged-at YYYY-MM-DD..YYYY-MM-DD --limit 100 \
     --json repository,number,title,closedAt
   ```
   Some work lands as **direct commits to master** with no PR (repo
   scaffolding, small config fixes) — PR search alone misses it. List commits
   per repo the PR search surfaced (plus any repo the user mentions):
   ```bash
   gh api "repos/netSkope/<repo>/commits?author=<github-login>&since=...&until=...&per_page=100"
   ```
   (`author` must be the GitHub login from `gh api user --jq .login`, not the
   git author name.) Direct commits are the ones whose message has no
   `(#NNNN)` PR suffix and isn't a merge commit; subtract commits already
   covered by the merged-PR list.

   Exclude bot/dependency PRs the same way as auto-generated tickets. Use
   PRs to (a) back Q1 claims with concrete code changes (repo#number reads
   well next to a ticket key), and (b) spot work with no ticket at all —
   those belong in the ticket list shown to the user in step 4, marked as
   PR-only. Don't enumerate every PR in the report; cite the ones behind
   each theme.

   **Not all impact lives in Jira or GitHub.** Non-code artifacts the user
   built during the quarter — Claude Code skills, runbooks, Confluence
   pages, dashboards — are legitimate Q1 material but invisible to both
   sources. The user works on Claude Code skills under
   `~/netskope/skills/skills/` (`git log --since/--until` there shows what
   changed in the window). When the quarter includes such work, give it its
   own bullet rather than burying it inside a code theme.

   **Tickets table**: right under the statistics block, render every kept
   ticket as a table grouped by repo/area (infer the group from summary
   keywords and components — e.g. `[swg-lookup-svc]` prefix, service name,
   NPLAN epic), with the group as a rowspan first column, largest groups
   first, and the ticket key linked to
   `https://netskope.atlassian.net/browse/<KEY>` — the report doubles as the
   evidence list when the review is questioned.


3. **Let the volume pick the topics.** Group tickets by repo/area (the same
   grouping as the Tickets table) and combine with the per-repo commit
   counts — the largest groups *are* the quarter's contributions, so the Q1
   topics and their order come from group size, one topic per major group.
   A group of one or two tickets is a supporting detail folded into a
   bigger topic, never a topic of its own, and non-code work (skills,
   runbooks) rides inside the closest topic rather than standing alone.
   The Summary bullets stay plain prose — the tables above already carry
   the numbers.

4. **Read each ticket's summary, issue type, components, and resolution.** For
   tickets whose summary is too terse to explain the work (very common),
   fetch the full issue with `jira issue KEY` for the description. Group the
   tickets into 2–4 themes (e.g. a feature area, a migration, a reliability
   push) — the themes become the Q1 bullets.

5. **Show the ticket list and draft Q1, then ask about Q2/Q3.** Q1 (proud
   contributions) is derivable from the tickets; Q2 (skills/growth) and Q3
   (support from People Leader) are not — the tickets only hint at them.
   Present a `AskUserQuestion` (or plain list if too long) with:
   - the grouped ticket list with the Q1 draft bullets, for approve-or-edit;
   - a *suggested* Q2 draft inferred from ticket types (new tech touched,
     migrations, new domains), marked clearly as a suggestion;
   - a direct question for Q3, since only the user knows what support they
     need.
   Wait for the user's answers before writing the file.

6. **Write the HTML.** Output to
   `~/netskope/note/performence/quarterly-review-<YYYY>Q<N>.html`.
   Bulleted answers are mandatory — the user pastes these into the
   review system and prose paragraphs don't fit. Use the dark-mode style the
   user's other notes use:

   ```html
   body { font: 15px/1.6 -apple-system, system-ui, "PingFang TC", "Microsoft JhengHei", sans-serif; max-width: 1040px; margin: 2rem auto; padding: 0 1rem; color: #d4d4d4; background: #1e1e1e; }
   ```

## Output format

Exactly this structure — keep the question text as headings so the file is
self-explanatory when revisited:

```html
<h1>Quarterly Review — 2026 Q3 (Johnny Hung)</h1>

<h2>Summary</h2>
<ul>
  <li>One bullet per Q1 theme, in plain prose without ticket keys — the
      highlight reel a reader can absorb in 20 seconds before the detail
      below.</li>
</ul>

<h2>1. What are 1-2 contributions or achievements that you're really proud of this quarter? How did these make an impact on your team, department, or Netskope as a whole?</h2>
<ul>
  <li><strong>Theme name</strong> — what was done, with ticket keys
      (ENG-XXXXXX) inline, and the impact (who it unblocked, what it
      improved). One bullet per theme, sub-bullets for individual tickets
      when the theme has several.</li>
</ul>

<h2>2. What new skills, knowledge, or habits did you develop this quarter? As you look ahead, what are 1-2 areas you're excited to keep growing or learning in?</h2>
<ul>
  <li>…</li>
</ul>

<h2>3. Heading into the next quarter, what kind of support from your People Leader would be most helpful to you?</h2>
<ul>
  <li>…</li>
</ul>
```

Write the content in English (the review system and People Leader read
English), keep bullets concrete — every Q1 bullet should name at least one
ticket key so the claim is verifiable. Never infer FedRAMP/compliance work as
a "skill developed" for Q2 just because FedRAMP-labeled tickets appear; Q2
suggestions should come from what the user visibly had to learn (new
technology, new systems, new process), not from ticket labels. Close with the
file path so the user can open it.
