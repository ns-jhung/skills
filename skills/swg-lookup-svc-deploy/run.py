#!/usr/bin/env python3
"""Trigger the `one_button_swg-lookup-svc_helm` Jenkins job on NPE or
PROD and wait for it to finish. Reads credentials from env vars
selected by --env:

  --env npe  → NPE_JENKINS_URL,  NPE_JENKINS_USER,  NPE_JENKINS_API_TOKEN
  --env prod → PROD_JENKINS_URL, PROD_JENKINS_USER, PROD_JENKINS_API_TOKEN
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

JOB_PATH = "job/one_button_swg-lookup-svc_helm"
REQUIRED = ["POPS", "RELEASE", "TICKET", "COMPONENT_NAME", "DEPLOY_TYPE"]
TRANSIENT = (urllib.error.URLError, TimeoutError, ConnectionError, OSError)

# Full pop name (as passed in POPS to Jenkins) → kubeconfig basename under ~/.nsk/.
# Keys match the expanded names from the SKILL.md alias table, not the short aliases.
POP_KUBECONFIG = {
    "qa01-mp-npe-iad0-nc1": "stork-qa01-mp-npe-iad0-nc1",
    "stg01-mp-iad0-nc4": "stork-stg01-mp-iad0-nc4",
    "fed1mp-iad0-nc1": "stork-fed1mp-iad0-nc1",
    "perf01-mp-iad0-nc6": "stork-perf01-mp-iad0-nc6",
    "ch-hippo-local": "ch-hippo-local",
    "devint-automation-iad0-nc1": "stork-devint-automation-iad0-nc1",
    "sjc1": "c4-sjc1",
    "sjc2": "stork-sjc2-mp-prod-sjc2-nc1",
    "am2": "c4-am2",
    "dfw3": "stork-dfw3-mp-prod-dfw3-nc1",
    "fr4": "c4-fr4",
    "fra2": "stork-fra2-mp-prod-fra2-nc1",
    "lon3": "stork-lon3-mp-prod-lon3-nc1",
    "mel2": "stork-mel2-mp-mel2-nc1",
    "ruh1": "stork-ruh1-mp-prod-ruh1-nc1",
    "sin2": "stork-sin2-mp-prod-sin2-nc1",
    "sv5": "c1-sv5",
    "zur2": "stork-zur2-mp-prod-zur2-nc1",
    "bom3": "stork-bom3-mp-prod-bom3-nc1",
}


def pop_to_kubeconfig(pop):
    """Return kubeconfig basename for a full pop name, or '<unknown-pop>' if not mapped."""
    return POP_KUBECONFIG.get(pop.lower(), f"<unknown-{pop}>")


def http(method, url, auth, *, data=None, retries=5):
    """HTTP request. Retries transient failures only for idempotent methods.

    POST is never retried: a network timeout doesn't prove Jenkins rejected
    the request, and retrying can queue a duplicate build. Caller must
    handle POST failures manually.

    Returns (status, headers, body). HTTP 4xx/5xx are returned, not raised.
    """
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", auth)
    effective_retries = 1 if method == "POST" else retries
    for attempt in range(effective_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read()
        except TRANSIENT as e:
            if attempt == effective_retries - 1:
                sys.exit(
                    f"error: {method} {url} failed: {e}\n"
                    + ("note: POST is not retried automatically to avoid duplicate builds. "
                       "Check Jenkins build history to see if the job was already queued before retrying."
                       if method == "POST" else f"({effective_retries} attempts)")
                )
            print(f"retrying {method} ({e})", flush=True)
            time.sleep(5)


def trigger(base, auth, params):
    url = f"{base}/{JOB_PATH}/buildWithParameters"
    status, headers, body = http("POST", url, auth, data=urllib.parse.urlencode(params).encode())
    if status not in (200, 201):
        sys.exit(f"error: buildWithParameters HTTP {status}\n{body.decode(errors='replace')[:500]}")
    loc = headers.get("Location") or headers.get("location")
    if not loc:
        sys.exit("error: Jenkins did not return a queue Location header")
    return loc.rstrip("/")


def poll(url, auth, deadline, interval, done):
    """Poll `url` every `interval` seconds until `done(json)` is truthy.

    `done(d)` returns a value when finished — that value is returned here.
    Returning None (or falsy) means "keep polling".
    """
    while time.time() < deadline:
        status, _, body = http("GET", url, auth)
        if status == 200:
            result = done(json.loads(body))
            if result is not None:
                return result
        else:
            print(f"poll HTTP {status}; retrying", flush=True)
        time.sleep(interval)
    sys.exit(f"error: timed out polling {url}")


def queue_done(d):
    if d.get("cancelled"):
        sys.exit("error: queue item cancelled: " + (d.get("why") or ""))
    ex = d.get("executable")
    if ex and ex.get("number"):
        return int(ex["number"])
    print(f"queued: {d.get('why') or 'waiting'}", flush=True)


def build_done(d):
    print(f"building={d.get('building')} result={d.get('result')}", flush=True)
    return d if not d.get("building") else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=("npe", "prod"), default="npe", help="Target Jenkins environment")
    ap.add_argument("--param", action="append", default=[], help="KEY=VALUE (repeatable)")
    ap.add_argument("--wait", action="store_true", help="Poll queue + build until done")
    ap.add_argument("--dry-run", action="store_true", help="Print request and exit")
    ap.add_argument("--timeout-sec", type=int, default=3600)
    args = ap.parse_args()

    prefix = args.env.upper()
    keys = (f"{prefix}_JENKINS_URL", f"{prefix}_JENKINS_USER", f"{prefix}_JENKINS_API_TOKEN")
    env = {k: os.environ.get(k) for k in keys}
    missing_env = [k for k, v in env.items() if not v]
    if missing_env:
        sys.exit(f"error: env vars not set: {', '.join(missing_env)} (source ~/.bashrc)")
    base = env[keys[0]].rstrip("/")
    user = env[keys[1]]
    auth = "Basic " + base64.b64encode(f"{user}:{env[keys[2]]}".encode()).decode()

    params = {}
    for item in args.param:
        if "=" not in item:
            sys.exit(f"error: --param expects KEY=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        params[k.strip()] = v
    missing = [k for k in REQUIRED if not params.get(k)]
    if missing:
        sys.exit("error: missing required params: " + ", ".join(missing))

    print(f"env : {args.env}")
    print(f"job : {base}/{JOB_PATH}/")
    print(f"user: {user}")
    print("params:")
    for k in sorted(params):
        print(f"  {k} = {params[k]}")

    if args.dry_run:
        print("(dry-run; not triggering)")
        return

    queue_url = trigger(base, auth, params)
    print(f"queued: {queue_url}")
    if not args.wait:
        return

    deadline = time.time() + args.timeout_sec
    build_number = poll(f"{queue_url}/api/json", auth, deadline, 5, queue_done)
    build_url = f"{base}/{JOB_PATH}/{build_number}"
    print(f"build  : {build_url}")
    print(f"console: {build_url}/console")

    info = poll(f"{build_url}/api/json", auth, deadline, 15, build_done)
    result = info.get("result") or "UNKNOWN"
    print(f"\nRESULT: {result}")
    print(f"console: {build_url}/console")

    pops = [p.strip() for p in params["POPS"].split(",") if p.strip()]
    release = params["RELEASE"]
    print("\nVerify deployed image tag per pop (run yourself):")
    for pop in pops:
        kubeconfig = f"~/.nsk/{pop_to_kubeconfig(pop)}.yaml"
        print(
            f"  KUBECONFIG={kubeconfig} kubectl -n swg-lookup-mp get pods "
            f"-o jsonpath='{{range .items[*]}}{{.metadata.name}} "
            f"{{.spec.containers[*].image}}{{\"\\n\"}}{{end}}'  # expect tag {release}"
        )

    if result != "SUCCESS":
        sys.exit(2)


if __name__ == "__main__":
    main()
