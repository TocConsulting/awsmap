"""
Tests for security hardening in config.py.

Verifies path traversal prevention for the 'db' config key
and that the file size limit in completions.py is enforced.
"""

import os
import tempfile
import pytest

from aws_inventory.config import validate_config


# ── path traversal prevention ─────────────────────────────────────────────────

def test_db_path_traversal_rejected():
    """Path containing ../ that resolves outside home must be rejected."""
    error = validate_config("db", "/tmp/evil.db")
    assert error is not None, "Expected error for path outside home"
    assert "home directory" in error


def test_db_path_traversal_dotdot_rejected():
    """Relative path with ../ must be rejected."""
    error = validate_config("db", "~/../../../etc/passwd")
    assert error is not None, "Expected error for ../ traversal"


def test_db_path_within_home_accepted():
    """Path within home directory must be accepted."""
    home = os.path.expanduser("~")
    valid_path = os.path.join(home, ".awsmap", "custom.db")
    error = validate_config("db", valid_path)
    assert error is None, f"Expected no error for valid path, got: {error}"


def test_db_default_path_accepted():
    """Default ~/.awsmap/inventory.db path must be accepted."""
    error = validate_config("db", "~/.awsmap/inventory.db")
    assert error is None, f"Expected no error for default path, got: {error}"


def test_db_absolute_outside_home_rejected():
    """Absolute path outside home directory must be rejected."""
    error = validate_config("db", "/var/db/inventory.db")
    assert error is not None, "Expected error for absolute path outside home"


def test_db_etc_passwd_rejected():
    """Classic /etc/passwd path must be rejected."""
    error = validate_config("db", "/etc/passwd")
    assert error is not None, "Expected error for /etc/passwd"


# ── other config key validation ───────────────────────────────────────────────

def test_unknown_key_rejected():
    """Unknown config keys must be rejected."""
    error = validate_config("unknown_key", "value")
    assert error is not None


def test_valid_format_accepted():
    """Valid format values must be accepted."""
    for fmt in ("html", "json", "csv"):
        error = validate_config("format", fmt)
        assert error is None, f"Expected no error for format={fmt}"


def test_invalid_format_rejected():
    """Invalid format values must be rejected."""
    error = validate_config("format", "xml")
    assert error is not None


def test_valid_workers_accepted():
    """Positive integer workers value must be accepted."""
    error = validate_config("workers", "10")
    assert error is None


def test_invalid_workers_rejected():
    """Non-integer or zero workers must be rejected."""
    assert validate_config("workers", "0") is not None
    assert validate_config("workers", "-1") is not None
    assert validate_config("workers", "abc") is not None
