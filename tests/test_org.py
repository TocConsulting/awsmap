"""
Tests for AWS Organizations discovery, scoped session policy, and orchestrator.
"""

import json
import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from aws_inventory.org import (
    DEFAULT_ROLE_NAME,
    SENSITIVE_DATA_DENY_ACTIONS,
    build_scoped_session_policy,
    discover_org_accounts,
    assume_member_role,
    probe_role_access,
    OrgInventoryOrchestrator,
)
from aws_inventory.cli import main


def test_build_scoped_session_policy_default():
    """Verify default session policy generates valid minified JSON under 2048 chars."""
    policy_str = build_scoped_session_policy()
    assert len(policy_str) <= 2048

    policy = json.loads(policy_str)
    assert policy["Version"] == "2012-10-17"
    statements = policy["Statement"]
    assert len(statements) == 2

    # Statement 1: Read-only Allow
    allow_stmt = next(s for s in statements if s["Effect"] == "Allow")
    assert allow_stmt["Action"] == ["*"]
    assert allow_stmt["Resource"] == "*"

    # Statement 2: Explicit Deny on sensitive data access
    deny_stmt = next(s for s in statements if s["Effect"] == "Deny")
    assert "s3:GetObject*" in deny_stmt["Action"]
    assert "secretsmanager:GetSecretValue" in deny_stmt["Action"]
    assert "kms:Decrypt" in deny_stmt["Action"]
    assert "dynamodb:GetItem" in deny_stmt["Action"]
    assert deny_stmt["Resource"] == "*"


def test_build_scoped_session_policy_services_filter():
    """Verify service-specific session policy only grants access to requested services."""
    policy_str = build_scoped_session_policy(services=["ec2", "s3", "lambda_"])
    assert len(policy_str) <= 2048

    policy = json.loads(policy_str)
    allow_stmt = next(s for s in policy["Statement"] if s["Effect"] == "Allow")
    actions = allow_stmt["Action"]

    assert "ec2:Describe*" in actions
    assert "s3:List*" in actions
    assert "lambda:Get*" in actions
    assert "*:Describe*" not in actions


def test_discover_org_accounts_filtering():
    """Test account discovery skips suspended accounts and prioritizes management account."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client

    mock_client.describe_organization.return_value = {
        "Organization": {
            "MasterAccountId": "111111111111",
            "Id": "o-1234567890",
        }
    }

    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [
        {
            "Accounts": [
                {"Id": "222222222222", "Name": "App-Dev", "Status": "ACTIVE", "Email": "dev@example.com"},
                {"Id": "333333333333", "Name": "Old-Suspended", "Status": "SUSPENDED", "Email": "old@example.com"},
                {"Id": "111111111111", "Name": "Root-Mgmt", "Status": "ACTIVE", "Email": "root@example.com"},
                {"Id": "444444444444", "Name": "App-Prod", "Status": "ACTIVE", "Email": "prod@example.com"},
            ]
        }
    ]

    accounts = discover_org_accounts(mock_session)

    # Suspended account should be excluded
    acct_ids = [a["id"] for a in accounts]
    assert "333333333333" not in acct_ids
    assert len(accounts) == 3

    # Management account should be sorted first
    assert accounts[0]["id"] == "111111111111"
    assert accounts[0]["is_management"] is True


def test_discover_org_accounts_include_exclude():
    """Test include and exclude filters."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    mock_client.describe_organization.return_value = {
        "Organization": {"MasterAccountId": "111111111111"}
    }
    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [
        {
            "Accounts": [
                {"Id": "111111111111", "Name": "Mgmt", "Status": "ACTIVE"},
                {"Id": "222222222222", "Name": "Dev", "Status": "ACTIVE"},
                {"Id": "333333333333", "Name": "Stage", "Status": "ACTIVE"},
                {"Id": "444444444444", "Name": "Prod", "Status": "ACTIVE"},
            ]
        }
    ]

    # Include filter
    inc_res = discover_org_accounts(mock_session, include_accounts=["222222222222", "444444444444"])
    assert [a["id"] for a in inc_res] == ["222222222222", "444444444444"]

    # Exclude filter
    exc_res = discover_org_accounts(mock_session, exclude_accounts=["333333333333"])
    assert "333333333333" not in [a["id"] for a in exc_res]
    assert len(exc_res) == 3


