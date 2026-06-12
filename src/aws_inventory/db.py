"""
SQLite storage and query engine for AWS inventory data.
"""

import json
import os
import shutil
import sqlite3
import uuid


DEFAULT_DB_PATH = os.path.expanduser("~/.awsmap/inventory.db")

# A few collectors are invoked under one service label but emit resources with a
# different `service` value. Normalize the scan label to the emitted name so the
# stored scanned-service list lines up with resources.service (used by snapshot
# reconstruction and is_current bookkeeping). Mirrors the special cases in
# collector.SERVICE_MODULE_MAP whose module name differs from the scan label.
_SERVICE_LABEL_TO_EMITTED = {
    "eventbridge-scheduler": "scheduler",
    "eventbridge-pipes": "pipes",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    scan_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    account_alias TEXT,
    profile TEXT,
    timestamp TEXT NOT NULL,
    duration_seconds REAL,
    resource_count INTEGER,
    services_scanned INTEGER,
    regions_scanned INTEGER,
    scanned_services TEXT
);

CREATE TABLE IF NOT EXISTS resources (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    service TEXT NOT NULL,
    type TEXT NOT NULL,
    id TEXT NOT NULL,
    arn TEXT,
    name TEXT,
    region TEXT,
    account_id TEXT,
    is_default INTEGER DEFAULT 0,
    is_current INTEGER DEFAULT 1,
    details TEXT,
    tags TEXT,
    FOREIGN KEY (scan_id) REFERENCES scans(scan_id)
);

CREATE INDEX IF NOT EXISTS idx_resources_service ON resources(service);
CREATE INDEX IF NOT EXISTS idx_resources_region ON resources(region);
CREATE INDEX IF NOT EXISTS idx_resources_scan_id ON resources(scan_id);
"""


def get_connection(db_path=None):
    """Open (or create) the SQLite database and ensure schema exists."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA_SQL)
    _migrate(conn)
    return conn


