"""
Tests for file permission hardening in db.py and formatter.py.

Verifies that the SQLite database directory/file and all exported
output files are created with owner-only (0o600/0o700) permissions.
"""

import os
import stat
import tempfile
import pytest

from aws_inventory.db import get_connection
from aws_inventory.formatter import export_file


# ── database permissions ──────────────────────────────────────────────────────

def test_db_directory_permissions():
    """~/.awsmap/ (or custom dir) must be created with 0o700."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "subdir", "inventory.db")
        conn = get_connection(db_path)
        conn.close()

        dir_mode = stat.S_IMODE(os.stat(os.path.dirname(db_path)).st_mode)
        assert dir_mode == 0o700, f"Expected 0o700, got {oct(dir_mode)}"


def test_db_file_permissions():
    """The SQLite database file must be created with 0o600."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "subdir", "inventory.db")
        conn = get_connection(db_path)
        conn.close()

        file_mode = stat.S_IMODE(os.stat(db_path).st_mode)
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"


def test_db_file_permissions_existing_db():
    """Permissions must be enforced even when opening an existing database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "subdir", "inventory.db")
        # First open creates the DB
        conn = get_connection(db_path)
        conn.close()
        # Second open re-applies permissions
        conn = get_connection(db_path)
        conn.close()

        file_mode = stat.S_IMODE(os.stat(db_path).st_mode)
        assert file_mode == 0o600, f"Expected 0o600 on re-open, got {oct(file_mode)}"


# ── output file permissions ───────────────────────────────────────────────────

def test_export_file_permissions_html():
    """Exported HTML files must be created with 0o600."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        export_file("<html></html>", out)

        file_mode = stat.S_IMODE(os.stat(out).st_mode)
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"


def test_export_file_permissions_json():
    """Exported JSON files must be created with 0o600."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.json")
        export_file('{"resources": []}', out)

        file_mode = stat.S_IMODE(os.stat(out).st_mode)
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"


def test_export_file_permissions_csv():
    """Exported CSV files must be created with 0o600."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.csv")
        export_file("service,type,id\n", out)

        file_mode = stat.S_IMODE(os.stat(out).st_mode)
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"


def test_export_file_content_intact():
    """Permissions fix must not corrupt file content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.json")
        content = '{"test": "value"}'
        export_file(content, out)

        with open(out) as f:
            assert f.read() == content