def test_discover_org_accounts_name_and_alias_matching(tmp_path):
    """Test matching accounts by Organization Name, Email, and local DB alias."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    mock_client.describe_organization.return_value = {
        "Organization": {"MasterAccountId": "976885433559"}
    }
    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [
        {
            "Accounts": [
                {"Id": "976885433559", "Name": "tocconsulting", "Status": "ACTIVE", "Email": "root@toc.com"},
                {"Id": "111122223333", "Name": "KloudSec-Sandbox", "Status": "ACTIVE", "Email": "sandbox@kloudsec.com"},
                {"Id": "444455556666", "Name": "Tarek Personal", "Status": "ACTIVE", "Email": "tarek-cheikh@gmail.com"},
            ]
        }
    ]

    # Create dummy sqlite db with an alias
    db_file = str(tmp_path / "test_inventory.db")
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE scans (account_id TEXT, account_alias TEXT, profile TEXT, timestamp TEXT)"
    )
    conn.execute(
        "INSERT INTO scans VALUES ('111122223333', 'kloudsec-alias', 'toc-sandbox-profile', '2026-01-01')"
    )
    conn.commit()
    conn.close()

    # 1. Match by organization account name (e.g. kloudsec-sandbox)
    res_name = discover_org_accounts(
        mock_session,
        include_accounts=["kloudsec-sandbox"],
        db_path=db_file,
    )
    assert len(res_name) == 1
    assert res_name[0]["id"] == "111122223333"

    # 2. Match by email user-domain combination (e.g. tarek-cheikh-gmail)
    res_email = discover_org_accounts(
        mock_session,
        include_accounts=["tarek-cheikh-gmail"],
        db_path=db_file,
    )
    assert len(res_email) == 1
    assert res_email[0]["id"] == "444455556666"

    # 3. Match both comma-separated
    res_both = discover_org_accounts(
        mock_session,
        include_accounts=["kloudsec-sandbox", "tarek-cheikh-gmail"],
        db_path=db_file,
    )
    assert len(res_both) == 2
    assert {a["id"] for a in res_both} == {"111122223333", "444455556666"}

    # 4. Match by SQLite db alias
    res_alias = discover_org_accounts(
        mock_session,
        include_accounts=["kloudsec-alias"],
        db_path=db_file,
    )
    assert len(res_alias) == 1
    assert res_alias[0]["id"] == "111122223333"


def test_discover_org_accounts_no_match_rich_error():
    """Verify that a helpful error message listing available accounts is raised on no match."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    mock_client.describe_organization.return_value = {
        "Organization": {"MasterAccountId": "976885433559"}
    }
    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [
        {
            "Accounts": [
                {"Id": "111122223333", "Name": "KloudSec-Sandbox", "Status": "ACTIVE", "Email": "sandbox@kloudsec.com"},
            ]
        }
    ]

    with pytest.raises(ValueError) as excinfo:
        discover_org_accounts(mock_session, include_accounts=["non-existent-account"])

    err_msg = str(excinfo.value)
    assert "No active member accounts matched criteria: 'non-existent-account'" in err_msg
    assert "KloudSec-Sandbox" in err_msg
    assert "111122223333" in err_msg



@patch("aws_inventory.org.boto3.Session")
def test_assume_member_role(mock_boto_session_cls):
    """Test role assumption with session policy."""
    root_session = MagicMock()
    sts_client = MagicMock()
    root_session.client.return_value = sts_client

    sts_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIA_TEST",
            "SecretAccessKey": "SECRET_TEST",
            "SessionToken": "TOKEN_TEST",
        }
    }

    session = assume_member_role(
        root_session,
        account_id="222222222222",
        role_name="CustomOrgRole",
        session_policy='{"Version":"2012-10-17"}',
        external_id="ext-123",
    )

    sts_client.assume_role.assert_called_once_with(
        RoleArn="arn:aws:iam::222222222222:role/CustomOrgRole",
        RoleSessionName="awsmap-222222",
        DurationSeconds=3600,
        ExternalId="ext-123",
        Policy='{"Version":"2012-10-17"}',
        PolicyArns=[{"arn": "arn:aws:iam::aws:policy/ReadOnlyAccess"}],
    )


def test_orchestrator_dry_run():
    """Test dry-run mode returns access matrix without scanning."""
    root_session = MagicMock()
    orchestrator = OrgInventoryOrchestrator(
        root_session=root_session,
        role_name=DEFAULT_ROLE_NAME,
        session_policy="{}",
        quiet=True,
    )

    accounts = [
        {"id": "111111111111", "name": "Mgmt", "is_management": True},
        {"id": "222222222222", "name": "Dev", "is_management": False},
    ]

    with patch("aws_inventory.org.probe_role_access", return_value=(True, None)):
        res = orchestrator.execute(accounts, dry_run=True)

    assert res["dry_run"] is True
    assert res["total"] == 2
    assert res["accessible"] == 2
    assert res["inaccessible"] == 0


