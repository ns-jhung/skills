---
name: deploy-swg-lookup-svc
description: Trigger the Jenkins job `one_button_swg-lookup-svc_helm` on either NPE (cdjenkins.betaskope) or PROD (cdjenkins.sjc1.nskope.net) to deploy swg-lookup-svc. Auto-infers env from POPS, collects build parameters interactively, confirms with the user, kicks off the build, and polls the queue + build until it reaches a final status. Use when the user says things like "deploy swg-lookup-svc", "run the swg-lookup-svc helm job", "npe/prod helm deploy swg-lookup-svc", or references the one_button_swg-lookup-svc_helm Jenkins job.
disable-model-invocation: false
argument-hint: [ENV=npe|prod] [POPS=..] [RELEASE=..] [TICKET=..] [COMPONENT_NAME=..] [DEPLOY_TYPE=..] [OTHER=..]
allowed-tools: Bash(python3 *) Bash(bash -ic *) Read AskUserQuestion
---

Trigger and follow the Jenkins job `one_button_swg-lookup-svc_helm` on
either NPE or PROD using the helper script at
`${CLAUDE_PLUGIN_ROOT}/skills/deploy-swg-lookup-svc/run.py`.

- NPE: `$NPE_JENKINS_URL/job/one_button_swg-lookup-svc_helm/`
- PROD: `$PROD_JENKINS_URL/job/one_button_swg-lookup-svc_helm/`

## Required env vars (read from user bashrc)

Per environment:

- `ENV=npe` → `NPE_JENKINS_URL`, `NPE_JENKINS_USER`, `NPE_JENKINS_API_TOKEN`
- `ENV=prod` → `PROD_JENKINS_URL`, `PROD_JENKINS_USER`, `PROD_JENKINS_API_TOKEN`

These live in `~/.bashrc`. Because `~/.bashrc` early-returns for
non-interactive shells, run any Bash step via `bash -ic '...'` so the
vars are loaded.

## Job parameters

The Jenkins job defines many parameters. The ones that change per run
and that the user must supply:

| Parameter | Notes |
|---|---|
| `ENV` | `npe` (default) or `prod`. Auto-inferred from POPS when possible (see below). |
| `POPS` | Comma-separated pop list, e.g. `qa01` (npe) or `sjc1` (prod). Required. |
| `RELEASE` | swg-lookup-svc version to deploy, e.g. `v0.0.0-PR1352.5870` (npe-only) or `v1.2.3`. Required. |
| `TICKET` | JIRA ticket. Required — always ask the user. |
| `COMPONENT_NAME` | Component list, typically `swg-lookup-svc`. Required. |
| `DEPLOY_TYPE` | One of `DRYRUN_AND_DEPLOY` (default), `DRYRUN`, `DEPLOY`. |

Everything else has a sensible default baked into the job. The user
may override any of them — `VERBOSE`, `WAIT`, `TIMEOUT`, `ATOMIC`,
`CLUSTER_NAME`, `HELM_ARTIFACTORY_CHANNEL`, `HELM_CHART_PATH`,
`NAMESPACE`, `PDV_ARTIFACTORY_CHANNEL`, `PDV_CONFIG_IMAGE_NAME`,
`SLACK_CHANNEL`, `BYPASS_MONITORING_RESULT`, `BYPASS_JIRA`,
`RUN_QE_PDV`, `PDV_CONFIG_IMAGE_TAG`, `SELECT_ALL_POPS`,
`SELECT_ALL_COMPONENTS`, `REGIONS`, `POP_TYPES`.

### Defaults & conventions

- **TICKET: required, no default.** Always ask the user for the JIRA
  ticket via `AskUserQuestion` — do not fall back to `ENG-1` or any
  other value. The job runs with `BYPASS_JIRA=YES` so the ticket
  isn't validated, but we still want a real ticket on the build
  record for traceability.
