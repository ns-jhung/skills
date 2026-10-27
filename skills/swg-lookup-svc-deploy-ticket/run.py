#!/usr/bin/env python3
"""Collect release info for swg-lookup-svc and create its ENG Deployment ticket.

  run.py collect                         -> JSON: latest tag, stg01 version, PRs, tickets
  run.py create --version V --tickets K1,K2 --date YYYY-MM-DD [--dry-run]
"""
import argparse
import base64
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "netSkope/swg-lookup-svc"
STG01_KUBECONFIG_NAME = "stork-stg01-mp-iad0-nc4"
STG01_KUBECONFIG = os.path.expanduser(f"~/.nsk/{STG01_KUBECONFIG_NAME}.yaml")
NAMESPACE = "swg-lookup-mp"
JIRA = "https://netskope.atlassian.net"
TICKET_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
PR_RE = re.compile(r"\(#(\d+)\)\s*$")

COMPONENT_ID = "28059"  # URL Security (URLSec)
ENGINEERING_VP = "5bfc7f8db203a71cc9cae4d9"  # Siying Yang
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "swg-lookup-svc-common"))
from schedule import BATCH_REGIONS, DATACENTERS, EVENTS, planned_dates

MONITORING_URL = "http://ui-prism.apps.netskope.io/goto/af61w62gt0ge8c?orgId=1"
MAINTENANCE_URL = "https://netskope.atlassian.net/wiki/x/EYF27gE"
# cc list appended at the end of the ticket description (from ENG-1358185)
CC_LIST = [
    {"accountId": "60d0c05fdae5670068d98063", "displayName": "Ana Acebal Spishock"},
    {"accountId": "712020:ceae21b9-723a-4918-91d1-41303dd0a518", "displayName": "Chuan-Che Yen"},
    {"accountId": "622ef2441dcf800070e7ee4e", "displayName": "Bill Wang"},
    {"accountId": "712020:f5c4462c-dc4c-4b67-b57a-545f5ade3fbf", "displayName": "Yao-Po Wang"},
    {"accountId": "712020:42e52160-3d4d-4b26-872f-d0b0cefa2507", "displayName": "CJ Yang"},
]


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def is_bot(login):
    # login suffix rule — catches User-typed bots like cicd-bot, where .type isn't "Bot"
    login = (login or "").lower()
    return login.endswith("-bot") or login.endswith("[bot]")


def latest_tag():
    r = sh(["gh", "release", "view", "-R", REPO, "--json", "tagName", "--jq", ".tagName"])
    if r.returncode != 0:
        sys.exit(f"gh release view failed: {r.stderr.strip()}")
    return r.stdout.strip()


def stg01_version():
    cmd = ["kubectl", "--kubeconfig", STG01_KUBECONFIG, "-n", NAMESPACE,
           "get", "deploy", "-l", "app=swg-lookup-svc",
           "-o", "jsonpath={.items[0].spec.template.spec.containers[0].image}"]
    sh(["nsk", "cluster", "kubeconfig", "-p", "npe", "-n", STG01_KUBECONFIG_NAME])
    r = sh(cmd)
    if r.returncode != 0:
        sys.exit(f"kubectl failed on stg01: {r.stderr.strip()[-500:]}")
    if ":" not in r.stdout:
        sys.exit(f"no swg-lookup-svc deployment found on stg01 (got {r.stdout.strip()!r})")
    return r.stdout.rsplit(":", 1)[1]


def compare_commits(base, head):
    r = sh(["gh", "api", "--paginate", f"repos/{REPO}/compare/{base}...{head}?per_page=100",
            "--jq", ".commits[] | {sha, login: .author.login, type: .author.type, "
                    "name: .commit.author.name, msg: .commit.message}"])
    if r.returncode != 0:
        sys.exit(f"gh compare failed: {r.stderr.strip()}")
    return [json.loads(line) for line in r.stdout.splitlines() if line.strip()]


def prs_in_range(base, head):
    """Non-bot commits between two tags, with each PR's Jira-validated ticket keys.

    Shared by collect() here and the update skill's sync_plan, so both agree
    on what shipped. Returns (prs, tickets, dropped_invalid, skipped_bot).
    """
    prs, skipped = [], 0
    for c in compare_commits(base, head):
        login = c["login"] or c["name"]
        if c["type"] == "Bot" or is_bot(login):
            skipped += 1
            continue
        title = c["msg"].splitlines()[0]
        pr = PR_RE.search(title)
        keys = TICKET_RE.findall(PR_RE.sub("", title))
        prs.append({"pr": int(pr.group(1)) if pr else None, "author": login,
                    "title": title, "tickets": keys})
    keys = [k for p in prs for k in p["tickets"]]
    valid = valid_ticket_keys(keys)
    for p in prs:
        p["tickets"] = [k for k in p["tickets"] if k in valid]
    return prs, [k for k in dict.fromkeys(keys) if k in valid], \
        sorted(set(keys) - valid), skipped


def collect():
    latest, stg01 = latest_tag(), stg01_version()
    out = {"latest_tag": latest, "stg01_version": stg01, "prs": [], "skipped_bot_prs": 0,
           "tickets": [], "dropped_invalid_tickets": []}
    if latest == stg01:
        print(json.dumps(out, indent=2))
        return
    out["prs"], out["tickets"], out["dropped_invalid_tickets"], out["skipped_bot_prs"] = \
        prs_in_range(stg01, latest)
    print(json.dumps(out, indent=2))


