"""
Waste / idle resource detection over the stored inventory.

Each rule is a deterministic SQL heuristic over fields already collected into the
`details` column. No new AWS calls. Rules only cover what is actually computable
from stored data: checks that need live metrics (NAT gateway traffic, S3 object
counts) are intentionally absent.
"""

from datetime import datetime, timedelta, timezone

from cmips_inventory.nlq import _scan_where


# key, title, service, type, where (SQL over details), display (detail keys to
# show per finding), note (caveat shown in output).
RULES = [
    {
        "key": "unattached-ebs",
        "title": "Unattached EBS volumes",
        "service": "ec2", "type": "volume",
        "where": "json_extract(details,'$.state')='available'",
        "display": ["size_gb", "volume_type"],
        "note": "",
    },
    {
        "key": "unassociated-eip",
        "title": "Unassociated Elastic IPs",
        "service": "ec2", "type": "elastic-ip",
        "where": "json_extract(details,'$.instance_id') IS NULL "
                 "AND json_extract(details,'$.network_interface_id') IS NULL",
        "display": ["public_ip"],
        "note": "Elastic IPs not attached to a running resource are billed hourly.",
    },
    {
        "key": "available-eni",
        "title": "Detached network interfaces",
        "service": "ec2", "type": "network-interface",
        "where": "json_extract(details,'$.status')='available'",
        "display": ["interface_type"],
        "note": "",
    },
    {
        "key": "idle-target-group",
        "title": "Target groups with no registered targets",
        "service": "elbv2", "type": "target-group",
        "where": "json_extract(details,'$.healthy_targets')=0 "
                 "AND json_extract(details,'$.unhealthy_targets')=0",
        "display": ["target_type", "port"],
        "note": "",
    },
    {
        "key": "empty-classic-elb",
        "title": "Classic load balancers with no instances",
        "service": "elb", "type": "classic-load-balancer",
        "where": "json_array_length(details,'$.instances')=0",
        "display": ["scheme"],
        "note": "",
    },
    {
        "key": "old-snapshot",
        "title": "EBS snapshots older than {min_age_days} days",
        "service": "ec2", "type": "snapshot",
        "where": "json_extract(details,'$.start_time') < '{cutoff}'",
        "display": ["size_gb", "start_time"],
        "note": "",
    },
    {
        "key": "old-ami",
        "title": "AMIs older than {min_age_days} days",
        "service": "ec2", "type": "ami",
        "where": "json_extract(details,'$.creation_date') < '{cutoff}'",
        "display": ["creation_date"],
        "note": "",
    },
    {
        "key": "stopped-instance",
        "title": "Stopped EC2 instances",
        "service": "ec2", "type": "instance",
        "where": "json_extract(details,'$.state')='stopped'",
        "display": ["instance_type"],
        "note": "Age since stop is not tracked; lists all stopped instances.",
    },
]

RULE_KEYS = [r["key"] for r in RULES]


def _detail_path(key):
    return f"json_extract(details,'$.{key}')"


def find_waste(conn, account_id=None, rule_keys=None, min_age_days=90,
               include_defaults=False):
    """Run waste rules and return structured findings.

    rule_keys: restrict to specific rule keys (None = all).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=min_age_days)).strftime('%Y-%m-%d')

    findings = {}
    summary = {}
    rules_meta = []
    base = _scan_where(account_id)
    if not include_defaults:
        base += " AND is_default=0"

    for rule in RULES:
        if rule_keys and rule["key"] not in rule_keys:
            continue
        cond = rule["where"].format(cutoff=cutoff, min_age_days=min_age_days)
        sql = (f"SELECT account_id, service, type, id, name, region "
               + "".join(f", {_detail_path(d)}" for d in rule["display"])
               + f" FROM resources WHERE {base} "
               f"AND service='{rule['service']}' AND type='{rule['type']}' "
               f"AND ({cond}) ORDER BY region, id")
        rows = conn.execute(sql).fetchall()
        items = []
        for row in rows:
            account, service, rtype, rid, name, region = row[:6]
            display = {}
            for i, dkey in enumerate(rule["display"]):
                display[dkey] = row[6 + i]
            items.append({
                "account_id": account,
                "service": service,
                "type": rtype,
                "id": rid,
                "name": name,
                "region": region,
                "display": display,
            })
        findings[rule["key"]] = items
        summary[rule["key"]] = len(items)
        rules_meta.append({
            "key": rule["key"],
            "title": rule["title"].format(min_age_days=min_age_days),
            "note": rule["note"],
        })

    return {
        "summary": summary,
        "findings": findings,
        "rules": rules_meta,
        "total": sum(summary.values()),
        "min_age_days": min_age_days,
    }
