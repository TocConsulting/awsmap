"""Tests for the tag-compliance audit."""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cmips_inventory.db import SCHEMA_SQL
from cmips_inventory.tags_audit import audit_tags


def _db():
    conn = sqlite3.connect(':memory:')
    conn.executescript(SCHEMA_SQL)
    return conn


def _res(conn, service, rtype, rid, tags, account='111', is_default=0, is_current=1):
    conn.execute(
        "INSERT INTO resources (scan_id, service, type, id, name, region, "
        "account_id, is_default, is_current, details, tags) "
        "VALUES ('s', ?, ?, ?, ?, 'us-east-1', ?, ?, ?, '{}', ?)",
        (service, rtype, rid, rid, account, is_default, is_current, json.dumps(tags))
    )


def test_required_tags_compliance():
    conn = _db()
    _res(conn, 'ec2', 'instance', 'i-1', {'Owner': 'a', 'Environment': 'prod'})
    _res(conn, 'ec2', 'instance', 'i-2', {'Owner': 'b'})          # missing Environment
    _res(conn, 's3', 'bucket', 'b-1', {'Owner': 'c', 'Environment': 'dev'})
    conn.commit()
    r = audit_tags(conn, required=['Owner', 'Environment'])
    assert r['overall'] == {'compliant': 2, 'total': 3, 'pct': 67}
    assert r['per_tag']['Owner']['present'] == 3
    assert r['per_tag']['Environment']['present'] == 2
    assert len(r['noncompliant']) == 1
    assert r['noncompliant'][0]['id'] == 'i-2'
    assert r['noncompliant'][0]['missing'] == ['Environment']


def test_fallback_any_tag():
    conn = _db()
    _res(conn, 'ec2', 'instance', 'i-1', {'Owner': 'a'})
    _res(conn, 'ec2', 'instance', 'i-2', {})
    conn.commit()
    r = audit_tags(conn)
    assert r['overall']['compliant'] == 1
    assert r['overall']['total'] == 2
    assert r['noncompliant'][0]['id'] == 'i-2'
    assert r['noncompliant'][0]['untagged'] is True


def test_empty_value_is_noncompliant():
    conn = _db()
    _res(conn, 'ec2', 'instance', 'i-1', {'Owner': ''})   # blank Owner != compliant
    conn.commit()
    r = audit_tags(conn, required=['Owner'])
    assert r['overall']['compliant'] == 0
    assert r['noncompliant'][0]['missing'] == ['Owner']
    # has a tag key but it is empty -> not "untagged"
    assert r['noncompliant'][0]['untagged'] is False


def test_defaults_excluded_by_default():
    conn = _db()
    _res(conn, 'ec2', 'security-group', 'sg-default', {}, is_default=1)
    _res(conn, 'ec2', 'instance', 'i-1', {'Owner': 'a'})
    conn.commit()
    assert audit_tags(conn, required=['Owner'])['scope_count'] == 1
    assert audit_tags(conn, required=['Owner'], include_defaults=True)['scope_count'] == 2


def test_account_and_service_scope():
    conn = _db()
    _res(conn, 'ec2', 'instance', 'i-1', {'Owner': 'a'}, account='111')
    _res(conn, 'ec2', 'instance', 'i-2', {}, account='222')
    _res(conn, 's3', 'bucket', 'b-1', {}, account='111')
    conn.commit()
    assert audit_tags(conn, account_id='111')['scope_count'] == 2
    assert audit_tags(conn, services=['ec2'])['scope_count'] == 2
    assert audit_tags(conn, account_id='111', services=['s3'])['scope_count'] == 1


def test_special_char_tag_key():
    conn = _db()
    _res(conn, 'ec2', 'instance', 'i-1', {'cost:center': '100'})
    conn.commit()
    r = audit_tags(conn, required=['cost:center'])
    assert r['overall']['compliant'] == 1


def test_empty_scope():
    conn = _db()
    r = audit_tags(conn, required=['Owner'])
    assert r['scope_count'] == 0
    assert r['overall']['pct'] == 0
