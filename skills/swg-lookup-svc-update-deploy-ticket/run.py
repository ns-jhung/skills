#!/usr/bin/env python3
"""Update an existing ENG Deployment Jira ticket.

  run.py show   ENG-XXXXXX
  run.py collect ENG-XXXXXX
  run.py update ENG-XXXXXX [--date YYYY-MM-DD] [--version TAG]
                           [--add-tickets K1,K2] [--remove-tickets K1,K2]
                           [--comment TEXT] [--dry-run]

--date moves the prod deploy date and reschedules every region's planned
start/end from the shared schedule in swg-lookup-svc-common/schedule.py — the
same constants swg-lookup-svc-deploy-ticket uses at create time, so an update
stays consistent with the original schedule.

collect diffs the ticket's Release Version against the latest GitHub release
tag and lists the PRs in that range plus the tickets from them that aren't
linked yet — the version/link sync every update applies.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

JIRA = "https://netskope.atlassian.net"

import datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "swg-lookup-svc-common"))
from schedule import PLANNED_FIELDS, planned_dates

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "deploy_ticket", os.path.join(HERE, "..", "swg-lookup-svc-deploy-ticket", "run.py"))
_deploy_ticket = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_deploy_ticket)


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


def show(key):
    fields = ["summary", "status", "issuetype", "issuelinks", "customfield_20823", *PLANNED_FIELDS]
    issue = jira("GET", f"/rest/api/3/issue/{key}?fields={','.join(fields)}")
    f = issue["fields"]
    related = [l.get("outwardIssue") or l.get("inwardIssue") for l in f["issuelinks"]
               if l["type"]["name"] == "Relates"]
    print(json.dumps({
        "key": issue["key"],
        "issuetype": f["issuetype"]["name"],
        "summary": f["summary"],
        "status": f["status"]["name"],
        "release_version": f["customfield_20823"],
        "planned": {k: f[k] for k in PLANNED_FIELDS if f.get(k)},
        "related_links": sorted(i["key"] for i in related if i),
    }, indent=2))


def sync_plan(key):
    """Diff the ticket's version/links against the latest release tag.

    Returns (issuetype, current_version, latest_tag, add_tickets, prs) —
    update applies latest_tag plus add_tickets to bring the ticket in sync;
    when current == latest there is nothing to sync.
    """
    fields = ["issuetype", "issuelinks", "customfield_20823"]
    issue = jira("GET", f"/rest/api/3/issue/{key}?fields={','.join(fields)}")
    f = issue["fields"]
    it = f["issuetype"]["name"]
    current = f["customfield_20823"]
    related = [l.get("outwardIssue") or l.get("inwardIssue") for l in f["issuelinks"]
               if l["type"]["name"] == "Relates"]
    linked = {i["key"] for i in related if i}

    prs = []
    add = []
    latest = _deploy_ticket.latest_tag()
    if current != latest:
        for c in _deploy_ticket.compare_commits(current, latest):
            login = c["login"] or c["name"]
            if c["type"] == "Bot" or (c["type"] is None and _deploy_ticket.is_bot(login)):
                continue
            title = c["msg"].splitlines()[0]
            pr = _deploy_ticket.PR_RE.search(title)
            keys = _deploy_ticket.TICKET_RE.findall(_deploy_ticket.PR_RE.sub("", title))
            prs.append({"pr": int(pr.group(1)) if pr else None, "author": login,
                        "title": title, "tickets": keys})
        keys = [k for p in prs for k in p["tickets"]]
        valid = _deploy_ticket.valid_ticket_keys(keys)
        for p in prs:
            p["tickets"] = [k for k in p["tickets"] if k in valid]
        add = [k for k in dict.fromkeys(keys) if k in valid and k not in linked]
    return it, current, latest, add, prs


def collect(key):
    it, current, latest, add, prs = sync_plan(key)
    print(json.dumps({
        "key": key,
        "current_version": current,
        "latest_tag": latest,
        "tickets_to_add": add,
        "prs": prs,
    }, indent=2))


def update(key, date, version, add, remove, comment, dry_run):
    it, current, latest, sync_add, prs = sync_plan(key)
    if it != "Deployment":
        sys.exit(f"{key} is a {it}, not a Deployment ticket — refusing to update")
    # Always sync the version and relates-to links to the latest release tag.
    if not version:
        version = latest
    elif version != latest:
        sys.exit(f"--version {version} is not the latest release tag ({latest})")
    add = list(dict.fromkeys(sync_add + add))
    fields = {}
    if date:
        fields.update(planned_dates(datetime.date.fromisoformat(date)))
    if version:
        fields["customfield_20823"] = version
    if not fields and not add and not remove and not comment:
        sys.exit("nothing to update")
    # Jira rejects more than one issuelinks operation per request, so add and
    # remove links one at a time.
    remove = [t for t in remove if t not in add]
    if dry_run:
        print(json.dumps({"fields": fields,
                          "add_links": add, "remove_links": remove,
                          **({"comment": comment} if comment else {})}, indent=2))
        return
    for link_ops in ([{"add": {"type": {"name": "Relates"}, "outwardIssue": {"key": t}}} for t in add] +
                     [{"remove": {"type": {"name": "Relates"}, "outwardIssue": {"key": t}}} for t in remove]):
        jira("PUT", f"/rest/api/3/issue/{key}",
             {"fields": fields, "update": {"issuelinks": [link_ops]}} if fields else
             {"update": {"issuelinks": [link_ops]}})
    if fields and not add and not remove:
        jira("PUT", f"/rest/api/3/issue/{key}", {"fields": fields})
    if comment:
        jira("POST", f"/rest/api/3/issue/{key}/comment",
             {"body": {"type": "doc", "version": 1, "content": [
                 {"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}})
    print(f"updated {key}: {JIRA}/browse/{key}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("key")
    c = sub.add_parser("collect")
    c.add_argument("key")
    u = sub.add_parser("update")
    u.add_argument("key")
    u.add_argument("--date", metavar="YYYY-MM-DD")
    u.add_argument("--version")
    u.add_argument("--add-tickets", default="", metavar="K1,K2")
    u.add_argument("--remove-tickets", default="", metavar="K1,K2")
    u.add_argument("--comment")
    u.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.cmd == "show":
        show(a.key)
    elif a.cmd == "collect":
        collect(a.key)
    else:
        update(a.key, a.date, a.version,
               [t for t in a.add_tickets.split(",") if t],
               [t for t in a.remove_tickets.split(",") if t],
               a.comment, a.dry_run)


if __name__ == "__main__":
    main()