def _migrate(conn):
    """Add is_current column to existing databases.

    Handles partial scans: finds latest scan per (account, service), not per account.
    Safe for concurrent access: try/except on ALTER TABLE, immediate commit,
    idempotent UPDATE (AND is_current=1).
    """
    cursor = conn.execute("PRAGMA table_info(resources)")
    columns = {row[1] for row in cursor.fetchall()}
    if "is_current" not in columns:
        try:
            conn.execute("ALTER TABLE resources ADD COLUMN is_current INTEGER DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        # Mark resource as NOT current if a newer scan exists for same account+service.
        # This correctly handles partial scans (e.g., scan A has ec2+s3, scan B has lambda).
        # AND is_current=1 makes it idempotent - concurrent processes find 0 rows.
        conn.execute(
            "UPDATE resources SET is_current=0 "
            "WHERE is_current=1 AND EXISTS ("
            "  SELECT 1 FROM resources r2 "
            "  JOIN scans s2 ON r2.scan_id = s2.scan_id "
            "  JOIN scans s1 ON resources.scan_id = s1.scan_id "
            "  WHERE r2.account_id = resources.account_id "
            "  AND r2.service = resources.service "
            "  AND s2.timestamp > s1.timestamp)"
        )
        conn.commit()
    # Add scanned_services column to existing scan tables (stores the JSON list of
    # services each scan covered, so reconstruct_snapshot can represent a service
    # that was scanned but returned zero resources). NULL for legacy scans.
    scan_cols = {row[1] for row in conn.execute("PRAGMA table_info(scans)").fetchall()}
    if "scanned_services" not in scan_cols:
        try:
            conn.execute("ALTER TABLE scans ADD COLUMN scanned_services TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    # Always ensure indexes exist (safe for both new and migrated DBs)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resources_current "
        "ON resources(is_current, account_id, service)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scans_timestamp "
        "ON scans(timestamp)"
    )


def get_accounts(conn):
    """Return list of (account_id, account_alias, profile) for all accounts."""
    cursor = conn.execute(
        "SELECT account_id, account_alias, profile "
        "FROM scans GROUP BY account_id ORDER BY MAX(timestamp) DESC")
    return cursor.fetchall()


def resolve_account_id(conn, identifier):
    """Find account_id by profile name, account alias, or account id."""
    # Try profile first
    cursor = conn.execute(
        "SELECT account_id FROM scans WHERE profile = ? "
        "ORDER BY timestamp DESC LIMIT 1", (identifier,))
    row = cursor.fetchone()
    if row:
        return row[0]
    # Try account alias
    cursor = conn.execute(
        "SELECT account_id FROM scans WHERE account_alias = ? "
        "ORDER BY timestamp DESC LIMIT 1", (identifier,))
    row = cursor.fetchone()
    if row:
        return row[0]
    # Try direct account_id
    cursor = conn.execute(
        "SELECT account_id FROM scans WHERE account_id = ? "
        "ORDER BY timestamp DESC LIMIT 1", (identifier,))
    row = cursor.fetchone()
    return row[0] if row else None


def account_label(conn, account_id):
    """Human-readable label for an account: alias > profile > account_id."""
    cursor = conn.execute(
        "SELECT account_alias, profile FROM scans WHERE account_id = ? "
        "ORDER BY timestamp DESC LIMIT 1", (account_id,))
    row = cursor.fetchone()
    if row:
        if row[0]:
            return row[0]
        if row[1]:
            return row[1]
    return account_id


def list_scans(conn, account_id=None):
    """Return scan rows (scan_id, timestamp, account_id, account_alias, profile,
    resource_count, services_scanned) newest first."""
    sql = ("SELECT scan_id, timestamp, account_id, account_alias, profile, "
           "resource_count, services_scanned FROM scans")
    params = []
    if account_id:
        sql += " WHERE account_id = ?"
        params.append(account_id)
    sql += " ORDER BY timestamp DESC, scan_id DESC"
    return conn.execute(sql, params).fetchall()


def resolve_scan(conn, selector, account_id=None):
    """Resolve a scan selector to a scan_id.

    selector: 'latest' | 'previous' | 'first' | <scan_id>. Returns None if it
    cannot be resolved.
    """
    sel = (selector or "").strip()
    where = []
    params = []
    if account_id:
        where.append("account_id = ?")
        params.append(account_id)
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    low = sel.lower()

    if low == "latest":
        rows = conn.execute(
            "SELECT scan_id FROM scans" + wsql +
            " ORDER BY timestamp DESC, scan_id DESC LIMIT 1", params).fetchall()
        return rows[0][0] if rows else None
    if low == "previous":
        rows = conn.execute(
            "SELECT scan_id FROM scans" + wsql +
            " ORDER BY timestamp DESC, scan_id DESC LIMIT 2", params).fetchall()
        return rows[1][0] if len(rows) > 1 else None
    if low == "first":
        rows = conn.execute(
            "SELECT scan_id FROM scans" + wsql +
            " ORDER BY timestamp ASC, scan_id ASC LIMIT 1", params).fetchall()
        return rows[0][0] if rows else None

    cond = where + ["scan_id = ?"]
    row = conn.execute(
        "SELECT scan_id FROM scans WHERE " + " AND ".join(cond),
        params + [sel]).fetchone()
    return row[0] if row else None


def get_recent_scan_timestamps(conn, account_id=None):
    """Return (latest_ts, prev_cutoff) for diff defaulting.

    latest_ts is the most recent scan timestamp; prev_cutoff is the most recent
    distinct timestamp strictly older than latest_ts. Either is None when there
    are zero or one distinct scan timestamps.
    """
    sql = "SELECT DISTINCT timestamp FROM scans"
    params = []
    if account_id:
        sql += " WHERE account_id = ?"
        params.append(account_id)
    sql += " ORDER BY timestamp DESC LIMIT 2"
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return (None, None)
    latest = rows[0][0]
    prev = rows[1][0] if len(rows) > 1 else None
    return (latest, prev)


def get_scan_timestamp_before(conn, ts, account_id=None):
    """Return the most recent scan timestamp strictly before ts, or None."""
    sql = "SELECT timestamp FROM scans WHERE timestamp < ?"
    params = [ts]
    if account_id:
        sql += " AND account_id = ?"
        params.append(account_id)
    sql += " ORDER BY timestamp DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def store_scan(conn, result, profile=None, account_alias=None, scanned_services=None):
    """Store a scan result in the database. Returns the scan_id."""
    scan_id = uuid.uuid4().hex[:16]
    meta = result["metadata"]
    account_id = meta.get("account_id", "")
    resources = result.get("resources", [])

    # Compute the canonical set of services this scan covered: the service labels
    # we scanned (normalized to their emitted names) plus the names actually emitted
    # by the collectors. Normalization is essential because a few collectors emit a
    # `service` value that differs from the scan label they run under (e.g. the
    # `eventbridge-scheduler`/`eventbridge-pipes` labels store rows as
    # `scheduler`/`pipes`). This canonical set is used both to retire superseded
    # rows and to persist what the scan covered.
    services_covered = {_SERVICE_LABEL_TO_EMITTED.get(s, s) for s in (scanned_services or [])}
    services_covered.update(r.get("service", "") for r in resources)
    services_covered.discard("")
    services_covered = sorted(services_covered)

    # Mark old resources as not current for every service this scan covered.
    # Without this, re-scanning would leave stale is_current rows behind.
    if services_covered:
        placeholders = ",".join("?" * len(services_covered))
        conn.execute(
            f"UPDATE resources SET is_current=0 "
            f"WHERE account_id=? AND service IN ({placeholders}) AND is_current=1",
            [account_id] + services_covered
        )

    conn.execute(
        "INSERT INTO scans (scan_id, account_id, account_alias, profile, timestamp, "
        "duration_seconds, resource_count, services_scanned, regions_scanned, scanned_services) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            scan_id,
            meta.get("account_id", ""),
            account_alias,
            profile,
            meta.get("timestamp", ""),
            meta.get("scan_duration_seconds"),
            meta.get("resource_count", 0),
            meta.get("services_scanned", 0),
            meta.get("regions_scanned", 0),
            json.dumps(services_covered),
        ),
    )

    for r in resources:
        conn.execute(
            "INSERT INTO resources (scan_id, service, type, id, arn, name, region, "
            "account_id, is_default, is_current, details, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                scan_id,
                r.get("service", ""),
                r.get("type", ""),
                r.get("id", ""),
                r.get("arn"),
                r.get("name"),
                r.get("region"),
                meta.get("account_id", ""),
                1 if r.get("is_default") else 0,
                json.dumps(r.get("details", {}), default=str),
                json.dumps(r.get("tags", {}), default=str),
            ),
        )

    conn.commit()
    return scan_id


