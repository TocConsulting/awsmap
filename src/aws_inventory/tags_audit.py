"""
Tag compliance auditing over the stored inventory.

Computes tagging coverage for the current snapshot: overall compliance, per
required-tag coverage, per-service breakdown, and the list of non-compliant
resources. Operates entirely on already-collected data.
"""

import json

from aws_inventory.nlq import _scan_where


# Matches the NLQ "is_empty" semantics for the tags column so a resource with
# no tags is counted consistently across `ask` and `tags`.
_NO_TAGS = "(tags IS NULL OR tags='{}' OR tags='null')"


def _present_expr(key):
    """SQL boolean: tag key is present and non-empty."""
    safe = key.replace("'", "''").replace('"', '""')
    expr = f"json_extract(tags,'$.\"{safe}\"')"
    return f"({expr} IS NOT NULL AND {expr} <> '')"


def _build_scope(account_id, services, include_defaults):
    """Build the WHERE clause that defines the audited resource set."""
    scope = _scan_where(account_id)
    if not include_defaults:
        scope += " AND is_default=0"
    if services:
        quoted = ",".join("'" + s.replace("'", "''") + "'" for s in services)
        scope += f" AND service IN ({quoted})"
    return scope


def audit_tags(conn, account_id=None, services=None, required=None,
               include_defaults=False):
    """Audit tag compliance and return a structured result.

    required: list of tag keys every resource must carry (non-empty). When empty
    or None, compliance falls back to "has at least one tag".
    """
    required = [k for k in (required or []) if k]
    scope = _build_scope(account_id, services, include_defaults)

    if required:
        compliant_expr = " AND ".join(_present_expr(k) for k in required)
    else:
        compliant_expr = f"NOT {_NO_TAGS}"

    total = conn.execute(
        f"SELECT COUNT(*) FROM resources WHERE {scope}").fetchone()[0]

    by_service = {}
    rows = conn.execute(
        f"SELECT service, COUNT(*), "
        f"SUM(CASE WHEN {compliant_expr} THEN 1 ELSE 0 END) "
        f"FROM resources WHERE {scope} GROUP BY service ORDER BY service"
    ).fetchall()
    compliant_total = 0
    for service, svc_total, svc_compliant in rows:
        svc_compliant = svc_compliant or 0
        compliant_total += svc_compliant
        by_service[service] = {
            "total": svc_total,
            "compliant": svc_compliant,
            "pct": round(svc_compliant * 100 / svc_total) if svc_total else 0,
        }

    per_tag = {}
    for key in required:
        present = conn.execute(
            f"SELECT SUM(CASE WHEN {_present_expr(key)} THEN 1 ELSE 0 END) "
            f"FROM resources WHERE {scope}"
        ).fetchone()[0] or 0
        per_tag[key] = {
            "present": present,
            "pct": round(present * 100 / total) if total else 0,
        }

    noncompliant = []
    nc_rows = conn.execute(
        f"SELECT account_id, service, type, id, name, region, tags "
        f"FROM resources WHERE {scope} AND NOT ({compliant_expr}) "
        f"ORDER BY service, type, id"
    ).fetchall()
    for account, service, rtype, rid, name, region, tags_json in nc_rows:
        tags = {}
        if tags_json:
            try:
                parsed = json.loads(tags_json)
                if isinstance(parsed, dict):
                    tags = parsed
            except (json.JSONDecodeError, TypeError):
                tags = {}
        if required:
            missing = [k for k in required if not tags.get(k)]
        else:
            missing = ["(any tag)"]
        noncompliant.append({
            "account_id": account,
            "service": service,
            "type": rtype,
            "id": rid,
            "name": name,
            "region": region,
            "missing": missing,
            "untagged": len(tags) == 0,
        })

    return {
        "required": required,
        "scope_count": total,
        "overall": {
            "compliant": compliant_total,
            "total": total,
            "pct": round(compliant_total * 100 / total) if total else 0,
        },
        "per_tag": per_tag,
        "by_service": by_service,
        "noncompliant": noncompliant,
    }
