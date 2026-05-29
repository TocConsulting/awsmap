"""
Snapshot diff / drift detection engine.

Compares two point-in-time snapshots of AWS resources to detect
added, removed, and modified resources. Works entirely offline
against the local SQLite database.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


def normalize_timestamp(date_str: str) -> str:
    """Normalize user date input to a full timestamp string.

    Supports: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, 7d, 30d, yesterday, today.

    Raises:
        ValueError: If the date string is not a recognized format.
    """
    date_str = date_str.strip()
    # Relative dates: 7d, 30d, 90d
    if date_str.endswith('d') and date_str[:-1].isdigit():
        days = int(date_str[:-1])
        target = datetime.now(timezone.utc) - timedelta(days=days)
        return target.strftime('%Y-%m-%d %H:%M:%S UTC')
    if date_str == 'yesterday':
        target = datetime.now(timezone.utc) - timedelta(days=1)
        return target.strftime('%Y-%m-%d') + ' 23:59:59 UTC'
    if date_str == 'today':
        return datetime.now(timezone.utc).strftime('%Y-%m-%d') + ' 23:59:59 UTC'
    # Full datetime
    if 'T' in date_str or ' ' in date_str:
        ts = date_str.replace('T', ' ')
        if not ts.endswith('UTC'):
            ts += ' UTC'
        # Validate by parsing
        try:
            datetime.strptime(ts.replace(' UTC', ''), '%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise ValueError(f"Invalid date format: '{date_str}'. "
                             f"Use YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, 7d, 30d, yesterday, or today.")
        return ts
    # Date only -> validate and convert to end of day
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. "
                         f"Use YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, 7d, 30d, yesterday, or today.")
    return f"{date_str} 23:59:59 UTC"


def reconstruct_snapshot(conn, cutoff_ts: str,
                         account_id: Optional[str] = None,
                         services: Optional[List[str]] = None,
                         regions: Optional[List[str]] = None) -> Dict[tuple, dict]:
    """Reconstruct the state of the world at a given timestamp.

    For each (account_id, service), finds the latest scan at or before cutoff_ts
    that *covered* that service, then returns that scan's resources for it.

    Coverage is read from each scan's recorded ``scanned_services`` list, so a
    service that was scanned but returned zero resources is correctly represented
    as empty — it will show as removed relative to an earlier non-empty scan,
    instead of falling back to that stale earlier scan. Scans written before this
    column existed (``scanned_services`` is NULL) fall back to the set of services
    actually present in their resources, preserving the previous behavior.

    Returns a dict keyed by (account_id, service, type, id, region)
    with resource row dicts as values.
    """
    # 1. Candidate scans at or before the cutoff, with their covered-service list.
    scan_sql = ("SELECT scan_id, account_id, scanned_services FROM scans "
                "WHERE timestamp <= ?")
    params = [cutoff_ts]
    if account_id:
        scan_sql += " AND account_id = ?"
        params.append(account_id)
    scan_sql += " ORDER BY timestamp ASC"
    scan_rows = conn.execute(scan_sql, params).fetchall()

    services_filter = set(services) if services else None

    # 2. Pick, per (account_id, service), the latest scan that covered it.
    #    Ascending timestamp order means later scans overwrite earlier choices.
    chosen = {}  # (account_id, service) -> scan_id
    for scan_id, acct, scanned_json in scan_rows:
        covered = None
        if scanned_json:
            try:
                covered = json.loads(scanned_json)
            except (json.JSONDecodeError, TypeError):
                covered = None
        if covered is None:
            # Legacy scan: fall back to the services present in its resources.
            covered = [row[0] for row in conn.execute(
                "SELECT DISTINCT service FROM resources WHERE scan_id = ?", (scan_id,))]
        for svc in covered:
            if services_filter is not None and svc not in services_filter:
                continue
            chosen[(acct, svc)] = scan_id

    # 3. Pull resources for each chosen (scan_id, service), grouped by scan.
    by_scan = {}  # scan_id -> set(services)
    for (acct, svc), scan_id in chosen.items():
        by_scan.setdefault(scan_id, set()).add(svc)

    snapshot = {}
    for scan_id, svcs in by_scan.items():
        svc_list = sorted(svcs)
        placeholders = ",".join("?" * len(svc_list))
        cursor = conn.execute(
            f"SELECT account_id, service, type, id, arn, name, region, "
            f"is_default, details, tags, scan_id FROM resources "
            f"WHERE scan_id = ? AND service IN ({placeholders})",
            [scan_id] + svc_list,
        )
        columns = [desc[0] for desc in cursor.description]
        for row in cursor:
            resource = dict(zip(columns, row))
            if regions and resource['region'] not in regions and resource['region'] is not None:
                continue
            snapshot[resource_key(resource)] = resource
    return snapshot


def reconstruct_current_snapshot(conn,
                                 account_id: Optional[str] = None,
                                 services: Optional[List[str]] = None,
                                 regions: Optional[List[str]] = None) -> Dict[tuple, dict]:
    """Get the current state using is_current=1. Used when --to is omitted."""
    clauses = ["is_current = 1"]
    params = []

    if account_id:
        clauses.append("account_id = ?")
        params.append(account_id)
    if services:
        placeholders = ",".join("?" * len(services))
        clauses.append(f"service IN ({placeholders})")
        params.extend(services)

    where = " AND ".join(clauses)
    cursor = conn.execute(
        f"SELECT account_id, service, type, id, arn, name, region, "
        f"is_default, details, tags, scan_id FROM resources WHERE {where}",
        params
    )
    columns = [desc[0] for desc in cursor.description]
    snapshot = {}
    for row in cursor:
        resource = dict(zip(columns, row))
        if regions and resource['region'] not in regions and resource['region'] is not None:
            continue
        key = resource_key(resource)
        snapshot[key] = resource
    return snapshot


def resource_key(r: dict) -> tuple:
    """Natural key for a resource: (account_id, service, type, id, region)."""
    return (r['account_id'], r['service'], r['type'], r['id'], r.get('region') or '')


def compute_diff(snapshot_from: Dict[tuple, dict],
                 snapshot_to: Dict[tuple, dict],
                 ignore_tags: bool = False) -> dict:
    """Compare two snapshots and classify every resource.

    Returns dict with keys: added, removed, modified, unchanged.
    """
    keys_from = set(snapshot_from.keys())
    keys_to = set(snapshot_to.keys())

    added = [snapshot_to[k] for k in sorted(keys_to - keys_from)]
    removed = [snapshot_from[k] for k in sorted(keys_from - keys_to)]
    modified = []
    unchanged = []

    for key in sorted(keys_from & keys_to):
        r_from = snapshot_from[key]
        r_to = snapshot_to[key]
        changes = _compute_changes(r_from, r_to, ignore_tags)
        if changes:
            modified.append({"resource": r_to, "changes": changes, "old": r_from})
        else:
            unchanged.append(r_to)

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
    }


def _compute_changes(r_from: dict, r_to: dict,
                     ignore_tags: bool = False) -> Optional[dict]:
    """Compute field-level changes between two versions of a resource.

    Returns None if no changes, or a dict with detail/tag/name diffs.
    """
    changes = {}

    # Name change
    old_name = r_from.get('name') or ''
    new_name = r_to.get('name') or ''
    if old_name != new_name:
        changes['name'] = {'from': old_name, 'to': new_name}

    # Detail diffs (deep JSON comparison)
    d_from = _parse_json(r_from.get('details'))
    d_to = _parse_json(r_to.get('details'))
    # Fast path: identical strings means identical dicts
    if r_from.get('details') != r_to.get('details'):
        detail_diffs = _dict_diff(d_from, d_to)
        if detail_diffs:
            changes['details'] = detail_diffs

    # Tag diffs (structured: added/removed/changed)
    if not ignore_tags:
        if r_from.get('tags') != r_to.get('tags'):
            t_from = _parse_json(r_from.get('tags'))
            t_to = _parse_json(r_to.get('tags'))
            tag_changes = _compute_tag_diffs(t_from, t_to)
            if tag_changes:
                changes['tags'] = tag_changes

    return changes if changes else None


def _compute_tag_diffs(tags_from: dict, tags_to: dict) -> Optional[dict]:
    """Compute structured tag diffs: added, removed, changed."""
    added = {k: v for k, v in tags_to.items() if k not in tags_from}
    removed = {k: v for k, v in tags_from.items() if k not in tags_to}
    changed = {}
    for k in set(tags_from.keys()) & set(tags_to.keys()):
        if tags_from[k] != tags_to[k]:
            changed[k] = {'from': tags_from[k], 'to': tags_to[k]}

    if added or removed or changed:
        return {'added': added, 'removed': removed, 'changed': changed}
    return None


def _parse_json(s) -> dict:
    """Parse JSON string, returning empty dict on failure."""
    if not s:
        return {}
    if isinstance(s, dict):
        return s
    try:
        result = json.loads(s)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _dict_diff(old: dict, new: dict) -> list:
    """Compare two dicts, return list of {field, from, to} for changed keys."""
    all_keys = set(old.keys()) | set(new.keys())
    diffs = []
    for key in sorted(all_keys):
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            diffs.append({'field': key, 'from': old_val, 'to': new_val})
    return diffs


def build_summary(diff_result: dict) -> dict:
    """Build per-service summary counts from diff result."""
    by_service = {}

    for category in ('added', 'removed', 'unchanged'):
        for r in diff_result[category]:
            svc = r.get('service', 'unknown')
            if svc not in by_service:
                by_service[svc] = {'added': 0, 'removed': 0, 'modified': 0, 'unchanged': 0}
            by_service[svc][category] += 1

    for entry in diff_result['modified']:
        svc = entry['resource'].get('service', 'unknown')
        if svc not in by_service:
            by_service[svc] = {'added': 0, 'removed': 0, 'modified': 0, 'unchanged': 0}
        by_service[svc]['modified'] += 1

    return {
        'added': len(diff_result['added']),
        'removed': len(diff_result['removed']),
        'modified': len(diff_result['modified']),
        'unchanged': len(diff_result['unchanged']),
        'by_service': dict(sorted(by_service.items()))
    }


def snapshot_metadata(conn, cutoff_ts: str,
                      account_id: Optional[str] = None,
                      services: Optional[List[str]] = None,
                      regions: Optional[List[str]] = None) -> dict:
    """Get summary metadata about a reconstructed snapshot."""
    where_clauses = ["s.timestamp <= ?"]
    params = [cutoff_ts]
    if account_id:
        where_clauses.append("r.account_id = ?")
        params.append(account_id)
    if services:
        placeholders = ",".join("?" * len(services))
        where_clauses.append(f"r.service IN ({placeholders})")
        params.extend(services)
    where_sql = " AND ".join(where_clauses)

    sql = f"""
    WITH latest_scan_per_service AS (
        SELECT r.account_id, r.service, MAX(s.timestamp) AS max_ts
        FROM resources r
        JOIN scans s ON r.scan_id = s.scan_id
        WHERE {where_sql}
        GROUP BY r.account_id, r.service
    )
    SELECT COUNT(DISTINCT lsps.service) as service_count,
           MAX(lsps.max_ts) as latest_scan,
           GROUP_CONCAT(DISTINCT lsps.service) as services
    FROM latest_scan_per_service lsps
    """
    cursor = conn.execute(sql, params)
    row = cursor.fetchone()
    result_services = sorted(row[2].split(',')) if row and row[2] else []
    if regions:
        # Note: region filtering happens at resource level, not scan level.
        # Metadata reflects the services that have scans, which is still useful.
        pass
    return {
        'service_count': row[0] if row else 0,
        'latest_scan': row[1] if row else None,
        'services': result_services,
    }
