---
name: deploy-swg-lookup-svc-npe
description: Trigger the Jenkins job `one_button_swg-lookup-svc_helm` on cdjenkins.betaskope (NPE) to deploy swg-lookup-svc. Collects build parameters interactively, confirms with the user, kicks off the build, and polls the queue + build until it reaches a final status. Use when the user says things like "deploy swg-lookup-svc", "run the swg-lookup-svc helm job", "npe helm deploy swg-lookup-svc", or references the one_button_swg-lookup-svc_helm Jenkins job.
disable-model-invocation: false
argument-hint: [POPS=..] [RELEASE=..] [TICKET=..] [COMPONENT_NAME=..] [DEPLOY_TYPE=..] [OTHER=..]
allowed-tools: Bash(python3 *) Bash(bash -ic *) Read AskUserQuestion
---

Trigger and follow the Jenkins job `one_button_swg-lookup-svc_helm` at
`$NPE_JENKINS_URL/job/one_button_swg-lookup-svc_helm/` using the
helper script at `~/.claude/skills/deploy-swg-lookup-svc-npe/run.py`.

## Required env vars (read from user bashrc)

- `NPE_JENKINS_URL`
- `NPE_JENKINS_USER`
- `NPE_JENKINS_API_TOKEN`

These live in `~/.bashrc`. Because `~/.bashrc` early-returns for
non-interactive shells, run any Bash step via `bash -ic '...'` so the
vars are loaded.

## Job parameters

The Jenkins job defines many parameters. The ones that change per run
and that the user must supply:

| Parameter | Notes |
|---|---|
| `POPS` | Comma-separated pop list, e.g. `qa01`. Required. |
| `RELEASE` | swg-lookup-svc version to deploy, e.g. `v0.0.0-PR1352.5870`. Required. |
| `TICKET` | JIRA ticket `ENG-12345`. Required by job (unless BYPASS_JIRA=YES, which is the default). |
| `COMPONENT_NAME` | Component list, typically `swg-lookup-svc`. Required. |
| `DEPLOY_TYPE` | One of `DRYRUN_AND_DEPLOY` (default), `DRYRUN`, `DEPLOY`. |

Everything else has a sensible default baked into the job. The user
may override any of them — `VP_APPROVAL`, `VERBOSE`, `WAIT`,
`TIMEOUT`, `ATOMIC`, `CLUSTER_NAME`, `HELM_ARTIFACTORY_CHANNEL`,
`HELM_CHART_PATH`, `NAMESPACE`, `PDV_ARTIFACTORY_CHANNEL`,
`PDV_CONFIG_IMAGE_NAME`, `SLACK_CHANNEL`, `BYPASS_MONITORING_RESULT`,
`BYPASS_JIRA`, `RUN_QE_PDV`, `PDV_CONFIG_IMAGE_TAG`,
`SELECT_ALL_POPS`, `SELECT_ALL_COMPONENTS`, `REGIONS`, `POP_TYPES`.

### Defaults & conventions

- **TICKET: always `ENG-1`.** The job is configured with
  `BYPASS_JIRA=YES` so ticket validity isn't checked. Do not ask the
  user for a ticket unless they explicitly want to supply one.
- **POPS uses the full pop name**, matching the
  `netSkope/swg-github-workflow` deployment template's `pops.yml`.
  When the user gives a short alias, expand it before passing to Jenkins:
  - `qa01`   → `qa01-mp-npe-iad0-nc1` (cluster `c1`)
  - `hippo`  → `ch-hippo-local`       (cluster `c1`)
  - `stg01`  → `stg01-mp-iad0-nc4`    (cluster `c1`)
  - `fed1mp` → `fed1mp-iad0-nc1`      (cluster `c1`)
  - `perf01` → `perf01-mp-iad0-nc6`   (cluster `c1`)
  - `npa01`  → `npa01-mp-npe-iad0-nc1`(cluster `c1`)
  - `npe02`  → `npe02-mp-iad0-nc4`    (cluster `c1`)
