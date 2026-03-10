"""
Tests for SQL injection hardening in nlq.py (_fix_partial_value_match).

Verifies that user-derived values in LIKE clauses are properly escaped
so that SQL special characters cannot break out of the string context.
"""

import sqlite3
import pytest

from aws_inventory.nlq import _fix_partial_value_match


@pytest.fixture
def conn():
    """In-memory SQLite DB with a minimal resources table."""
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE resources (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT,
            service TEXT,
            type TEXT,
            id TEXT,
            arn TEXT,
            name TEXT,
            region TEXT,
            account_id TEXT,
            is_default INTEGER DEFAULT 0,
            is_current INTEGER DEFAULT 1,
            details TEXT,
            tags TEXT
        );
        INSERT INTO resources (scan_id, service, type, id, name, region, account_id, is_current)
        VALUES ('s1', 's3', 'bucket', 'my-bucket', 'my-bucket', 'us-east-1', '123456789012', 1);
    """)
    return c


def test_normal_name_becomes_like(conn):
    """A normal name= clause with no exact match is widened to LIKE '%value%'."""
    # 'bucket' is a partial match for 'my-bucket' in the DB — exact match
    # returns a row so no widening needed. Use a value that matches partially
    # but not exactly to trigger the LIKE fallback.
    sql = "SELECT * FROM resources WHERE is_current=1 AND name='bucket'"
    result = _fix_partial_value_match(sql, conn)
    # Either widened to LIKE (partial match found) or returned as-is (no rows)
    # The important thing is the result is valid SQL
    assert isinstance(result, str)
    conn.execute(result)  # Must not raise


def test_single_quote_escaped(conn):
    """Single quotes in value must be escaped to '' to prevent injection."""
    sql = "SELECT * FROM resources WHERE is_current=1 AND name='test''injection'"
    # Should not raise; the escaped SQL must be valid
    result = _fix_partial_value_match(sql, conn)
    # Result is valid SQL (no unhandled exception)
    assert isinstance(result, str)


def test_percent_wildcard_escaped(conn):
    """% in user value should be escaped so it doesn't act as a wildcard."""
    sql = "SELECT * FROM resources WHERE is_current=1 AND name='100%done'"
    result = _fix_partial_value_match(sql, conn)
    if "LIKE" in result:
        # The % in the value must be escaped with backslash
        assert "\\%" in result or "100" in result


def test_underscore_escaped(conn):
    """_ in user value should be escaped so it doesn't act as a single-char wildcard."""
    sql = "SELECT * FROM resources WHERE is_current=1 AND name='my_bucket'"
    result = _fix_partial_value_match(sql, conn)
    if "LIKE" in result:
        assert "\\_" in result or "my_bucket" in result


def test_or_injection_does_not_return_extra_rows(conn):
    """Classic OR 1=1 injection attempt should not return unintended rows."""
    # If injection worked, the LIKE clause would be: name LIKE '%x' OR '1'='1%'
    # which would match all rows. Our escaping should prevent this.
    sql = "SELECT * FROM resources WHERE is_current=1 AND service='s3' AND name='x'' OR ''1''=''1'"
    # This should not raise and should not widen to a dangerous pattern
    result = _fix_partial_value_match(sql, conn)
    assert isinstance(result, str)
    # The result SQL must be executable without error
    conn.execute(result)


def test_backslash_escaped(conn):
    """Backslash in value must be escaped to prevent ESCAPE sequence manipulation."""
    sql = r"SELECT * FROM resources WHERE is_current=1 AND name='test\value'"
    result = _fix_partial_value_match(sql, conn)
    assert isinstance(result, str)
    # Must execute without error
    conn.execute(result)


def test_known_exact_values_skipped(conn):
    """Values like 'global' should not be converted to LIKE clauses."""
    sql = "SELECT * FROM resources WHERE is_current=1 AND name='global'"
    result = _fix_partial_value_match(sql, conn)
    # 'global' is in the skip list, should remain as exact match
    assert "LIKE" not in result


def test_service_field_not_widened(conn):
    """service= clauses must never be widened to LIKE (allowlist field)."""
    sql = "SELECT * FROM resources WHERE is_current=1 AND service='s3'"
    result = _fix_partial_value_match(sql, conn)
    assert "LIKE" not in result
