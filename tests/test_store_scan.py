"""Tests for store_scan is_current bookkeeping across re-scans."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from aws_inventory.db import get_connection, store_scan


def _scan(account_id, timestamp, resources):
    return {
        "metadata": {"account_id": account_id, "timestamp": timestamp,
                     "resource_count": len(resources)},
        "resources": resources,
    }


def _current_rows(conn, account_id, service):
    return conn.execute(
        "SELECT COUNT(*) FROM resources WHERE account_id=? AND service=? AND is_current=1",
        (account_id, service),
    ).fetchone()[0]


def test_rescan_retires_old_rows(tmp_path):
    """A re-scan of the same service leaves exactly one current row, not duplicates."""
    db = str(tmp_path / "t.db")
    conn = get_connection(db)
    acct = "111122223333"
    r = [{"service": "s3", "type": "bucket", "id": "b1", "region": "us-east-1"}]
    store_scan(conn, _scan(acct, "2026-01-01 00:00:00 UTC", r), scanned_services=["s3"])
    store_scan(conn, _scan(acct, "2026-01-02 00:00:00 UTC", r), scanned_services=["s3"])
    assert _current_rows(conn, acct, "s3") == 1
    conn.close()


def test_rescan_retires_when_emitted_service_differs_from_scan_label(tmp_path):
    """Regression: collectors whose emitted `service` differs from the scan label
    (e.g. `eventbridge-scheduler` stores rows as `scheduler`) must still retire
    old current rows, or is_current rows accumulate on every re-scan."""
    db = str(tmp_path / "t.db")
    conn = get_connection(db)
    acct = "111122223333"
    # The collector is invoked under the label "eventbridge-scheduler" but emits
    # resources with service="scheduler".
    sched = [{"service": "scheduler", "type": "schedule-group",
              "id": "FISConsoleDefault", "region": "us-east-1"}]
    for ts in ("2026-01-01 00:00:00 UTC", "2026-01-02 00:00:00 UTC",
               "2026-01-03 00:00:00 UTC", "2026-01-04 00:00:00 UTC"):
        store_scan(conn, _scan(acct, ts, sched),
                   scanned_services=["eventbridge-scheduler"])
    # Without the fix this would be 4 (one stale duplicate per re-scan).
    assert _current_rows(conn, acct, "scheduler") == 1
    conn.close()


def test_scanned_service_with_zero_results_retires_old_rows(tmp_path):
    """A service scanned again but now returning nothing retires its old rows."""
    db = str(tmp_path / "t.db")
    conn = get_connection(db)
    acct = "111122223333"
    r = [{"service": "sqs", "type": "queue", "id": "q1", "region": "us-east-1"}]
    store_scan(conn, _scan(acct, "2026-01-01 00:00:00 UTC", r), scanned_services=["sqs"])
    # Re-scan found no queues (deleted) — pass scanned_services so the empty
    # service is still retired.
    store_scan(conn, _scan(acct, "2026-01-02 00:00:00 UTC", []), scanned_services=["sqs"])
    assert _current_rows(conn, acct, "sqs") == 0
    conn.close()
