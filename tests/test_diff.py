"""Tests for the drift detection engine."""

import json
import sqlite3
import os
import sys
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cmips_inventory.diff import (
    normalize_timestamp, reconstruct_snapshot, reconstruct_current_snapshot,
    compute_diff, build_summary, resource_key, _parse_json, _compute_tag_diffs,
    _dict_diff, snapshot_metadata
)
from cmips_inventory.diff_formatter import format_diff_table, format_diff_json, format_diff_html
from cmips_inventory.db import get_connection, SCHEMA_SQL


def _create_test_db(tmp_path):
    """Create a test database with schema."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resources_current "
        "ON resources(is_current, account_id, service)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scans_timestamp "
        "ON scans(timestamp)"
    )
    return conn


def _insert_scan(conn, scan_id, account_id, timestamp, resource_count=0,
                 scanned_services=None):
    """Insert a scan record.

    scanned_services=None leaves the column NULL (legacy scan -> reconstruct falls
    back to resource-derived services). Pass a list to record covered services.
    """
    conn.execute(
        "INSERT INTO scans (scan_id, account_id, timestamp, resource_count, scanned_services) "
        "VALUES (?, ?, ?, ?, ?)",
        (scan_id, account_id, timestamp, resource_count,
         json.dumps(scanned_services) if scanned_services is not None else None)
    )


def _insert_resource(conn, scan_id, service, rtype, rid, name=None,
                     region='us-east-1', account_id='111111111111',
                     details=None, tags=None, is_current=1):
    """Insert a resource record."""
    conn.execute(
        "INSERT INTO resources (scan_id, service, type, id, name, region, "
        "account_id, is_current, details, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (scan_id, service, rtype, rid, name, region, account_id, is_current,
         json.dumps(details or {}), json.dumps(tags or {}))
    )


# ─── normalize_timestamp tests ───

def test_normalize_timestamp_date_only():
    result = normalize_timestamp('2026-01-15')
    assert result == '2026-01-15 23:59:59 UTC'


def test_normalize_timestamp_datetime():
    result = normalize_timestamp('2026-01-15T14:30:00')
    assert result == '2026-01-15 14:30:00 UTC'


def test_normalize_timestamp_relative():
    result = normalize_timestamp('30d')
    # Should be a valid timestamp string
    assert 'UTC' in result
    assert len(result) > 10


def test_normalize_timestamp_yesterday():
    result = normalize_timestamp('yesterday')
    assert '23:59:59 UTC' in result


def test_normalize_timestamp_today():
    result = normalize_timestamp('today')
    assert '23:59:59 UTC' in result


# ─── resource_key tests ───

def test_resource_key_basic():
    r = {'account_id': '111', 'service': 'ec2', 'type': 'instance',
         'id': 'i-abc', 'region': 'us-east-1'}
    assert resource_key(r) == ('111', 'ec2', 'instance', 'i-abc', 'us-east-1')


def test_resource_key_null_region():
    r = {'account_id': '111', 'service': 'iam', 'type': 'user',
         'id': 'admin', 'region': None}
    assert resource_key(r) == ('111', 'iam', 'user', 'admin', '')


def test_resource_key_missing_region():
    r = {'account_id': '111', 'service': 'iam', 'type': 'user', 'id': 'admin'}
    assert resource_key(r) == ('111', 'iam', 'user', 'admin', '')


# ─── _parse_json tests ───

def test_parse_json_string():
    assert _parse_json('{"a": 1}') == {'a': 1}


def test_parse_json_dict():
    assert _parse_json({'a': 1}) == {'a': 1}


def test_parse_json_none():
    assert _parse_json(None) == {}


def test_parse_json_empty():
    assert _parse_json('') == {}


def test_parse_json_invalid():
    assert _parse_json('not json') == {}


# ─── _dict_diff tests ───

def test_dict_diff_no_changes():
    assert _dict_diff({'a': 1, 'b': 2}, {'a': 1, 'b': 2}) == []


def test_dict_diff_changed():
    result = _dict_diff({'a': 1}, {'a': 2})
    assert result == [{'field': 'a', 'from': 1, 'to': 2}]


def test_dict_diff_added():
    result = _dict_diff({}, {'a': 1})
    assert result == [{'field': 'a', 'from': None, 'to': 1}]


def test_dict_diff_removed():
    result = _dict_diff({'a': 1}, {})
    assert result == [{'field': 'a', 'from': 1, 'to': None}]


# ─── _compute_tag_diffs tests ───

def test_tag_diffs_no_changes():
    assert _compute_tag_diffs({'a': '1'}, {'a': '1'}) is None


def test_tag_diffs_added():
    result = _compute_tag_diffs({}, {'Env': 'prod'})
    assert result == {'added': {'Env': 'prod'}, 'removed': {}, 'changed': {}}


def test_tag_diffs_removed():
    result = _compute_tag_diffs({'Env': 'prod'}, {})
    assert result == {'added': {}, 'removed': {'Env': 'prod'}, 'changed': {}}


def test_tag_diffs_changed():
    result = _compute_tag_diffs({'Env': 'staging'}, {'Env': 'prod'})
    assert result == {
        'added': {}, 'removed': {},
        'changed': {'Env': {'from': 'staging', 'to': 'prod'}}
    }


def test_tag_diffs_mixed():
    result = _compute_tag_diffs(
        {'Env': 'staging', 'Old': 'yes'},
        {'Env': 'prod', 'New': 'yes'}
    )
    assert result['added'] == {'New': 'yes'}
    assert result['removed'] == {'Old': 'yes'}
    assert result['changed'] == {'Env': {'from': 'staging', 'to': 'prod'}}


# ─── reconstruct_snapshot tests ───

def test_reconstruct_empty_db(tmp_path):
    conn = _create_test_db(tmp_path)
    snapshot = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC')
    assert snapshot == {}
    conn.close()


def test_reconstruct_single_scan(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 2)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-bbb', 'web-2')
    conn.commit()

    snapshot = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC')
    assert len(snapshot) == 2
    conn.close()


def test_reconstruct_partial_scans(tmp_path):
    conn = _create_test_db(tmp_path)
    # EC2 scanned Jan 5
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-05 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    # Lambda scanned Jan 10
    _insert_scan(conn, 'scan2', '111111111111', '2026-01-10 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan2', 'lambda', 'function', 'my-func', 'my-func')
    conn.commit()

    # Snapshot at Jan 15 should include both
    snapshot = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC')
    assert len(snapshot) == 2
    services = {r['service'] for r in snapshot.values()}
    assert services == {'ec2', 'lambda'}
    conn.close()


def test_reconstruct_superseded_scan(tmp_path):
    conn = _create_test_db(tmp_path)
    # EC2 scanned Jan 5 (old)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-05 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1',
                     details={'state': 'stopped'})
    # EC2 scanned Jan 10 (new)
    _insert_scan(conn, 'scan2', '111111111111', '2026-01-10 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan2', 'ec2', 'instance', 'i-aaa', 'web-1',
                     details={'state': 'running'})
    conn.commit()

    snapshot = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC')
    assert len(snapshot) == 1
    r = list(snapshot.values())[0]
    details = json.loads(r['details'])
    assert details['state'] == 'running'  # Should be from Jan 10 scan
    conn.close()


def test_reconstruct_cutoff_excludes_future(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-02-01 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    conn.commit()

    # Cutoff Jan 15 should NOT include Feb 1 scan
    snapshot = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC')
    assert len(snapshot) == 0
    conn.close()


def test_reconstruct_with_account_filter(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1',
                     account_id='111111111111')
    _insert_scan(conn, 'scan2', '222222222222', '2026-01-10 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan2', 'ec2', 'instance', 'i-bbb', 'web-2',
                     account_id='222222222222')
    conn.commit()

    snapshot = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC',
                                   account_id='111111111111')
    assert len(snapshot) == 1
    assert list(snapshot.values())[0]['id'] == 'i-aaa'
    conn.close()


def test_reconstruct_with_service_filter(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 2)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    _insert_resource(conn, 'scan1', 's3', 'bucket', 'my-bucket', 'my-bucket')
    conn.commit()

    snapshot = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC',
                                   services=['ec2'])
    assert len(snapshot) == 1
    assert list(snapshot.values())[0]['service'] == 'ec2'
    conn.close()


# ─── reconstruct_snapshot: scanned-but-empty representation ───

def test_reconstruct_scanned_but_empty_service_is_empty(tmp_path):
    """A later scan that covered a service but found nothing represents it as
    empty - the resource from an earlier scan must NOT linger in the snapshot."""
    conn = _create_test_db(tmp_path)
    # Jan 10: ec2 scanned, has one instance.
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 1,
                 scanned_services=['ec2'])
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    # Jan 20: ec2 scanned again, but found nothing (instance terminated).
    _insert_scan(conn, 'scan2', '111111111111', '2026-01-20 10:00:00 UTC', 0,
                 scanned_services=['ec2'])
    conn.commit()

    snapshot = reconstruct_snapshot(conn, '2026-01-25 23:59:59 UTC')
    assert snapshot == {}  # ec2 is empty as of the latest covering scan
    conn.close()


def test_reconstruct_legacy_scan_without_coverage_falls_back(tmp_path):
    """Scans written before the scanned_services column (NULL) fall back to the
    services present in their resources - preserving the prior behavior."""
    conn = _create_test_db(tmp_path)
    # Legacy scan: scanned_services NULL.
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    conn.commit()

    snapshot = reconstruct_snapshot(conn, '2026-01-25 23:59:59 UTC')
    assert len(snapshot) == 1
    conn.close()


def test_reconstruct_empty_scan_does_not_hide_other_services(tmp_path):
    """An empty re-scan of one service must not affect a different service."""
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 2,
                 scanned_services=['ec2', 's3'])
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    _insert_resource(conn, 'scan1', 's3', 'bucket', 'b-1', 'b-1')
    # Later scan covers only ec2, empty.
    _insert_scan(conn, 'scan2', '111111111111', '2026-01-20 10:00:00 UTC', 0,
                 scanned_services=['ec2'])
    conn.commit()

    snapshot = reconstruct_snapshot(conn, '2026-01-25 23:59:59 UTC')
    services = {r['service'] for r in snapshot.values()}
    assert services == {'s3'}  # ec2 now empty, s3 still present from scan1
    conn.close()


# ─── reconstruct_current_snapshot tests ───

def test_reconstruct_current(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 2)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1', is_current=1)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-bbb', 'web-old', is_current=0)
    conn.commit()

    snapshot = reconstruct_current_snapshot(conn)
    assert len(snapshot) == 1
    assert list(snapshot.values())[0]['id'] == 'i-aaa'
    conn.close()


# ─── compute_diff tests ───

def test_diff_all_added():
    from_snap = {}
    to_snap = {
        ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1'): {
            'account_id': '111', 'service': 'ec2', 'type': 'instance',
            'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
            'details': '{}', 'tags': '{}'
        }
    }
    result = compute_diff(from_snap, to_snap)
    assert len(result['added']) == 1
    assert len(result['removed']) == 0
    assert len(result['modified']) == 0
    assert len(result['unchanged']) == 0


def test_diff_all_removed():
    from_snap = {
        ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1'): {
            'account_id': '111', 'service': 'ec2', 'type': 'instance',
            'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
            'details': '{}', 'tags': '{}'
        }
    }
    to_snap = {}
    result = compute_diff(from_snap, to_snap)
    assert len(result['added']) == 0
    assert len(result['removed']) == 1
    assert len(result['modified']) == 0
    assert len(result['unchanged']) == 0


def test_diff_no_changes():
    resource = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{"state": "running"}', 'tags': '{"Env": "prod"}'
    }
    key = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    result = compute_diff({key: resource}, {key: resource})
    assert len(result['unchanged']) == 1
    assert len(result['added']) == 0
    assert len(result['removed']) == 0
    assert len(result['modified']) == 0


def test_diff_modified_details():
    key = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    r_from = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{"state": "stopped", "instance_type": "t3.micro"}',
        'tags': '{}'
    }
    r_to = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{"state": "running", "instance_type": "t3.large"}',
        'tags': '{}'
    }
    result = compute_diff({key: r_from}, {key: r_to})
    assert len(result['modified']) == 1
    changes = result['modified'][0]['changes']
    assert 'details' in changes
    detail_fields = {d['field'] for d in changes['details']}
    assert 'state' in detail_fields
    assert 'instance_type' in detail_fields


def test_diff_modified_tags():
    key = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    r_from = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{}',
        'tags': '{"Env": "staging", "Old": "yes"}'
    }
    r_to = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{}',
        'tags': '{"Env": "prod", "New": "yes"}'
    }
    result = compute_diff({key: r_from}, {key: r_to})
    assert len(result['modified']) == 1
    tag_changes = result['modified'][0]['changes']['tags']
    assert tag_changes['added'] == {'New': 'yes'}
    assert tag_changes['removed'] == {'Old': 'yes'}
    assert 'Env' in tag_changes['changed']


def test_diff_modified_name():
    key = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    r_from = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'old-name',
        'details': '{}', 'tags': '{}'
    }
    r_to = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'new-name',
        'details': '{}', 'tags': '{}'
    }
    result = compute_diff({key: r_from}, {key: r_to})
    assert len(result['modified']) == 1
    assert result['modified'][0]['changes']['name'] == {'from': 'old-name', 'to': 'new-name'}


def test_diff_ignore_tags():
    key = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    r_from = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{}', 'tags': '{"Env": "staging"}'
    }
    r_to = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{}', 'tags': '{"Env": "prod"}'
    }
    # With ignore_tags=True, tag-only change should be unchanged
    result = compute_diff({key: r_from}, {key: r_to}, ignore_tags=True)
    assert len(result['unchanged']) == 1
    assert len(result['modified']) == 0


def test_diff_mixed():
    base = {'account_id': '111', 'region': 'us-east-1'}
    from_snap = {
        ('111', 'ec2', 'instance', 'i-kept', 'us-east-1'): {
            **base, 'service': 'ec2', 'type': 'instance', 'id': 'i-kept',
            'name': 'kept', 'details': '{"state":"running"}', 'tags': '{}'
        },
        ('111', 'ec2', 'instance', 'i-removed', 'us-east-1'): {
            **base, 'service': 'ec2', 'type': 'instance', 'id': 'i-removed',
            'name': 'removed', 'details': '{}', 'tags': '{}'
        },
        ('111', 'ec2', 'instance', 'i-modified', 'us-east-1'): {
            **base, 'service': 'ec2', 'type': 'instance', 'id': 'i-modified',
            'name': 'modified', 'details': '{"state":"stopped"}', 'tags': '{}'
        },
    }
    to_snap = {
        ('111', 'ec2', 'instance', 'i-kept', 'us-east-1'): {
            **base, 'service': 'ec2', 'type': 'instance', 'id': 'i-kept',
            'name': 'kept', 'details': '{"state":"running"}', 'tags': '{}'
        },
        ('111', 'ec2', 'instance', 'i-added', 'us-east-1'): {
            **base, 'service': 'ec2', 'type': 'instance', 'id': 'i-added',
            'name': 'added', 'details': '{}', 'tags': '{}'
        },
        ('111', 'ec2', 'instance', 'i-modified', 'us-east-1'): {
            **base, 'service': 'ec2', 'type': 'instance', 'id': 'i-modified',
            'name': 'modified', 'details': '{"state":"running"}', 'tags': '{}'
        },
    }
    result = compute_diff(from_snap, to_snap)
    assert len(result['added']) == 1
    assert len(result['removed']) == 1
    assert len(result['modified']) == 1
    assert len(result['unchanged']) == 1


def test_natural_key_different_regions():
    """Same id in different regions = different resources."""
    key1 = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    key2 = ('111', 'ec2', 'instance', 'i-aaa', 'eu-west-1')
    r1 = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{}', 'tags': '{}'
    }
    r2 = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'eu-west-1', 'name': 'web-1',
        'details': '{}', 'tags': '{}'
    }
    from_snap = {key1: r1}
    to_snap = {key2: r2}
    result = compute_diff(from_snap, to_snap)
    # r1 removed (us-east-1), r2 added (eu-west-1)
    assert len(result['added']) == 1
    assert len(result['removed']) == 1


def test_json_key_ordering_no_false_positive():
    """Different JSON key ordering should NOT trigger a modification."""
    key = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    r_from = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{"a": 1, "b": 2}', 'tags': '{"X": "1", "Y": "2"}'
    }
    r_to = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{"b": 2, "a": 1}', 'tags': '{"Y": "2", "X": "1"}'
    }
    result = compute_diff({key: r_from}, {key: r_to})
    assert len(result['unchanged']) == 1
    assert len(result['modified']) == 0


def test_multi_account():
    r1 = {
        'account_id': '111', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{}', 'tags': '{}'
    }
    r2 = {
        'account_id': '222', 'service': 'ec2', 'type': 'instance',
        'id': 'i-aaa', 'region': 'us-east-1', 'name': 'web-1',
        'details': '{}', 'tags': '{}'
    }
    key1 = ('111', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    key2 = ('222', 'ec2', 'instance', 'i-aaa', 'us-east-1')
    from_snap = {key1: r1}
    to_snap = {key2: r2}
    result = compute_diff(from_snap, to_snap)
    # Different accounts = different resources
    assert len(result['added']) == 1
    assert len(result['removed']) == 1


# ─── build_summary tests ───

def test_build_summary():
    diff_result = {
        'added': [
            {'service': 'ec2', 'type': 'instance', 'id': 'i-1'},
            {'service': 'ec2', 'type': 'instance', 'id': 'i-2'},
            {'service': 's3', 'type': 'bucket', 'id': 'b-1'},
        ],
        'removed': [
            {'service': 'ec2', 'type': 'instance', 'id': 'i-3'},
        ],
        'modified': [
            {'resource': {'service': 'ec2', 'type': 'instance', 'id': 'i-4'},
             'changes': {'details': []}},
        ],
        'unchanged': [
            {'service': 's3', 'type': 'bucket', 'id': 'b-2'},
        ],
    }
    summary = build_summary(diff_result)
    assert summary['added'] == 3
    assert summary['removed'] == 1
    assert summary['modified'] == 1
    assert summary['unchanged'] == 1
    assert summary['by_service']['ec2']['added'] == 2
    assert summary['by_service']['ec2']['removed'] == 1
    assert summary['by_service']['ec2']['modified'] == 1
    assert summary['by_service']['s3']['added'] == 1
    assert summary['by_service']['s3']['unchanged'] == 1


# ─── snapshot_metadata tests ───

def test_snapshot_metadata(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 2)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    _insert_resource(conn, 'scan1', 's3', 'bucket', 'my-bucket', 'my-bucket')
    conn.commit()

    meta = snapshot_metadata(conn, '2026-01-15 23:59:59 UTC')
    assert meta['service_count'] == 2
    assert meta['latest_scan'] == '2026-01-10 10:00:00 UTC'
    assert sorted(meta['services']) == ['ec2', 's3']
    conn.close()


# ─── Integration: full pipeline with DB ───

def test_full_diff_pipeline(tmp_path):
    """End-to-end: create two scans, compute diff, format output."""
    conn = _create_test_db(tmp_path)

    # Scan 1: Jan 10 - 2 instances
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 2)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-kept', 'kept-server',
                     details={'state': 'running', 'instance_type': 't3.micro'})
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-removed', 'old-server',
                     details={'state': 'stopped'})

    # Scan 2: Feb 5 - 1 kept (modified) + 1 new
    _insert_scan(conn, 'scan2', '111111111111', '2026-02-05 10:00:00 UTC', 2)
    _insert_resource(conn, 'scan2', 'ec2', 'instance', 'i-kept', 'kept-server',
                     details={'state': 'running', 'instance_type': 't3.large'},
                     tags={'Env': 'prod'})
    _insert_resource(conn, 'scan2', 'ec2', 'instance', 'i-new', 'new-server',
                     details={'state': 'running'})
    conn.commit()

    # Build snapshots
    from_snap = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC')
    to_snap = reconstruct_snapshot(conn, '2026-02-10 23:59:59 UTC')

    assert len(from_snap) == 2
    assert len(to_snap) == 2

    # Compute diff
    diff_result = compute_diff(from_snap, to_snap)
    diff_result['_summary'] = build_summary(diff_result)

    assert len(diff_result['added']) == 1      # i-new
    assert len(diff_result['removed']) == 1    # i-removed
    assert len(diff_result['modified']) == 1   # i-kept (instance_type + tags changed)
    assert len(diff_result['unchanged']) == 0

    # Verify modified details
    mod = diff_result['modified'][0]
    assert mod['resource']['id'] == 'i-kept'
    detail_fields = {d['field'] for d in mod['changes']['details']}
    assert 'instance_type' in detail_fields
    assert 'tags' in mod['changes']

    # Format as table
    meta = {
        'from_date': '2026-01-15', 'to_date': '2026-02-10',
        'account_label': 'test [111111111111]',
        'from_info': '1 services', 'to_info': '1 services',
    }
    table_output = format_diff_table(diff_result, meta)
    assert 'ADDED (1)' in table_output
    assert 'REMOVED (1)' in table_output
    assert 'MODIFIED (1)' in table_output
    assert 'i-new' in table_output
    assert 'i-removed' in table_output
    assert 'i-kept' in table_output

    # Format as JSON
    json_output = format_diff_json(diff_result, meta)
    parsed = json.loads(json_output)
    assert parsed['summary']['added'] == 1
    assert parsed['summary']['removed'] == 1
    assert parsed['summary']['modified'] == 1
    assert len(parsed['added']) == 1
    assert len(parsed['removed']) == 1
    assert len(parsed['modified']) == 1

    # Format as HTML
    html_output = format_diff_html(diff_result, meta)
    assert '<!DOCTYPE html>' in html_output
    assert 'ADDED' in html_output
    assert 'REMOVED' in html_output
    assert 'MODIFIED' in html_output
    assert 'i-new' in html_output

    conn.close()


def test_full_diff_summary_mode(tmp_path):
    """Test summary-only output."""
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 'scan1', '111111111111', '2026-01-10 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan1', 'ec2', 'instance', 'i-aaa', 'web-1')
    _insert_scan(conn, 'scan2', '111111111111', '2026-02-05 10:00:00 UTC', 1)
    _insert_resource(conn, 'scan2', 'ec2', 'instance', 'i-bbb', 'web-2')
    conn.commit()

    from_snap = reconstruct_snapshot(conn, '2026-01-15 23:59:59 UTC')
    to_snap = reconstruct_snapshot(conn, '2026-02-10 23:59:59 UTC')
    diff_result = compute_diff(from_snap, to_snap)
    diff_result['_summary'] = build_summary(diff_result)

    meta = {'from_date': '2026-01-15', 'to_date': '2026-02-10',
            'account_label': '', 'from_info': '', 'to_info': ''}
    output = format_diff_table(diff_result, meta, summary_only=True)
    assert 'By Service:' in output
    assert 'ec2' in output
    # Should NOT have detailed resource rows
    assert 'ADDED (' not in output
    conn.close()


# ─── default-diff (bare `cmipsmap diff`) tests ───

from cmips_inventory.db import get_recent_scan_timestamps, get_scan_timestamp_before


def test_normalize_timestamp_utc_suffix_roundtrip():
    # Stored timestamps end in ' UTC' and must round-trip, not get mangled
    # by the T->space separator conversion (the 'UTC' -> 'U C' regression).
    assert normalize_timestamp('2026-06-09 18:00:00 UTC') == '2026-06-09 18:00:00 UTC'


def test_normalize_timestamp_t_separator_gets_utc():
    assert normalize_timestamp('2026-01-15T14:30:00') == '2026-01-15 14:30:00 UTC'


def test_recent_scan_timestamps_two_scans(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 's1', '111111111111', '2026-01-10 10:00:00 UTC')
    _insert_scan(conn, 's2', '111111111111', '2026-02-05 10:00:00 UTC')
    conn.commit()
    latest, prev = get_recent_scan_timestamps(conn)
    assert latest == '2026-02-05 10:00:00 UTC'
    assert prev == '2026-01-10 10:00:00 UTC'
    conn.close()


def test_recent_scan_timestamps_single_scan(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 's1', '111111111111', '2026-01-10 10:00:00 UTC')
    conn.commit()
    latest, prev = get_recent_scan_timestamps(conn)
    assert latest == '2026-01-10 10:00:00 UTC'
    assert prev is None
    conn.close()


def test_recent_scan_timestamps_no_scans(tmp_path):
    conn = _create_test_db(tmp_path)
    assert get_recent_scan_timestamps(conn) == (None, None)
    conn.close()


def test_recent_scan_timestamps_account_scoped(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 's1', '111111111111', '2026-01-10 10:00:00 UTC')
    _insert_scan(conn, 's2', '111111111111', '2026-02-05 10:00:00 UTC')
    _insert_scan(conn, 's3', '222222222222', '2026-03-01 10:00:00 UTC')
    conn.commit()
    latest, prev = get_recent_scan_timestamps(conn, account_id='111111111111')
    assert latest == '2026-02-05 10:00:00 UTC'
    assert prev == '2026-01-10 10:00:00 UTC'
    conn.close()


def test_scan_timestamp_before(tmp_path):
    conn = _create_test_db(tmp_path)
    _insert_scan(conn, 's1', '111111111111', '2026-01-10 10:00:00 UTC')
    _insert_scan(conn, 's2', '111111111111', '2026-02-05 10:00:00 UTC')
    conn.commit()
    assert get_scan_timestamp_before(conn, '2026-02-05 10:00:00 UTC') == '2026-01-10 10:00:00 UTC'
    assert get_scan_timestamp_before(conn, '2026-01-10 10:00:00 UTC') is None
    conn.close()


def test_default_diff_ignores_untouched_services_on_partial_rescan(tmp_path):
    # Scan A: full (ec2 + s3). Scan B: ec2 only, with one ec2 change.
    # Bare-diff defaulting reconstructs the previous state at A's timestamp and
    # compares against current. s3 (untouched by B) must NOT appear as removed.
    conn = _create_test_db(tmp_path)

    _insert_scan(conn, 'A', '111111111111', '2026-01-10 10:00:00 UTC',
                 scanned_services=['ec2', 's3'])
    _insert_resource(conn, 'A', 'ec2', 'instance', 'i-aaa', 'web-1', is_current=0)
    _insert_resource(conn, 'A', 's3', 'bucket', 'data-bucket', 'data-bucket', is_current=1)

    _insert_scan(conn, 'B', '111111111111', '2026-02-05 10:00:00 UTC',
                 scanned_services=['ec2'])
    _insert_resource(conn, 'B', 'ec2', 'instance', 'i-bbb', 'web-2', is_current=1)
    conn.commit()

    latest, prev_cutoff = get_recent_scan_timestamps(conn)
    assert latest == '2026-02-05 10:00:00 UTC'
    assert prev_cutoff == '2026-01-10 10:00:00 UTC'

    from_snap = reconstruct_snapshot(conn, prev_cutoff)
    to_snap = reconstruct_current_snapshot(conn)
    diff_result = compute_diff(from_snap, to_snap)

    services_removed = {r['service'] for r in diff_result['removed']}
    services_added = {r['service'] for r in diff_result['added']}
    # Only ec2 churned; s3 stayed put across the partial rescan.
    assert services_removed == {'ec2'}
    assert services_added == {'ec2'}
    assert all(r['service'] != 's3' for r in diff_result['removed'])
    conn.close()
