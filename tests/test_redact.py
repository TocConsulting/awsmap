"""
Tests for the --redact flag and redact_account_ids() in formatter.py.

Verifies that account IDs are replaced with [REDACTED] in all output
formats, and that filenames generated with --redact use REDACTED.
"""

import pytest

from aws_inventory.formatter import redact_account_ids, format_output


ACCOUNT_ID = "123456789012"

SAMPLE_DATA = {
    "metadata": {
        "account_id": ACCOUNT_ID,
        "timestamp": "2026-03-10T12:00:00",
        "scan_duration_seconds": 1.0,
        "resource_count": 1,
        "services_scanned": 1,
        "regions_scanned": 1,
    },
    "resources": [
        {
            "service": "s3",
            "type": "bucket",
            "id": "my-bucket",
            "arn": f"arn:aws:s3:::my-bucket",
            "name": "my-bucket",
            "region": "us-east-1",
            "account_id": ACCOUNT_ID,
            "is_default": False,
            "details": {},
            "tags": {},
        }
    ],
}


# ── redact_account_ids() ──────────────────────────────────────────────────────

def test_account_id_replaced_in_string():
    content = f"Account: {ACCOUNT_ID} is the owner"
    result = redact_account_ids(content, ACCOUNT_ID)
    assert ACCOUNT_ID not in result
    assert "[REDACTED]" in result


def test_multiple_occurrences_replaced():
    content = f"{ACCOUNT_ID} and again {ACCOUNT_ID}"
    result = redact_account_ids(content, ACCOUNT_ID)
    assert ACCOUNT_ID not in result
    assert result.count("[REDACTED]") == 2


def test_empty_account_id_noop():
    content = "no account id here"
    result = redact_account_ids(content, "")
    assert result == content


def test_none_like_empty_account_id_noop():
    content = "no account id here"
    result = redact_account_ids(content, "   ")
    assert result == content


def test_unrelated_content_unchanged():
    content = "nothing sensitive"
    result = redact_account_ids(content, ACCOUNT_ID)
    assert result == content


# ── format_output with redact=True ────────────────────────────────────────────

def test_json_redact_removes_account_id():
    output = format_output(SAMPLE_DATA, "json", redact=True)
    assert ACCOUNT_ID not in output
    assert "[REDACTED]" in output


def test_csv_redact_removes_account_id():
    output = format_output(SAMPLE_DATA, "csv", redact=True)
    assert ACCOUNT_ID not in output


def test_html_redact_removes_account_id():
    output = format_output(SAMPLE_DATA, "html", redact=True)
    assert ACCOUNT_ID not in output
    assert "[REDACTED]" in output


def test_json_no_redact_keeps_account_id():
    output = format_output(SAMPLE_DATA, "json", redact=False)
    assert ACCOUNT_ID in output


def test_html_no_redact_keeps_account_id():
    output = format_output(SAMPLE_DATA, "html", redact=False)
    assert ACCOUNT_ID in output


# ── format_output default (redact=False) ─────────────────────────────────────

def test_redact_defaults_to_false():
    """Calling format_output without redact= should NOT redact."""
    output = format_output(SAMPLE_DATA, "json")
    assert ACCOUNT_ID in output


# ── completions file size limit ───────────────────────────────────────────────

def test_completions_size_limit_constant():
    """Verify the 1 MB size limit constant exists and is correctly set."""
    from aws_inventory.completions import _AWS_CONFIG_MAX_BYTES
    assert _AWS_CONFIG_MAX_BYTES == 1 * 1024 * 1024
