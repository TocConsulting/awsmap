"""Tests for the waste / idle-resource detection rules.

Resources are inserted with the same detail field names the real collectors
emit (see collectors/ec2.py, elbv2.py, elb.py), so these assert the rules match
real scan output, not demo-only shapes.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cmips_inventory.db import SCHEMA_SQL
from cmips_inventory.waste import find_waste, RULE_KEYS


def _db():
    conn = sqlite3.connect(':memory:')
    conn.executescript(SCHEMA_SQL)
    return conn


def _res(conn, service, rtype, rid, details, account='111', is_default=0, is_current=1):
    conn.execute(
        "INSERT INTO resources (scan_id, service, type, id, name, region, "
        "account_id, is_default, is_current, details, tags) "
        "VALUES ('s', ?, ?, ?, ?, 'us-east-1', ?, ?, ?, ?, '{}')",
        (service, rtype, rid, rid, account, is_default, is_current, json.dumps(details))
    )


def _ids(result, key):
    return {r['id'] for r in result['findings'][key]}


def test_unattached_ebs():
    conn = _db()
    _res(conn, 'ec2', 'volume', 'vol-idle', {'state': 'available', 'size_gb': 8, 'volume_type': 'gp3'})
    _res(conn, 'ec2', 'volume', 'vol-used', {'state': 'in-use', 'size_gb': 8})
    conn.commit()
    assert _ids(find_waste(conn), 'unattached-ebs') == {'vol-idle'}


def test_unassociated_eip():
    conn = _db()
    _res(conn, 'ec2', 'elastic-ip', 'eip-idle',
         {'public_ip': '1.2.3.4', 'instance_id': None, 'network_interface_id': None})
    _res(conn, 'ec2', 'elastic-ip', 'eip-used',
         {'public_ip': '5.6.7.8', 'instance_id': 'i-1', 'network_interface_id': None})
    _res(conn, 'ec2', 'elastic-ip', 'eip-eni',
         {'public_ip': '9.9.9.9', 'instance_id': None, 'network_interface_id': 'eni-1'})
    conn.commit()
    assert _ids(find_waste(conn), 'unassociated-eip') == {'eip-idle'}


def test_available_eni():
    conn = _db()
    _res(conn, 'ec2', 'network-interface', 'eni-free', {'status': 'available'})
    _res(conn, 'ec2', 'network-interface', 'eni-busy', {'status': 'in-use'})
    conn.commit()
    assert _ids(find_waste(conn), 'available-eni') == {'eni-free'}


def test_idle_target_group():
    conn = _db()
    _res(conn, 'elbv2', 'target-group', 'tg-idle',
         {'healthy_targets': 0, 'unhealthy_targets': 0, 'target_type': 'ip', 'port': 80})
    _res(conn, 'elbv2', 'target-group', 'tg-live',
         {'healthy_targets': 2, 'unhealthy_targets': 0, 'target_type': 'ip', 'port': 80})
    _res(conn, 'elbv2', 'target-group', 'tg-unhealthy',
         {'healthy_targets': 0, 'unhealthy_targets': 3, 'target_type': 'ip', 'port': 80})
    conn.commit()
    assert _ids(find_waste(conn), 'idle-target-group') == {'tg-idle'}


def test_empty_classic_elb():
    conn = _db()
    _res(conn, 'elb', 'classic-load-balancer', 'clb-empty', {'instances': [], 'scheme': 'internal'})
    _res(conn, 'elb', 'classic-load-balancer', 'clb-full', {'instances': ['i-1', 'i-2'], 'scheme': 'internal'})
    conn.commit()
    assert _ids(find_waste(conn), 'empty-classic-elb') == {'clb-empty'}


def test_old_snapshot_and_ami_age_threshold():
    conn = _db()
    # 2000 is always older than (now - 90d); 2099 is always newer.
    _res(conn, 'ec2', 'snapshot', 'snap-old', {'start_time': '2000-01-01 00:00:00', 'size_gb': 8})
    _res(conn, 'ec2', 'snapshot', 'snap-new', {'start_time': '2099-01-01 00:00:00', 'size_gb': 8})
    _res(conn, 'ec2', 'ami', 'ami-old', {'creation_date': '2000-01-01T00:00:00.000Z'})
    _res(conn, 'ec2', 'ami', 'ami-new', {'creation_date': '2099-01-01T00:00:00.000Z'})
    conn.commit()
    r = find_waste(conn, min_age_days=90)
    assert _ids(r, 'old-snapshot') == {'snap-old'}
    assert _ids(r, 'old-ami') == {'ami-old'}


def test_stopped_instance():
    conn = _db()
    _res(conn, 'ec2', 'instance', 'i-stopped', {'state': 'stopped', 'instance_type': 't3.micro'})
    _res(conn, 'ec2', 'instance', 'i-running', {'state': 'running', 'instance_type': 't3.micro'})
    conn.commit()
    assert _ids(find_waste(conn), 'stopped-instance') == {'i-stopped'}


def test_defaults_excluded_by_default():
    conn = _db()
    _res(conn, 'ec2', 'network-interface', 'eni-default', {'status': 'available'}, is_default=1)
    _res(conn, 'ec2', 'network-interface', 'eni-user', {'status': 'available'})
    conn.commit()
    assert _ids(find_waste(conn), 'available-eni') == {'eni-user'}
    assert _ids(find_waste(conn, include_defaults=True), 'available-eni') == {'eni-default', 'eni-user'}


def test_account_scope_and_rule_filter():
    conn = _db()
    _res(conn, 'ec2', 'volume', 'vol-a', {'state': 'available'}, account='111')
    _res(conn, 'ec2', 'volume', 'vol-b', {'state': 'available'}, account='222')
    conn.commit()
    assert _ids(find_waste(conn, account_id='111'), 'unattached-ebs') == {'vol-a'}
    r = find_waste(conn, rule_keys=['unattached-ebs'])
    assert set(r['findings'].keys()) == {'unattached-ebs'}
    assert r['total'] == 2


def test_only_current_resources():
    conn = _db()
    _res(conn, 'ec2', 'volume', 'vol-old', {'state': 'available'}, is_current=0)
    _res(conn, 'ec2', 'volume', 'vol-cur', {'state': 'available'}, is_current=1)
    conn.commit()
    assert _ids(find_waste(conn), 'unattached-ebs') == {'vol-cur'}


def test_rule_keys_constant_matches_rules():
    assert 'unattached-ebs' in RULE_KEYS and len(RULE_KEYS) == 8
