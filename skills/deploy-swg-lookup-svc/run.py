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


def http(method, url, auth, *, data=None, retries=5):
    """HTTP request with retry on transient network failures.

    Returns (status, headers, body). HTTP 4xx/5xx are returned, not raised.
    """
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", auth)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read()
        except TRANSIENT as e:
            if attempt == retries - 1:
                sys.exit(f"error: {method} {url} failed after {retries} tries: {e}")
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
    if result != "SUCCESS":
        sys.exit(2)


if __name__ == "__main__":
    main()