- **POPS uses the full pop name**, matching the `pops.yml` block in
  `netSkope/swg-github-workflow/.github/workflows/deployment.yml`
  (source of truth for alias → full-name + cluster). When the user
  gives a short alias, expand it before passing to Jenkins. Aliases
  also determine env auto-inference:

  | Alias | Full name | Cluster | Env |
  |---|---|---|---|
  | `qa01` | `qa01-mp-npe-iad0-nc1` | c1 | npe |
  | `stg01` | `stg01-mp-iad0-nc4` | c1 | npe |
  | `fed1` | `fed1mp-iad0-nc1` | c1 | npe |
  | `perf01` | `perf01-mp-iad0-nc6` | c1 | npe |
  | `hippo` | `ch-hippo-local` | c1 | npe |
  | `sjc1` | `sjc1` | c4 | prod |
  | `sjc2` | `sjc2` | c1 | prod |
  | `am2` | `am2` | c4 | prod |
  | `dfw3` | `dfw3` | c1 | prod |
  | `fr4` | `fr4` | c4 | prod |
  | `fra2` | `fra2` | c1 | prod |
  | `lon3` | `lon3` | c1 | prod |
  | `mel2` | `mel2` | c1 | prod |
  | `ruh1` | `ruh1` | c1 | prod |
  | `sin2` | `sin2` | c1 | prod |
  | `sv5` | `sv5` | c1 | prod |
  | `zur2` | `zur2` | c1 | prod |
  | `bom3` | `bom3` | c1 | prod |

- **ENV auto-inference**: parse POPS aliases. If all are prod → `ENV=prod`.
  If all are npe → `ENV=npe`. If mixed or unknown → ask the user.
- **CLUSTER_NAME is per-pop and the job runs against one cluster.**
  Look up each pop's cluster (`c1` or `c4`) in the alias table. If the
  user's POPS list spans multiple clusters (e.g. `sin2` is c1 and
  `fr4` is c4), **split the request into one Jenkins build per
  cluster**. Each build sends its own `POPS=<pops-in-that-cluster>`
  and `CLUSTER_NAME=<c1|c4>`. Do not attempt to send a mixed-cluster
  POPS list in a single build — Jenkins won't accept it.
- **HELM_ARTIFACTORY_CHANNEL** depends on env and RELEASE:
  - `ENV=prod` → always `dataplane-production-helm`
  - `ENV=npe`, `v0.0.0-PR*` → `dataplane-develop-helm`
  - `ENV=npe`, anything else → `dataplane-release-helm`
- **PDV_ARTIFACTORY_CHANNEL** (only relevant if `RUN_QE_PDV != DEPLOY_ONLY`):
  - `ENV=prod` → `dataplane-production-docker`
  - `ENV=npe`, PDV tag `v0.0.0-PR*` → `dataplane-develop-docker`
  - `ENV=npe`, anything else → `dataplane-release-docker`
- **PDV_CONFIG_IMAGE_TAG** defaults to the latest release of
  `netSkope/swg-mp-pdv`:
  `gh release view --repo github.com/netSkope/swg-mp-pdv --json tagName --jq .tagName`
- **INSIGHTS_RELEASE_VERSION** defaults to `YYYY.MM` of today.
- **RUN_QE_PDV defaults to `DEPLOY_ONLY`** on both envs (user
  preference — skip PDV unless the user explicitly asks to run it).
  When `DEPLOY_ONLY`, also omit `PDV_ARTIFACTORY_CHANNEL`,
  `PDV_CONFIG_IMAGE_NAME`, `PDV_CONFIG_IMAGE_TAG` — let Jenkins use
  its own defaults.
- **SLACK_CHANNEL defaults to empty** (user preference — do not spam a
  channel unless the user explicitly asks). Omit the param entirely
  from the trigger.
- **Other fixed defaults**:
  `BYPASS_JIRA=YES`, `BYPASS_MONITORING_RESULT=NO`,
  `COMPONENT_NAME=swg-lookup-svc`.

### Prod guardrails (mirror `swg-github-workflow`)

These match the deployment workflow's own checks; refuse to trigger
client-side rather than letting Jenkins reject the build.

- If `ENV=prod` and `RELEASE` matches `v0.0.0-PR*` → refuse.
  Reason: the upstream workflow errors with "Cannot deploy to prod
  with pull-request build".