def run_query(conn, sql):
    """Execute a SQL query and return (columns, rows)."""
    cursor = conn.execute(sql)
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    return columns, rows


def format_table(columns, rows):
    """Pretty-print columns and rows as an aligned terminal table."""
    if not columns:
        return "No results."
    if not rows:
        return "No results."

    # Convert all values to strings
    str_rows = [[str(v) if v is not None else "" for v in row] for row in rows]

    # Get terminal width (default 120 if unavailable)
    term_width = shutil.get_terminal_size((120, 24)).columns

    # Calculate natural column widths
    widths = [len(c) for c in columns]
    for row in str_rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    # Distribute available width across columns
    # Reserve 2 chars ("  ") between each column
    gap = 2
    total_gap = gap * (len(columns) - 1) if len(columns) > 1 else 0
    available = term_width - total_gap

    total_natural = sum(widths)
    if total_natural > available:
        # Two-pass approach: lock short columns, shrink wide ones
        # "Short" = columns that fit in their fair share (available / n_cols)
        fair_share = available // len(columns) if columns else available
        locked = {}  # index -> width (columns that keep natural width)
        flexible = []  # indices of columns that need shrinking

        for i, w in enumerate(widths):
            if w <= fair_share:
                locked[i] = w
            else:
                flexible.append(i)

        # Give flexible columns the remaining space equally
        locked_total = sum(locked.values())
        flex_available = available - locked_total
        if flexible:
            flex_each = flex_available // len(flexible)
            remainder = flex_available % len(flexible)
            for j, i in enumerate(flexible):
                # Last flexible column gets the remainder pixels
                widths[i] = min(widths[i], flex_each + (1 if j < remainder else 0))
        for i, w in locked.items():
            widths[i] = w

    # Build header
    header = "  ".join(c.ljust(w) for c, w in zip(columns, widths))
    separator = "  ".join("-" * w for w in widths)

    # Build rows (truncate long values with ellipsis)
    lines = [header, separator]
    for row in str_rows:
        parts = []
        for val, w in zip(row, widths):
            if len(val) > w and w > 3:
                parts.append(val[:w - 3] + "...")
            else:
                parts.append(val[:w].ljust(w))
        lines.append("  ".join(parts))

    return "\n".join(lines)
