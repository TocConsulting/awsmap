"""Tests for the demo data generator — focused on --seed reproducibility."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from aws_inventory.demo import generate_demo_db


def _resource_rows(db_path):
    """All resource content, fully ordered, including details/tags."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT account_id, service, type, id, name, region, details, tags "
        "FROM resources ORDER BY account_id, service, type, id"
    ).fetchall()
    conn.close()
    return rows


def _scan_rows(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT account_id, timestamp, resource_count, scanned_services "
        "FROM scans ORDER BY account_id, timestamp"
    ).fetchall()
    conn.close()
    return rows


def test_same_seed_is_byte_reproducible(tmp_path):
    """Two generations with the same seed produce an identical database,
    down to detail/tag values and scan timestamps. Guards the _NOW_ANCHOR
    fix: timestamps are anchored to today's UTC midnight rather than the
    exact instant, so wall-clock skew between runs cannot leak in."""
    a = str(tmp_path / "a.db")
    b = str(tmp_path / "b.db")
    generate_demo_db(a, n_accounts=2, n_scans=3, seed=42)
    generate_demo_db(b, n_accounts=2, n_scans=3, seed=42)

    assert _resource_rows(a) == _resource_rows(b)
    assert _scan_rows(a) == _scan_rows(b)


def test_different_seed_differs(tmp_path):
    """A different seed yields different data (sanity check that the seed
    actually drives generation, not just a constant)."""
    a = str(tmp_path / "a.db")
    c = str(tmp_path / "c.db")
    generate_demo_db(a, n_accounts=2, n_scans=3, seed=42)
    generate_demo_db(c, n_accounts=2, n_scans=3, seed=7)

    assert _resource_rows(a) != _resource_rows(c)


def test_services_covered_stat_matches_db(tmp_path):
    """The reported services_covered count equals the distinct services
    actually stored (regression for the old len(_AWSMAP_TYPES) stat)."""
    db = str(tmp_path / "demo.db")
    stats = generate_demo_db(db, n_accounts=1, n_scans=1, seed=42)

    conn = sqlite3.connect(db)
    distinct = conn.execute("SELECT COUNT(DISTINCT service) FROM resources").fetchone()[0]
    conn.close()
    assert stats["services_covered"] == distinct
