"""Tests for scan-scoped querying (query/ask --scan) and the shared scope filter.

The backward-compat assertions on _scan_where are the key guard: the NLQ and
named-query paths share it, and there is no separate NLQ regression corpus in
this repo, so the default (scan_id=None) output must stay byte-identical.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cmips_inventory.nlq import _scan_where, generate_sql
from cmips_inventory.queries_lib import prepare_query
from cmips_inventory.db import SCHEMA_SQL, list_scans, resolve_scan


def _db():
    conn = sqlite3.connect(':memory:')
    conn.executescript(SCHEMA_SQL)
    return conn


def _scan(conn, scan_id, account, ts, count=0):
    conn.execute(
        "INSERT INTO scans (scan_id, account_id, timestamp, resource_count) "
        "VALUES (?, ?, ?, ?)", (scan_id, account, ts, count))


# ─── _scan_where backward compatibility (no regression) ───

def test_scan_where_default_unchanged():
    assert _scan_where() == "is_current=1"


def test_scan_where_account_unchanged():
    assert _scan_where("111122223333") == "is_current=1 AND account_id='111122223333'"


def test_scan_where_scan_id():
    assert _scan_where(scan_id="abc123") == "scan_id='abc123'"


def test_scan_where_scan_and_account():
    assert _scan_where("111", scan_id="abc123") == "scan_id='abc123' AND account_id='111'"


def test_scan_where_sanitizes_scan_id():
    assert _scan_where(scan_id="ab'c; DROP--") == "scan_id='abcDROP'"


# ─── resolve_scan / list_scans ───

def test_resolve_scan_selectors():
    conn = _db()
    _scan(conn, 'old', '111', '2026-01-01 10:00:00 UTC')
    _scan(conn, 'mid', '111', '2026-02-01 10:00:00 UTC')
    _scan(conn, 'new', '111', '2026-03-01 10:00:00 UTC')
    conn.commit()
    assert resolve_scan(conn, 'latest') == 'new'
    assert resolve_scan(conn, 'previous') == 'mid'
    assert resolve_scan(conn, 'first') == 'old'
    assert resolve_scan(conn, 'mid') == 'mid'
    assert resolve_scan(conn, 'nope') is None
    conn.close()


def test_resolve_scan_account_scoped():
    conn = _db()
    _scan(conn, 'a1', '111', '2026-01-01 10:00:00 UTC')
    _scan(conn, 'b1', '222', '2026-02-01 10:00:00 UTC')
    conn.commit()
    assert resolve_scan(conn, 'latest', account_id='111') == 'a1'
    assert resolve_scan(conn, 'latest', account_id='222') == 'b1'
    conn.close()


def test_list_scans_order():
    conn = _db()
    _scan(conn, 'old', '111', '2026-01-01 10:00:00 UTC', 5)
    _scan(conn, 'new', '111', '2026-03-01 10:00:00 UTC', 9)
    conn.commit()
    scans = list_scans(conn)
    assert [s[0] for s in scans] == ['new', 'old']
    conn.close()


# ─── threading scan_id through generate_sql / prepare_query ───

# A small batch standing in for the absent NLQ corpus: default must scope by
# is_current=1 and never reference scan_id.
_BATCH = [
    "show me ec2 instances",
    "how many s3 buckets per region",
    "iam users with admin access",
    "lambda functions using python",
    "rds instances that are not encrypted",
]


def test_default_questions_use_is_current_not_scan_id():
    for q in _BATCH:
        sql = generate_sql(q)
        assert "is_current=1" in sql, q
        assert "scan_id" not in sql, q


def test_questions_with_scan_id_scope_by_scan():
    for q in _BATCH:
        sql = generate_sql(q, scan_id="deadbeef")
        assert "scan_id='deadbeef'" in sql, q
        assert "is_current=1" not in sql, q


def test_prepare_query_scan_filter_substitution():
    raw = "SELECT * FROM resources WHERE {scan_filter}"
    assert prepare_query(raw, {}, scan_id="abc") == "SELECT * FROM resources WHERE scan_id='abc'"
    assert prepare_query(raw, {}) == "SELECT * FROM resources WHERE is_current=1"
    assert prepare_query(raw, {}, account_id="111") == \
        "SELECT * FROM resources WHERE is_current=1 AND account_id='111'"
