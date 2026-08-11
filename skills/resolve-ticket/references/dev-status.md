# Reading the Jira Development panel

How to get a ticket's linked PRs when they aren't in the description or
comments. Needs `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` in the environment; if
unset, ask the user to paste the panel instead.

```bash
# 1. Summary — confirms the PR count and the applicationType to use.
#    Takes the issue's NUMERIC id, returned at the top level of the step-1
#    getJiraIssue response regardless of `fields` (e.g. 4037624) — don't re-fetch.
curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  "https://netskope.atlassian.net/rest/dev-status/1.0/issue/summary?issueId=<numeric-id>"

# 2. Detail — applicationType comes from summary's `byInstanceType` key,
#    normally `oAuth-com.github.integration.production`.
curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  "https://netskope.atlassian.net/rest/dev-status/1.0/issue/detail?issueId=<numeric-id>&applicationType=oAuth-com.github.integration.production&dataType=pullrequest"
```

Trust the summary's `pullrequest.overall.count`. If it's 0, skip the detail call.
A wrong `applicationType` (e.g. `GitHub`) returns `{"errors":[],"detail":[]}` with
**HTTP 200** — indistinguishable from "no PRs", so a non-zero count with an empty
detail response means the applicationType is wrong, not the ticket.

Once you have the PR numbers, read each one — `gh pr view <n> --repo
netSkope/<repo> --json title,body,files` — and reconcile them in merge order. A
ticket's final state is often several PRs deep: a later PR may retune, disable,
or revert what an earlier one shipped, and the last merged value is the one QA
must verify.
