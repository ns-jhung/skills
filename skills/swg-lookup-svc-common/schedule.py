"""Shared schedule constants for the swg-lookup-svc deploy-ticket skills.

Imported by both swg-lookup-svc-deploy-ticket/run.py (create) and
swg-lookup-svc-update-deploy-ticket/run.py (update), so a reschedule computes
the same per-region planned dates the ticket was created with. Edit here, not
in the callers.
"""
import datetime

UTC8 = datetime.timezone(datetime.timedelta(hours=8))
WINDOW = datetime.timedelta(hours=1)

NPE_POPS = ["ch-hippo-local", "qa01-mp-npe-iad0-nc1", "stg01-mp-iad0-nc4",
            "fed1mp-iad0-nc1", "perf01-mp-iad0-nc6", "devint-automation-iad0-nc1"]
# (event, days from the prod deploy date, detail, pops)
EVENTS = [
    ("NPE", -7, "Deploy following home pops", NPE_POPS),
    ("Batch 1 (09:00, UTC+8)", 0, "Deployment", ["RUH1", "AM2", "FR4", "FRA2", "ZUR2", "LON3"]),
    ("Batch 2 (15:00, UTC+8)", 0, "Deployment", ["DFW3", "SJC1", "SJC2", "SV5"]),
    ("Batch 3 (24:00, UTC+8)", 0, "Deployment", ["MEL2", "SIN2", "BOM3"]),
    ("Fed PreProd", -7, None, []),
    ("Fed", 7, None, []),
]
DATACENTERS = sorted({p for e in EVENTS if e[0].startswith("Batch") for p in e[3]})

# batch -> (start hour UTC+8 on the deploy date, [(region start, region end)]); 24 rolls to the next day
BATCH_REGIONS = {
    "batch1": (9, [("customfield_20808", "customfield_20809")]),  # EU
    "batch2": (15, [("customfield_20810", "customfield_20811"),  # US East
                    ("customfield_20812", "customfield_20813")]),  # US West
    "batch3": (24, [("customfield_20806", "customfield_20807"),  # APAC
                    ("customfield_21276", "customfield_21277")]),  # AUS
}
PLANNED_FIELDS = [f for _, regions in BATCH_REGIONS.values() for pair in regions for f in pair]


def planned_dates(deploy_day):
    day = datetime.datetime.combine(deploy_day, datetime.time.min, tzinfo=UTC8)
    fields = {}
    for hour, regions in BATCH_REGIONS.values():
        start = day + datetime.timedelta(hours=hour)
        for start_field, end_field in regions:
            fields[start_field] = start.strftime("%Y-%m-%dT%H:%M:%S.000%z")
            fields[end_field] = (start + WINDOW).strftime("%Y-%m-%dT%H:%M:%S.000%z")
    return fields