def jira(method, path, body=None):
    auth = base64.b64encode(
        f"{os.environ['ATLASSIAN_EMAIL']}:{os.environ['ATLASSIAN_API_TOKEN']}".encode()).decode()
    req = urllib.request.Request(
        JIRA + path, method=method, data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            return json.loads(data) if data else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"Jira {method} {path} -> {e.code}: {e.read().decode()[:1000]}")


def text(s, bold=False):
    node = {"type": "text", "text": s}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def para(*content):
    return {"type": "paragraph", "content": list(content)}


def heading(s, level):
    return {"type": "heading", "attrs": {"level": level}, "content": [text(s)]}


def bullets(items):
    return {"type": "bulletList",
            "content": [{"type": "listItem", "content": [para(text(i))]} for i in items]}


def cell(*content, header=False):
    return {"type": "tableHeader" if header else "tableCell", "content": list(content) or [para()]}


def link(url):
    return {"type": "text", "text": url, "marks": [{"type": "link", "attrs": {"href": url}}]}


def mention(user):
    return {"type": "mention", "attrs": {"id": user["accountId"], "text": "@" + user["displayName"]}}


def mentions(users, sep):
    return [n for u in users for n in (mention(u), text(sep))][:-1]


def valid_ticket_keys(keys):
    unique = list(dict.fromkeys(keys))
    if not unique:
        return set()
    body = {"jql": "key in (" + ",".join(unique) + ")", "fields": [],
            "maxResults": len(unique)}
    return {i["key"] for i in jira("POST", "/rest/api/3/search/jql", body).get("issues", [])}


def ticket_owners(keys, me):
    if not keys:
        return []
    body = {"jql": "key in (" + ",".join(keys) + ")", "fields": ["assignee", "reporter"],
            "maxResults": len(keys)}
    owners = {}
    for i in jira("POST", "/rest/api/3/search/jql", body).get("issues", []):
        f = i["fields"]
        owner = f["assignee"] or f["reporter"]
        if owner["accountId"] != me:
            owners.setdefault(owner["accountId"], owner)
    return list(owners.values())


def dependencies(owners):
    if not owners:
        return [bullets(["N/A"])]
    return [para(*mentions(owners, ", "),
                 text(" if there are any dependencies, please update here. e.g. nsproxy-xxx")),
            bullets(["N/A"])]


def cc_paragraph():
    return para(text("cc "), *mentions(CC_LIST, " "))


def date_node(day):
    utc = datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.timezone.utc)
    return {"type": "date", "attrs": {"timestamp": str(int(utc.timestamp() * 1000))}}


def description(version, owners, deploy_day):
    rows = [{"type": "tableRow", "content": [cell(para(text(h, True)), header=True)
                                             for h in ("Event", "Date", "Detail")]}]
    for event, offset, detail, pops in EVENTS:
        detail_cell = [para(text(detail, True))] if detail else []
        if pops:
            detail_cell.append(bullets(pops))
        rows.append({"type": "tableRow",
                     "content": [cell(para(text(event))), cell(para(date_node(deploy_day + datetime.timedelta(days=offset)))), cell(*detail_cell)]})
    return {"type": "doc", "version": 1, "content": [
        heading("Action Items", 2),
        bullets(["Deploy SWG-lookup-svc to all mp environments."]),
        heading("Dependencies", 2),
        *dependencies(owners),
        heading("Events", 2),
        {"type": "table", "attrs": {"isNumberColumnEnabled": False, "layout": "align-start"},
         "content": rows},
        heading("Deployment Info", 2),
        heading("Version", 3), bullets([version]),
        heading("Deploy Jenkins Jobs", 3), bullets(["Will leverage easy deployment"]),
        heading("Monitoring", 3), para(link(MONITORING_URL)),
        heading("Maintenance window", 3), para({"type": "inlineCard", "attrs": {"url": MAINTENANCE_URL}}),
        cc_paragraph(),
    ]}


def create(version, tickets, date, dry_run):
    deploy_day = datetime.date.fromisoformat(date)
    me = jira("GET", "/rest/api/3/myself")["accountId"]
    owners = ticket_owners(tickets, me)
    fields = {
        "project": {"key": "ENG"},
        "issuetype": {"name": "Deployment"},
        "summary": f"[swg-lookup-svc] deploy {version}",
        "description": description(version, owners, deploy_day),
        "components": [{"id": COMPONENT_ID}],
        "assignee": {"accountId": me},
        "customfield_20800": {"accountId": ENGINEERING_VP},
        "customfield_10004": 1,
        "customfield_17018": {"value": "Scheduled deployment"},
        "customfield_17280": [{"value": dc} for dc in DATACENTERS],
        "customfield_20803": [{"value": "No downtime / No inline impact / No customer action required"}],
        "customfield_20823": version,
        "customfield_23296": {"value": "No"},
        **planned_dates(deploy_day),
    }
    # The Deployment create validator rejects tickets without links, so add them in the same request.
    update = {"issuelinks": [{"add": {"type": {"name": "Relates"}, "outwardIssue": {"key": t}}}
                             for t in tickets]}
    if dry_run:
        print(json.dumps({"fields": fields, "update": update}, indent=2))
        return
    key = jira("POST", "/rest/api/3/issue", {"fields": fields, "update": update})["key"]
    print(f"created {key}: {JIRA}/browse/{key} with {len(tickets)} relates-to links")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect")
    c = sub.add_parser("create")
    c.add_argument("--version", required=True)
    c.add_argument("--tickets", default="")
    c.add_argument("--date", required=True, metavar="YYYY-MM-DD")
    c.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.cmd == "collect":
        collect()
    else:
        create(a.version, [t for t in a.tickets.split(",") if t],
               a.date, a.dry_run)


if __name__ == "__main__":
    main()