- **qa01 is an MP pop**, not EKS. Namespace default `swg-lookup-mp` is correct.
- **HELM_ARTIFACTORY_CHANNEL** depends on RELEASE:
  - `v0.0.0-PR*`  → `dataplane-develop-helm`
  - anything else → `dataplane-release-helm` (NPE)
- **PDV_ARTIFACTORY_CHANNEL** for NPE → `dataplane-release-docker`
  (use `-develop-docker` only if the PDV tag itself is `v0.0.0-PR*`).
- **PDV_CONFIG_IMAGE_TAG** defaults to the latest release of
  `netSkope/swg-mp-pdv`:
  `gh release view --repo github.com/netSkope/swg-mp-pdv --json tagName --jq .tagName`
- **INSIGHTS_RELEASE_VERSION** defaults to `YYYY.MM` of today.
- **RUN_QE_PDV defaults to `DEPLOY_ONLY`** (user preference — skip PDV
  unless the user explicitly asks to run it). When `DEPLOY_ONLY`, also
  omit `PDV_ARTIFACTORY_CHANNEL`, `PDV_CONFIG_IMAGE_NAME`,
  `PDV_CONFIG_IMAGE_TAG` — let Jenkins use its own defaults.
- **SLACK_CHANNEL defaults to empty** (user preference — do not spam a
  channel unless the user explicitly asks). Omit the param entirely
  from the trigger.
- **Other fixed defaults**:
  `BYPASS_JIRA=YES`, `BYPASS_MONITORING_RESULT=YES`,
  `COMPONENT_NAME=swg-lookup-svc`.

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

1. **Gather params.** Parse any `KEY=VALUE` args the user provided
   upfront. For any of the five required params still missing, use
   `AskUserQuestion` to ask the user — one question per missing param,
   with known choices as options when the param is a Choice type.
   Example: for `DEPLOY_TYPE`, the options are `DRYRUN_AND_DEPLOY`,
   `DRYRUN`, `DEPLOY`. For free-text params (`POPS`, `RELEASE`,
   `TICKET`, `COMPONENT_NAME`) let the user type the value via the
   automatic "Other" slot or ask plainly.
2. **Confirm.** Show the final parameter set back to the user and ask
   for explicit confirmation before triggering. Never trigger without
   confirmation — this job touches real pops.
3. **Trigger + poll.** Call `run.py` with the chosen params. It:
   - POSTs to `/job/<job>/buildWithParameters`
   - Reads the `Location:` header → queue item URL
   - Polls queue until a `executable.number` appears
   - Polls `/job/<job>/<buildNumber>/api/json` until `building=false`
   - Prints final `result` (SUCCESS / FAILURE / ABORTED / UNSTABLE)
     and the console log URL.
4. **Report.** Relay the result and the console URL. If FAILURE, offer
   to tail the last ~200 lines of the console log.

## How to run the helper

```bash
bash -ic 'python3 ~/.claude/skills/deploy-swg-lookup-svc-npe/run.py \
  --param POPS=<...> \
  --param RELEASE=<...> \
  --param TICKET=ENG-<...> \
  --param COMPONENT_NAME=<...> \
  --param DEPLOY_TYPE=<...> \
  [--param KEY=VALUE ...] \
  --wait'
```

- `--wait` enables queue+build polling (always use this for this skill).
- `--dry-run` prints the resolved URL + params without POSTing (use
  during confirmation if the user wants to see the exact request).
- `--timeout-sec N` caps how long we poll (default 3600).

## Safety rules

- **Never** trigger a build without an explicit user "yes" in the
  current turn. A prior confirmation from an earlier turn does not
  carry over.
- If `DEPLOY_TYPE=DEPLOY` and `VP_APPROVAL=FALSE`, warn the user that
  the job may block outside dryrun without VP approval, and confirm
  they really want DEPLOY (not `DRYRUN_AND_DEPLOY`).
- Do not log the API token. If you need to show the curl equivalent,
  mask the auth: `-u "$NPE_JENKINS_USER:***"`.