def test_cli_org_help():
    """Verify that 'awsmap org --help' displays options and examples."""
    runner = CliRunner()
    result = runner.invoke(main, ["org", "--help"])
    assert result.exit_code == 0
    assert "--profile" in result.output
    assert "--role-name" in result.output
    assert "--session-policy" in result.output
    assert "--concurrency" in result.output
    assert "--workers" in result.output
    assert "--ou" in result.output
    assert "--resume" in result.output
    assert "--dry-run" in result.output


def test_collect_all_thread_safety_concurrent():
    """Verify concurrent collect_all calls do not clobber state or raise KeyError."""
    from aws_inventory.collector import collect_all
    from concurrent.futures import ThreadPoolExecutor

    mock_session = MagicMock()
    with patch("aws_inventory.collector.get_account_id", return_value="123456789012"), \
         patch("aws_inventory.collector.collect_service_resources", return_value=([], 0.01)), \
         patch("aws_inventory.collector.collect_s3_with_region_filter", return_value=([], 0.01)):

        def run_collect():
            return collect_all(
                mock_session,
                services=["s3", "ec2", "elbv2", "vpc-lattice"],
                regions=["us-east-1", "eu-west-1"],
                max_workers=5,
                validate_regions=False,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(run_collect) for _ in range(8)]
            results = [f.result() for f in futures]

        assert len(results) == 8
        for r in results:
            assert r["metadata"]["account_id"] == "123456789012"
            assert "resources" in r


def test_orchestrator_multi_account_scan_execution(tmp_path):
    """Verify orchestrator dispatches every account to the engine and stores results."""
    from aws_inventory.engine import AccountPlan

    root_session = MagicMock()
    db_file = str(tmp_path / "test_exec.db")

    orchestrator = OrgInventoryOrchestrator(
        root_session=root_session,
        role_name=DEFAULT_ROLE_NAME,
        session_policy=None,
        account_concurrency=4,
        threads_per_process=5,
        processes=2,
        services=["s3"],
        regions=["us-east-1"],
        db_path=db_file,
        quiet=True,
    )

    accounts = [
        {"id": "111111111111", "name": "Mgmt", "is_management": True},
        {"id": "222222222222", "name": "Dev", "is_management": False},
        {"id": "333333333333", "name": "Prod", "is_management": False},
    ]

    class FakeEngine:
        def __init__(self, prepare_account, on_account_done, **kwargs):
            self.prepare_account = prepare_account
            self.on_account_done = on_account_done

        def run(self, accts):
            for a in accts:
                plan = self.prepare_account(a)
                assert plan.tasks == [("s3", None)]
                resources = [{"service": "s3", "type": "bucket", "id": f"b{i}", "name": f"b{i}",
                              "region": "us-east-1"} for i in range(5)]
                result = {
                    "metadata": {
                        "account_id": a["id"],
                        "timestamp": "2026-01-01 00:00:00 UTC",
                        "scan_duration_seconds": 1.0,
                        "services_scanned": 1,
                        "services_scanned_list": ["s3"],
                        "regions_scanned": 1,
                        "resource_count": 5,
                    },
                    "resources": resources,
                }
                self.on_account_done(a, result, None, 1.0)

    creds = {"AccessKeyId": "AK", "SecretAccessKey": "SK", "SessionToken": "TK"}
    with patch.object(orchestrator, "run_preflight") as mock_preflight, \
         patch("aws_inventory.org.assume_member_role_credentials", return_value=creds), \
         patch("aws_inventory.org.OrgScanEngine", FakeEngine):

        mock_preflight.return_value = [
            {**a, "can_assume": True, "error": None} for a in accounts
        ]

        summary = orchestrator.execute(accounts)

    assert summary["total_accounts"] == 3
    assert summary["completed_accounts"] == 3
    assert summary["failed_accounts"] == 0
    assert summary["total_resources"] == 15

    conn = sqlite3.connect(db_file)
    stored = {row[0] for row in conn.execute("SELECT account_id FROM scans")}
    conn.close()
    assert stored == {"111111111111", "222222222222", "333333333333"}