- If `ENV=prod`, `RUN_QE_PDV != DEPLOY_ONLY`, and `PDV_CONFIG_IMAGE_TAG`
  matches `v0.0.0-PR*` → refuse. Reason: workflow errors with "Cannot
  deploy to prod with pull-request built PDV".

### Why no cascade option scraping

Jenkins' `POPS` and `COMPONENT_NAME` are Active Choices cascade
parameters, whose option lists are populated via a session-bound
stapler proxy (not exposed over REST). The Jenkins web UI is also
behind Netskope SSO, so basic auth with an API token cannot render the
build form for scraping. Conclusion: pass `POPS` / `COMPONENT_NAME` as
free-text strings and let Jenkins validate on build trigger — if the
value isn't in the cascade, the build will be rejected and the error
message returned via the API.

## Workflow

1. **Resolve ENV.** Parse any `KEY=VALUE` args. If `ENV` not given,
   try to auto-infer from POPS aliases (all-prod → `prod`, all-npe →
   `npe`). If POPS is missing, mixed, or contains unknown aliases,
   ask the user with `AskUserQuestion`.
2. **Gather params.** For any of the five required params still
   missing (`POPS`, `RELEASE`, `TICKET`, `COMPONENT_NAME`,
   `DEPLOY_TYPE`), use `AskUserQuestion` — one question per missing
   param, with known choices as options when the param is a Choice
   type. For free-text params let the user type via the automatic
   "Other" slot or ask plainly.
3. **Validate prod guardrails.** Apply the prod-specific rules above.
   If a guardrail trips, surface the error and stop — do not prompt
   to bypass.
4. **Group POPS by cluster.** Look up each pop in the alias table and
   group by `c1` / `c4`. Each cluster group becomes its own Jenkins
   build with `CLUSTER_NAME=<c1|c4>` and `POPS=<comma-joined pops in
   that cluster>`. Default sequencing is sequential (one cluster at a
   time, abort if the first fails); ask the user if they prefer
   parallel.
5. **Confirm.** Show the final parameter set for **each** build
   (including `ENV`, `CLUSTER_NAME`, and the target Jenkins URL) and
   ask for explicit confirmation before triggering. Never trigger
   without confirmation — this job touches real pops.
6. **Trigger + poll.** For each cluster group, call `run.py` with
   `--env <npe|prod>` and the chosen params. It:
   - POSTs to `/job/<job>/buildWithParameters`
   - Reads the `Location:` header → queue item URL
   - Polls queue until a `executable.number` appears
   - Polls `/job/<job>/<buildNumber>/api/json` until `building=false`
   - Prints final `result` (SUCCESS / FAILURE / ABORTED / UNSTABLE)
     and the console log URL.
7. **Report.** Relay the result and the console URL for each build.
   If FAILURE, offer to tail the last ~200 lines of the console log;
   if running sequentially, do not start the next cluster's build.

## How to run the helper

```bash
bash -ic 'python3 "${CLAUDE_PLUGIN_ROOT}/skills/deploy-swg-lookup-svc/run.py" \
  --env <npe|prod> \
  --param POPS=<pops-in-this-cluster> \
  --param CLUSTER_NAME=<c1|c4> \
  --param RELEASE=<...> \
  --param TICKET=ENG-<...> \
  --param COMPONENT_NAME=<...> \
  --param DEPLOY_TYPE=<...> \
  [--param KEY=VALUE ...] \
  --wait'
```

- `--env` selects which `*_JENKINS_*` env-var triple to use. Defaults
  to `npe`.
- `--wait` enables queue+build polling (always use this for this skill).
- `--dry-run` prints the resolved URL + params without POSTing (use
  during confirmation if the user wants to see the exact request).
- `--timeout-sec N` caps how long we poll (default 3600).

## Safety rules

- **Never** trigger a build without an explicit user "yes" in the
  current turn. A prior confirmation from an earlier turn does not
  carry over.
- For `ENV=prod`, the prod guardrails above are non-negotiable. Don't
  offer a workaround if `RELEASE` or `PDV_CONFIG_IMAGE_TAG` is a PR
  build — tell the user to use a real release version instead.
- Do not log the API token. If you need to show the curl equivalent,
  mask the auth: `-u "$<ENV>_JENKINS_USER:***"`.
