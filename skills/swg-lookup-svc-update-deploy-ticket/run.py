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
tag and lists the PRs in that range (bot commits filtered the same way the
creation skill does) plus the tickets from them that aren't linked yet — the
version/link sync every update applies. When the summary names a different
version, the sync also rewrites the summary and the description (Version
bullet + Dependencies mentions for newly linked ticket owners).
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
from schedule import BATCH_REGIONS, PLANNED_FIELDS, planned_dates

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


# batch1's start field — the prod deploy date is its date part
BATCH1_START = BATCH_REGIONS["batch1"][1][0][0]


def mentioned_users(doc):
    """Ordered deduped @mentions in a description doc, as {accountId, displayName}."""
    out, seen = [], set()
    for p in doc.get("content", []):
        if p.get("type") == "paragraph":
            for n in p.get("content", []):
                if n.get("type") == "mention" and n["attrs"]["id"] not in seen:
                    seen.add(n["attrs"]["id"])
                    out.append({"accountId": n["attrs"]["id"],
                                "displayName": n["attrs"].get("text", "").lstrip("@")})
    return out


def remove_link(key, ticket):
    links = jira("GET", f"/rest/api/3/issue/{key}?fields=issuelinks")["fields"]["issuelinks"]
    for l in links:
        if l["type"]["name"] != "Relates":
            continue
        other = l.get("outwardIssue") or l.get("inwardIssue")
        if other and other["key"] == ticket:
            jira("DELETE", f"/rest/api/3/issueLink/{l['id']}")
            return
    sys.exit(f"no Relates link between {key} and {ticket} found")


def show(key):
    fields = ["summary", "status", "issuetype", "issuelinks", "customfield_20823",
              "description", *PLANNED_FIELDS]
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
        "mentioned_users": sorted(u["accountId"] for u in mentioned_users(f.get("description") or {})),
    }, indent=2))


def sync_plan(key):
    """Diff the ticket's version/links against the latest release tag.

    Returns a plan dict — update applies latest_tag plus add_tickets to bring
    the ticket in sync; when current == latest there is nothing to sync.
    summary/mentioned/deploy_day feed the summary+description rewrite.
    """
    fields = ["issuetype", "issuelinks", "customfield_20823", "summary",
              "description", BATCH1_START]
    issue = jira("GET", f"/rest/api/3/issue/{key}?fields={','.join(fields)}")
    f = issue["fields"]
    current = f["customfield_20823"]
    related = [l.get("outwardIssue") or l.get("inwardIssue") for l in f["issuelinks"]
               if l["type"]["name"] == "Relates"]
    linked = {i["key"] for i in related if i}
    # the batch1 start stores the UTC+8 day, so its date part is the prod deploy date
    deploy_day = (f.get(BATCH1_START) or "")[:10] or None

    add, prs = [], []
    latest = _deploy_ticket.latest_tag()
    if current != latest:
        prs, tickets, _, _ = _deploy_ticket.prs_in_range(current, latest)
        add = [k for k in tickets if k not in linked]
    return {"issuetype": f["issuetype"]["name"], "current": current,
            "summary": f["summary"], "latest": latest, "mentioned": mentioned_users(
                f.get("description") or {}),
            "deploy_day": deploy_day, "add": add, "prs": prs}


def collect(key):
    plan = sync_plan(key)
    print(json.dumps({
        "key": key,
        "current_version": plan["current"],
        "latest_tag": plan["latest"],
        "tickets_to_add": plan["add"],
        "prs": plan["prs"],
    }, indent=2))


def update(key, date, version, add, remove, comment, dry_run):
    plan = sync_plan(key)
    if plan["issuetype"] != "Deployment":
        sys.exit(f"{key} is a {plan['issuetype']}, not a Deployment ticket — refusing to update")
    # Always sync the version and relates-to links to the latest release tag.
    if not version:
        version = plan["latest"]
    elif version != plan["latest"]:
        sys.exit(f"--version {version} is not the latest release tag ({plan['latest']})")
    add = list(dict.fromkeys(plan["add"] + add))
    fields = {}
    if date:
        fields.update(planned_dates(datetime.date.fromisoformat(date)))
    if version != plan["current"]:
        fields["customfield_20823"] = version
    if plan["summary"] != f"[swg-lookup-svc] deploy {version}":
        # Summary still names another version — rewrite summary and description
        # with the creation helpers so the Version bullet and the Dependencies
        # mentions (owners of newly linked tickets) match the new version.
        if not (date or plan["deploy_day"]):
            sys.exit("no planned batch1 date to rebuild the description from")
        deploy_day = datetime.date.fromisoformat(date or plan["deploy_day"])
        me = jira("GET", "/rest/api/3/myself")["accountId"] if add else None
        cc_ids = {u["accountId"] for u in _deploy_ticket.CC_LIST}
        owners = [u for u in plan["mentioned"]
                  if u["accountId"] not in cc_ids and u["displayName"]]
        owner_ids = {u["accountId"] for u in owners}
        for u in _deploy_ticket.ticket_owners(add, me):
            if u["accountId"] not in owner_ids and u["accountId"] not in cc_ids:
                owners.append(u)
                owner_ids.add(u["accountId"])
        fields["summary"] = f"[swg-lookup-svc] deploy {version}"
        fields["description"] = _deploy_ticket.description(version, owners, deploy_day)
    if not fields and not add and not remove and not comment:
        sys.exit("nothing to update")
    # Links are added via issue PUT (one issuelinks op per request) and removed
    # via DELETE /issueLink/{id} — removeRelates needs delete-issue permission.
    remove = [t for t in remove if t not in add]
    if dry_run:
        print(json.dumps({"fields": fields,
                          "add_links": add, "remove_links": remove,
                          **({"comment": comment} if comment else {})}, indent=2))
        return
    link_ops = [{"add": {"type": {"name": "Relates"}, "outwardIssue": {"key": t}}} for t in add]
    if fields and link_ops:
        jira("PUT", f"/rest/api/3/issue/{key}",
             {"fields": fields, "update": {"issuelinks": [link_ops[0]]}})
        link_ops = link_ops[1:]
    elif fields:
        jira("PUT", f"/rest/api/3/issue/{key}", {"fields": fields})
    for op in link_ops:
        jira("PUT", f"/rest/api/3/issue/{key}", {"update": {"issuelinks": [op]}})
    for t in remove:
        remove_link(key, t)
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
