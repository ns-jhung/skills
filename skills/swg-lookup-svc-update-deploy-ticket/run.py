#!/usr/bin/env python3
"""Update an existing ENG Deployment Jira ticket.

  run.py show   ENG-XXXXXX
  run.py update ENG-XXXXXX [--date YYYY-MM-DD] [--version TAG]
                           [--add-tickets K1,K2] [--remove-tickets K1,K2]
                           [--comment TEXT] [--dry-run]

--date moves the prod deploy date and reschedules every region's planned
start/end from the shared schedule in swg-lookup-svc-common/schedule.py — the
same constants swg-lookup-svc-deploy-ticket uses at create time, so an update
stays consistent with the original schedule.
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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "swg-lookup-svc-common"))
from schedule import PLANNED_FIELDS, planned_dates


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


def update(key, date, version, add, remove, comment, dry_run):
    it = jira("GET", f"/rest/api/3/issue/{key}?fields=issuetype")["fields"]["issuetype"]["name"]
    if it != "Deployment":
        sys.exit(f"{key} is a {it}, not a Deployment ticket — refusing to update")
    fields = {}
    if date:
        fields.update(planned_dates(datetime.date.fromisoformat(date)))
    if version:
        fields["customfield_20823"] = version
    update_ops = {"issuelinks":
        [{"add": {"type": {"name": "Relates"}, "outwardIssue": {"key": t}}} for t in add] +
        [{"remove": {"type": {"name": "Relates"}, "outwardIssue": {"key": t}}} for t in remove]}
    if not fields and not add and not remove:
        sys.exit("nothing to update")
    if dry_run:
        print(json.dumps({"fields": fields, "update": update_ops,
                          **({"comment": comment} if comment else {})}, indent=2))
        return
    jira("PUT", f"/rest/api/3/issue/{key}", {"fields": fields, "update": update_ops})
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
    else:
        update(a.key, a.date, a.version,
               [t for t in a.add_tickets.split(",") if t],
               [t for t in a.remove_tickets.split(",") if t],
               a.comment, a.dry_run)


if __name__ == "__main__":
    main()
