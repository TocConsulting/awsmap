"""Pre-built query library for awsmap query --name."""

import os
import re

from aws_inventory.nlq import _scan_where


def _escape_sql_string(value: str) -> str:
    """Escape a string value for safe inline SQL interpolation (single-quote escaping)."""
    return value.replace("'", "''")


# Directories searched for .sql files (built-in first, then user)
_BUILTIN_DIR = os.path.join(os.path.dirname(__file__), "queries")
_USER_DIR = os.path.join(os.path.expanduser("~"), ".awsmap", "queries")


def _parse_header(sql_text):
    """Parse SQL file header comments into metadata dict."""
    meta = {"name": "", "description": "", "params": []}
    for line in sql_text.splitlines():
        line = line.strip()
        if not line.startswith("--"):
            break
        line = line[2:].strip()
        if line.startswith("name:"):
            meta["name"] = line[5:].strip()
        elif line.startswith("description:"):
            meta["description"] = line[12:].strip()
        elif line.startswith("params:"):
            raw = line[7:].strip()
            meta["params"] = [p.strip() for p in raw.split(",") if p.strip()]
    return meta


def _find_sql_files():
    """Find all .sql files in built-in and user directories."""
    files = {}
    for d in [_BUILTIN_DIR, _USER_DIR]:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname.endswith(".sql"):
                name = fname[:-4]  # strip .sql
                files[name] = os.path.join(d, fname)
    return files


def list_named_queries():
    """Return list of (name, description, params) for all available queries."""
    files = _find_sql_files()
    result = []
    for name in sorted(files):
        with open(files[name]) as f:
            meta = _parse_header(f.read())
        result.append((name, meta.get("description", ""), meta.get("params", [])))
    return result


def load_named_query(name):
    """Load a named query. Returns (raw_sql, metadata).

    Raises FileNotFoundError if query doesn't exist.
    """
    files = _find_sql_files()
    if name not in files:
        raise FileNotFoundError(f"No query named '{name}'")
    with open(files[name]) as f:
        text = f.read()
    meta = _parse_header(text)
    # Strip header comments to get raw SQL
    lines = []
    past_header = False
    for line in text.splitlines():
        if not past_header and line.strip().startswith("--"):
            continue
        past_header = True
        lines.append(line)
    raw_sql = "\n".join(lines).strip()
    return raw_sql, meta


def prepare_query(raw_sql, meta, account_id=None, params=None):
    """Prepare a query for execution by injecting scan filter and params."""
    params = params or {}

    # Build scan filter
    scan_filter = _scan_where(account_id)

    # Replace scan filter placeholders (supports aliased versions)
    raw_sql = raw_sql.replace("{scan_filter}", scan_filter)
    # Handle aliased scan filters like {scan_filter_u} → u.is_current=1 AND u.account_id='X'
    for m in re.finditer(r"\{scan_filter_(\w+)\}", raw_sql):
        alias = m.group(1)
        aliased = re.sub(r'\b(is_current|account_id)\b', rf'{alias}.\1', scan_filter)
        raw_sql = raw_sql.replace(m.group(0), aliased)

    # Apply parameter defaults from header
    for p in meta.get("params", []):
        if "=" in p:
            key, default = p.split("=", 1)
            key = key.strip()
            default = default.strip()
            if key not in params:
                params[key] = default

    # Inject optional filters for common params (account already handled via scan_filter)
    if "service" in params:
        svc_raw = params.pop("service")
        # Validate service against known collectors to prevent injection
        try:
            from aws_inventory.collector import get_available_services
            _known_services = set(get_available_services())
        except Exception:
            _known_services = None
        if _known_services is not None and svc_raw not in _known_services:
            raise ValueError(f"Unknown service: {svc_raw!r}")
        svc = _escape_sql_string(svc_raw)
        # Inject service filter before GROUP BY/ORDER BY/LIMIT or at end
        inject_m = re.search(r'\s+(?:GROUP|ORDER|LIMIT)\b', raw_sql, re.IGNORECASE)
        clause = f" AND service = '{svc}'"
        if inject_m:
            raw_sql = raw_sql[:inject_m.start()] + clause + raw_sql[inject_m.start():]
        else:
            raw_sql += clause

    if "region" in params:
        rgn_raw = params.pop("region")
        # Validate region: alphanumeric + hyphens only
        if not re.fullmatch(r'[a-z0-9-]{1,30}', rgn_raw):
            raise ValueError(f"Invalid region: {rgn_raw!r}")
        rgn = _escape_sql_string(rgn_raw)
        inject_m = re.search(r'\s+(?:GROUP|ORDER|LIMIT)\b', raw_sql, re.IGNORECASE)
        clause = f" AND region = '{rgn}'"
        if inject_m:
            raw_sql = raw_sql[:inject_m.start()] + clause + raw_sql[inject_m.start():]
        else:
            raw_sql += clause

    # Replace remaining {param} placeholders (escape single quotes)
    for key, value in params.items():
        raw_sql = raw_sql.replace("{" + key + "}", _escape_sql_string(value))

    return raw_sql
