"""
Tests for SQL injection hardening in queries_lib.py (prepare_query).

Verifies that service/region validation and parameter escaping
prevent injection through named query parameters.
"""

import pytest

from aws_inventory.queries_lib import prepare_query, _escape_sql_string


# prepare_query signature: (raw_sql, meta, account_id=None, params=None)
# meta must be a dict with at least {"params": []} key

BASE_META = {"name": "test", "description": "", "params": []}
BASE_SQL = "SELECT * FROM resources WHERE {scan_filter}"


# ── _escape_sql_string ────────────────────────────────────────────────────────

def test_escape_single_quote():
    assert _escape_sql_string("O'Reilly") == "O''Reilly"


def test_escape_multiple_quotes():
    assert _escape_sql_string("it's a 'test'") == "it''s a ''test''"


def test_escape_no_special_chars():
    assert _escape_sql_string("normal") == "normal"


def test_escape_empty_string():
    assert _escape_sql_string("") == ""


# ── service validation ────────────────────────────────────────────────────────

def test_invalid_service_raises():
    """Unknown service name should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown service"):
        prepare_query(BASE_SQL, BASE_META, params={"service": "not_a_real_service_xyz"})


def test_valid_service_accepted():
    """Known service name should be injected without error."""
    result = prepare_query(BASE_SQL, BASE_META, params={"service": "s3"})
    assert "service = 's3'" in result


def test_service_injection_attempt_rejected():
    """SQL injection via service param should be rejected by allowlist."""
    with pytest.raises(ValueError, match="Unknown service"):
        prepare_query(BASE_SQL, BASE_META, params={"service": "s3' OR '1'='1"})


# ── region validation ─────────────────────────────────────────────────────────

def test_valid_region_accepted():
    """Valid region should be injected without error."""
    result = prepare_query(BASE_SQL, BASE_META, params={"region": "us-east-1"})
    assert "region = 'us-east-1'" in result


def test_invalid_region_raises():
    """Region with SQL characters should be rejected."""
    with pytest.raises(ValueError, match="Invalid region"):
        prepare_query(BASE_SQL, BASE_META, params={"region": "us-east-1' OR '1'='1"})


def test_region_with_uppercase_rejected():
    """Regions must be lowercase per AWS convention."""
    with pytest.raises(ValueError, match="Invalid region"):
        prepare_query(BASE_SQL, BASE_META, params={"region": "US-EAST-1"})


def test_region_too_long_rejected():
    """Region strings longer than 30 chars should be rejected."""
    with pytest.raises(ValueError, match="Invalid region"):
        prepare_query(BASE_SQL, BASE_META, params={"region": "a" * 31})


# ── generic param escaping ────────────────────────────────────────────────────

def test_generic_param_quote_escaped():
    """Single quotes in generic params must be escaped."""
    sql = "SELECT * FROM resources WHERE {scan_filter} AND name = '{myval}'"
    meta = {"name": "test", "description": "", "params": ["myval"]}
    result = prepare_query(sql, meta, params={"myval": "test'injection"})
    assert "test''injection" in result
    assert "test'injection" not in result.replace("test''injection", "")
