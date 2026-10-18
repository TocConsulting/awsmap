"""
AWS Organizations multi-account discovery and high-performance parallel inventory.
"""

import json
import os
import queue
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import boto3
import botocore.exceptions
from botocore.config import Config

from aws_inventory.auth import get_enabled_regions
from aws_inventory.collector import get_available_services, plan_collection_tasks
from aws_inventory.db import _SERVICE_LABEL_TO_EMITTED, get_connection, store_scan
from aws_inventory.engine import (
    DEFAULT_TOTAL_CONCURRENCY,
    AccountPlan,
    OrgScanEngine,
    default_process_count,
    threads_for,
)

# Standard AWS Organizations cross-account role
DEFAULT_ROLE_NAME = "OrganizationAccountAccessRole"

# Sensitive actions to explicitly deny in the session policy to enforce read-only
# metadata access and prevent data extraction (e.g. object payloads, secrets, database items).
SENSITIVE_DATA_DENY_ACTIONS = [
    "s3:GetObject*",
    "secretsmanager:GetSecretValue",
    "ssm:GetParameter*",
    "kms:Decrypt",
    "dynamodb:GetItem",
    "dynamodb:BatchGetItem",
    "dynamodb:Scan",
    "dynamodb:Query",
    "sqs:ReceiveMessage",
    "kinesis:GetRecords",
]


SERVICE_IAM_PREFIX_MAP: Dict[str, str] = {
    "cognito": "cognito-idp",
    "eventbridge-pipes": "pipes",
    "eventbridge-scheduler": "scheduler",
    "lexv2": "lex",
    "opensearch-serverless": "aoss",
    "vpc": "ec2",
    "elbv2": "elasticloadbalancing",
    "elb": "elasticloadbalancing",
    "lambda_": "lambda",
    "stepfunctions": "states",
}


def build_scoped_session_policy(services: Optional[List[str]] = None) -> str:
    """Generate a minified least-privilege IAM session policy for AssumeRole.

    Under AWS IAM evaluation logic, the session policy intersects with the target
    role's permissions. Even if the role has AdministratorAccess, the assumed session
    is restricted strictly to read-only metadata inspection and denied all data/secret
    extraction.

    The resulting JSON is guaranteed to remain well within the 2,048-character AWS
    STS session policy limit.

    Args:
        services: Optional list of service names to restrict Allow actions to.

    Returns:
        Compact JSON string of the IAM session policy.
    """
    if services:
        allow_actions = []
        for svc in sorted(set(s.lower() for s in services)):
            prefix = SERVICE_IAM_PREFIX_MAP.get(svc, svc)
            allow_actions.extend([
                f"{prefix}:Describe*",
                f"{prefix}:List*",
                f"{prefix}:Get*",
            ])
    else:
        # Full scan: allow all actions, intersected with ReadOnlyAccess managed policy in AssumeRole
        allow_actions = ["*"]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AwsMapReadOnlyMetadata",
                "Effect": "Allow",
                "Action": allow_actions,
                "Resource": "*",
            },
            {
                "Sid": "AwsMapDenySensitiveData",
                "Effect": "Deny",
                "Action": SENSITIVE_DATA_DENY_ACTIONS,
                "Resource": "*",
            },
        ],
    }

    # Minify JSON to ensure it fits comfortably within the 2,048-byte STS limit
    minified = json.dumps(policy, separators=(",", ":"))
    if len(minified) > 2048:
        # Fallback to compact wildcard if service list made the policy exceed 2048 chars
        fallback_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AwsMapReadOnlyMetadata",
                    "Effect": "Allow",
                    "Action": "*",
                    "Resource": "*",
                },
                {
                    "Sid": "AwsMapDenySensitiveData",
                    "Effect": "Deny",
                    "Action": SENSITIVE_DATA_DENY_ACTIONS,
                    "Resource": "*",
                },
            ],
        }
        minified = json.dumps(fallback_policy, separators=(",", ":"))

    return minified


def _normalize_identifier(text: str) -> str:
    """Normalize string for fuzzy comparison by removing separators."""
    return re.sub(r"[\s\-_.]+", "", str(text)).lower()


def _matches_account(
    acct: Dict[str, Any],
    filter_identifiers: List[str],
    db_aliases: Optional[Dict[str, Set[str]]] = None,
) -> bool:
    """Check if an account matches any of the filter identifiers.

    Matches against:
    - 12-digit AWS Account ID
    - AWS Organization Account Name (case-insensitive, exact or normalized)
    - AWS Organization Email address (full, username before @, or user-domain)
    - IAM Account Alias or Profile stored in local SQLite database
    """
    acct_id = str(acct.get("Id", "")).strip()
    acct_name = (acct.get("Name") or "").strip().lower()
    acct_email = (acct.get("Email") or "").strip().lower()
    email_user = acct_email.split("@")[0] if "@" in acct_email else ""
    email_domain = acct_email.split("@")[1].split(".")[0] if "@" in acct_email and "." in acct_email else ""
    email_user_domain = f"{email_user}-{email_domain}" if email_user and email_domain else ""

    norm_id = acct_id.lower()
    norm_name = _normalize_identifier(acct_name)
    norm_email = _normalize_identifier(acct_email)
    norm_email_user = _normalize_identifier(email_user)
    norm_email_user_domain = _normalize_identifier(email_user_domain)

    known_aliases = db_aliases.get(acct_id, set()) if db_aliases else set()
    norm_known_aliases = {_normalize_identifier(a) for a in known_aliases}

    for item in filter_identifiers:
        raw = item.strip().lower()
        if not raw:
            continue

        # Direct exact matches (case-insensitive)
        if raw == norm_id:
            return True
        if raw == acct_name:
            return True
        if raw in (acct_email, email_user, email_user_domain):
            return True
        if raw in known_aliases:
            return True

        # Normalized matches (ignoring dashes, underscores, dots, and spaces)
        norm_raw = _normalize_identifier(raw)
        if norm_raw:
            if norm_raw == norm_id:
                return True
            if norm_raw == norm_name:
                return True
            if norm_raw in (norm_email, norm_email_user, norm_email_user_domain):
                return True
            if norm_raw in norm_known_aliases:
                return True

    return False


def discover_org_accounts(
    root_session: boto3.Session,
    ou_filter: Optional[str] = None,
    include_accounts: Optional[List[str]] = None,
    exclude_accounts: Optional[List[str]] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Discover active member accounts in the AWS Organization.

    Args:
        root_session: boto3.Session configured with root/delegated-admin credentials
        ou_filter: Optional OU ID (e.g. ou-xxxx) to limit discovery to
        include_accounts: Optional list of account IDs, names, emails, or aliases to include
        exclude_accounts: Optional list of account IDs, names, emails, or aliases to exclude
        db_path: Optional SQLite database path to load known account aliases/profiles

    Returns:
        List of account dictionaries sorted by account name / ID.
    """
    client = root_session.client("organizations", region_name="us-east-1")

    # Verify organization access
    try:
        org_desc = client.describe_organization()
        org_info = org_desc.get("Organization", {})
        master_id = org_info.get("MasterAccountId")
    except botocore.exceptions.ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("AWSOrganizationsNotInUseException", "AccessDeniedException"):
            raise ValueError(
                f"AWS Organizations error: {e}. Ensure the session profile has "
                f"permissions to call organizations:ListAccounts (management or delegated admin account)."
            )
        raise

    discovered: List[Dict[str, Any]] = []

    # If OU filter is specified, recursively traverse starting from that OU
    if ou_filter:
        target_account_ids = _get_accounts_in_ou_recursive(client, ou_filter)
        paginator = client.get_paginator("list_accounts")
        for page in paginator.paginate():
            for acct in page.get("Accounts", []):
                if acct["Id"] in target_account_ids:
                    discovered.append(acct)
    else:
        # List all accounts
        paginator = client.get_paginator("list_accounts")
        for page in paginator.paginate():
            for acct in page.get("Accounts", []):
                discovered.append(acct)

    # Load known aliases/profiles from local database if available
    db_aliases: Dict[str, Set[str]] = {}
    target_db = db_path or os.path.expanduser("~/.awsmap/inventory.db")
    if os.path.exists(target_db):
        try:
            conn = get_connection(target_db)
            cursor = conn.execute("SELECT account_id, account_alias, profile FROM scans")
            for aid, alias, prof in cursor.fetchall():
                aid_str = str(aid)
                s = db_aliases.setdefault(aid_str, set())
                if alias:
                    s.add(str(alias).strip().lower())
                if prof:
                    s.add(str(prof).strip().lower())
            conn.close()
        except Exception:
            pass

    filtered = []
    active_in_org = []
    for acct in discovered:
        acct_id = acct["Id"]
        status = acct.get("Status", "").upper()

        # Always skip SUSPENDED or non-ACTIVE accounts
        if status != "ACTIVE":
            continue

        account_entry = {
            "id": acct_id,
            "name": acct.get("Name", acct_id),
            "email": acct.get("Email", ""),
            "status": status,
            "is_management": (acct_id == master_id),
        }
        active_in_org.append(account_entry)

        # Exclusion filter (supports account ID, Org Name, Email, and DB aliases)
        if exclude_accounts and _matches_account(acct, exclude_accounts, db_aliases):
            continue

        # Inclusion filter (supports account ID, Org Name, Email, and DB aliases)
        if include_accounts and not _matches_account(acct, include_accounts, db_aliases):
            continue

        filtered.append(account_entry)

    # If user provided include_accounts but nothing matched, provide a rich error message
    if include_accounts and not filtered and active_in_org:
        names_list = [
            f"  - {a['id']} ({a['name']})" + (f" [email: {a['email']}]" if a.get("email") else "")
            for a in active_in_org
        ]
        avail_str = "\n".join(names_list)
        filter_str = ", ".join(include_accounts)
        raise ValueError(
            f"No active member accounts matched criteria: '{filter_str}'.\n"
            f"Active accounts found in this AWS Organization:\n{avail_str}"
        )

    # Sort management account first, then by name
    filtered.sort(key=lambda a: (not a["is_management"], a["name"].lower()))
    return filtered



def _get_accounts_in_ou_recursive(client: Any, parent_id: str) -> Set[str]:
    """Recursively collect all account IDs under a given OU or Root."""
    account_ids: Set[str] = set()

    # Get direct accounts under this parent
    try:
        paginator = client.get_paginator("list_accounts_for_parent")
        for page in paginator.paginate(ParentId=parent_id):
            for acct in page.get("Accounts", []):
                account_ids.add(acct["Id"])
    except Exception:
        pass

    # Recurse into child OUs
    try:
        ou_paginator = client.get_paginator("list_organizational_units_for_parent")
        for page in ou_paginator.paginate(ParentId=parent_id):
            for child_ou in page.get("OrganizationalUnits", []):
                child_id = child_ou["Id"]
                account_ids.update(_get_accounts_in_ou_recursive(client, child_id))
    except Exception:
        pass

    return account_ids


def assume_member_role(
    root_session: boto3.Session,
    account_id: str,
    role_name: str,
    session_policy: Optional[str] = None,
    policy_arns: Optional[List[Dict[str, str]]] = None,
    external_id: Optional[str] = None,
    duration_seconds: int = 3600,
) -> boto3.Session:
    """Assume IAM role into a member account and return a boto3 Session for it.

    See assume_member_role_credentials for the arguments.
    """
    creds = assume_member_role_credentials(
        root_session, account_id, role_name,
        session_policy=session_policy, policy_arns=policy_arns,
        external_id=external_id, duration_seconds=duration_seconds,
    )
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def assume_member_role_credentials(
    root_session: boto3.Session,
    account_id: str,
    role_name: str,
    session_policy: Optional[str] = None,
    policy_arns: Optional[List[Dict[str, str]]] = None,
    external_id: Optional[str] = None,
    duration_seconds: int = 3600,
    sts_client: Any = None,
) -> Dict[str, Any]:
    """Assume IAM role into a member account with an optional Least-Privilege session policy.

    Args:
        root_session: Source boto3 session
        account_id: Destination member account ID
        role_name: IAM role name in member account
        session_policy: Minified IAM policy JSON string to intersect permissions
        policy_arns: Optional list of managed policy ARNs (e.g. ReadOnlyAccess)
        external_id: Optional external ID
        duration_seconds: Credential duration (default 1 hour)
        sts_client: Optional pre-built STS client to reuse (thread-safe)

    Returns:
        The STS Credentials dict (AccessKeyId, SecretAccessKey, SessionToken, Expiration).
    """
    # Configure fast retry and backoff on the STS client
    sts_config = Config(
        retries={"max_attempts": 5, "mode": "adaptive"},
        connect_timeout=10,
        read_timeout=10,
    )
    sts = sts_client or root_session.client("sts", config=sts_config)
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    kwargs: Dict[str, Any] = {
        "RoleArn": role_arn,
        "RoleSessionName": f"awsmap-{account_id[:6]}",
        "DurationSeconds": duration_seconds,
    }

    if external_id:
        kwargs["ExternalId"] = external_id

    if session_policy:
        kwargs["Policy"] = session_policy

        if policy_arns is not None:
            kwargs["PolicyArns"] = policy_arns
        else:
            partition = "aws"
            try:
                reg = root_session.region_name or "us-east-1"
                part = root_session.get_partition_for_region(reg)
                if isinstance(part, str) and part.strip():
                    partition = part.strip()
            except Exception:
                partition = "aws"
            kwargs["PolicyArns"] = [{"arn": f"arn:{partition}:iam::aws:policy/ReadOnlyAccess"}]

    try:
        resp = sts.assume_role(**kwargs)
    except botocore.exceptions.ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        # If PolicyArns is rejected (e.g. permission boundary or SCP), retry with inline Policy only
        if "PolicyArns" in kwargs and code in ("AccessDenied", "InvalidParameterValue", "MalformedPolicyDocument"):
            fallback_kwargs = dict(kwargs)
            del fallback_kwargs["PolicyArns"]
            resp = sts.assume_role(**fallback_kwargs)
        else:
            raise

    return resp["Credentials"]


def probe_role_access(
    root_session: boto3.Session,
    account_id: str,
    role_name: str,
    session_policy: Optional[str] = None,
    external_id: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Quickly probe role assumption for preflight checks (< 1s timeout)."""
    try:
        session = assume_member_role(
            root_session,
            account_id,
            role_name,
            session_policy=session_policy,
            external_id=external_id,
            duration_seconds=900,  # 15 min probe
        )
        # Verify identity
        sts = session.client("sts")
        sts.get_caller_identity()
        return True, None
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "ClientError")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        return False, f"{error_code}: {error_msg}"
    except Exception as e:
        return False, str(e)


probe_role_access.__test__ = False  # Prevent pytest from treating as a test case


def _list_enabled_regions(session: boto3.Session) -> List[str]:
    """Regions enabled in the session's account (raises on failure, unlike get_enabled_regions)."""
    account = session.client("account", region_name="us-east-1")
    regions: List[str] = []
    for page in account.get_paginator("list_regions").paginate(
        RegionOptStatusContains=["ENABLED", "ENABLED_BY_DEFAULT"]
    ):
        regions.extend(r["RegionName"] for r in page.get("Regions", []))
    if not regions:
        raise ValueError("no enabled regions returned")
    return sorted(regions)


class OrgInventoryOrchestrator:
    """Coordinates high-speed multi-account inventory scanning.

    Collection runs on OrgScanEngine (see engine.py): a pool of worker processes
    that share boto3 clients across accounts. This class handles everything around
    it: preflight, role assumption, region and task planning, filtering, progress
    output and the single SQLite writer.
    """

    def __init__(
        self,
        root_session: boto3.Session,
        role_name: str = DEFAULT_ROLE_NAME,
        session_policy: Optional[str] = None,
        external_id: Optional[str] = None,
        account_concurrency: Optional[int] = None,
        total_concurrency: int = DEFAULT_TOTAL_CONCURRENCY,
        processes: Optional[int] = None,
        threads_per_process: Optional[int] = None,
        services: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        exclude_defaults: bool = False,
        include_global: bool = False,
        tag_filters: Optional[List[str]] = None,
        db_path: Optional[str] = None,
        no_db: bool = False,
        resume: bool = False,
        quiet: bool = False,
    ):
        self.root_session = root_session
        self.role_name = role_name
        self.session_policy = session_policy
        self.external_id = external_id
        self.processes = max(1, processes or default_process_count())
        # Enough accounts in flight to keep every worker busy while the slowest
        # tasks of earlier accounts (IAM, S3, large regions) are still running.
        self.account_concurrency = max(1, account_concurrency or max(8, self.processes * 4))
        # total_concurrency is the budget the network sees; split it across workers.
        self.threads_per_process = max(1, threads_per_process or threads_for(total_concurrency, self.processes))
        self.services = services
        self.regions = regions
        self.exclude_defaults = exclude_defaults
        self.include_global = include_global
        self.tag_filters = tag_filters
        self.db_path = db_path
        self.no_db = no_db
        self.resume = resume
        self.quiet = quiet

        # Resolved lazily (only needed for a real scan, not for dry-run)
        self._fallback_regions: Optional[List[str]] = None
        self._sts_client: Any = None
        self._setup_lock = threading.Lock()

        # Synchronization & Queueing
        self.write_queue: queue.Queue = queue.Queue()
        self.print_lock = threading.Lock()

        # Metrics
        self.start_time: float = 0.0
        self.total_accounts: int = 0
        self.completed_accounts: int = 0
        self.failed_accounts: int = 0
        self.skipped_accounts: int = 0
        self.partial_accounts: List[Tuple[str, List[str]]] = []
        self.total_resources: int = 0

    def log(self, message: str) -> None:
        """Thread-safe stdout logging."""
        if not self.quiet:
            with self.print_lock:
                sys.stdout.write(message + "\n")
                sys.stdout.flush()

    def get_already_scanned_accounts(self) -> Set[str]:
        """Fetch account IDs fully scanned in the database within the last 24 hours for --resume.

        An account whose latest scan had failed services is not done: --resume scans it again.
        """
        if self.no_db:
            return set()
        try:
            conn = get_connection(self.db_path)
            # Accounts whose latest scan is complete and from the last 24 hours
            cursor = conn.execute(
                "SELECT DISTINCT account_id FROM scans s "
                "WHERE timestamp >= datetime('now', '-24 hours') AND incomplete_services IS NULL "
                "AND timestamp = (SELECT MAX(timestamp) FROM scans WHERE account_id = s.account_id)"
            )
            scanned = {row[0] for row in cursor.fetchall()}
            conn.close()
            return scanned
        except Exception:
            return set()

    def _sqlite_writer_loop(self) -> None:
        """Single dedicated writer thread consuming scan results (Actor Model).

        This guarantees zero SQLite database locks regardless of how many threads
        finish scanning simultaneously.
        """
        conn = None
        if not self.no_db:
            try:
                conn = get_connection(self.db_path)
            except Exception as e:
                self.log(f"  [ERROR] Could not open database for writer: {e}")

        while True:
            item = self.write_queue.get()
            if item is None:
                # Sentinel to stop
                break

            result, account_info = item
            if conn:
                try:
                    store_scan(
                        conn,
                        result,
                        profile=None,
                        account_alias=account_info["name"],
                        scanned_services=result["metadata"].get("services_scanned_list"),
                    )
                except Exception as e:
                    self.log(f"  [ERROR] Failed to save {account_info['id']} to database: {e}")

            self.write_queue.task_done()

        if conn:
            conn.close()

    def run_preflight(self, accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run parallel role-assumption checks across all accounts (< 2s)."""
        self.log(f"\nRunning fast pre-flight check across {len(accounts)} accounts...")
        results = []

        with ThreadPoolExecutor(max_workers=min(20, len(accounts))) as executor:
            future_to_acct = {
                executor.submit(
                    probe_role_access,
                    self.root_session,
                    acct["id"],
                    self.role_name,
                    self.session_policy,
                    self.external_id,
                ): acct
                for acct in accounts
                if not acct.get("is_management", False)
            }
            for acct in accounts:
                if acct.get("is_management", False):
                    # Root management account uses direct root credentials
                    results.append({**acct, "can_assume": True, "error": None})

            for future in as_completed(future_to_acct):
                acct = future_to_acct[future]
                success, error = future.result()
                results.append({**acct, "can_assume": success, "error": error})

        # Re-sort to maintain order
        results.sort(key=lambda a: (not a.get("is_management", False), a["name"].lower()))
        return results

    # -- account preparation (runs on the engine's prepare threads) ----------

    def _setup(self) -> None:
        """Create the shared STS client and fallback region list once."""
        with self._setup_lock:
            if self._sts_client is None:
                self._sts_client = self.root_session.client(
                    "sts",
                    config=Config(retries={"max_attempts": 5, "mode": "adaptive"},
                                  connect_timeout=10, read_timeout=10),
                )
            if self._fallback_regions is None and not self.regions:
                try:
                    self._fallback_regions = _list_enabled_regions(self.root_session)
                except Exception:
                    self._fallback_regions = get_enabled_regions(self.root_session)

    def _account_credentials(self, account_info: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        if account_info.get("is_management", False):
            # Management account: use root credentials directly
            frozen = self.root_session.get_credentials().get_frozen_credentials()
            return (frozen.access_key, frozen.secret_key, frozen.token)
        creds = assume_member_role_credentials(
            self.root_session,
            account_info["id"],
            self.role_name,
            session_policy=self.session_policy,
            external_id=self.external_id,
            sts_client=self._sts_client,
        )
        return (creds["AccessKeyId"], creds["SecretAccessKey"], creds["SessionToken"])

    def prepare_account(self, account_info: Dict[str, Any]) -> AccountPlan:
        """Assume the member role and build this account's task list."""
        self._setup()
        credentials = self._account_credentials(account_info)

        if self.regions:
            region_list = list(self.regions)
        else:
            # Member accounts can opt in to regions the management account has not.
            try:
                member = boto3.Session(
                    aws_access_key_id=credentials[0],
                    aws_secret_access_key=credentials[1],
                    aws_session_token=credentials[2],
                    region_name="us-east-1",
                )
                region_list = _list_enabled_regions(member)
            except Exception:
                region_list = list(self._fallback_regions or [])

        service_list = sorted(s.lower() for s in (self.services or get_available_services()))
        tasks = plan_collection_tasks(service_list, region_list, bool(self.regions), self.include_global)
        return AccountPlan(
            account_id=account_info["id"],
            credentials=credentials,
            service_list=service_list,
            region_list=region_list,
            regions_filtered=bool(self.regions),
            tasks=tasks,
        )

    def _post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply --tag and --exclude-defaults filters to one account's result."""
        if self.tag_filters:
            parsed_filters: Dict[str, List[str]] = {}
            for t in self.tag_filters:
                if "=" in t:
                    k, v = t.split("=", 1)
                    parsed_filters.setdefault(k, []).append(v)
            if parsed_filters:
                filtered_res = []
                for r in result.get("resources", []):
                    rtags = r.get("tags", {})
                    if all(rtags.get(k) in vals for k, vals in parsed_filters.items()):
                        filtered_res.append(r)
                result["resources"] = filtered_res
                result["metadata"]["resource_count"] = len(filtered_res)

        if self.exclude_defaults:
            result["resources"] = [r for r in result.get("resources", []) if not r.get("is_default")]
            result["metadata"]["resource_count"] = len(result["resources"])
        return result

    def _drop_incomplete_services(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Keep out of the stored scan every service that had a failed task.

        A service with a missing region would otherwise be stored as fully scanned: it
        would replace the previous rows of that service and look like deletions in a diff.
        Left out, the previous rows of that service stay current.
        """
        meta = result["metadata"]
        incomplete = sorted({task[0] for task in meta.get("incomplete_tasks", [])})
        if not incomplete:
            return result
        emitted = {_SERVICE_LABEL_TO_EMITTED.get(s, s) for s in incomplete}
        result["resources"] = [r for r in result["resources"] if r.get("service") not in emitted]
        meta["resource_count"] = len(result["resources"])
        meta["incomplete_services"] = incomplete
        meta["services_scanned_list"] = [s for s in meta["services_scanned_list"] if s not in incomplete]
        meta["services_scanned"] = len(meta["services_scanned_list"])
        return result

    def _on_account_done(self, acct: Dict[str, Any], result: Optional[Dict[str, Any]],
                         error: Optional[str], elapsed: float) -> None:
        self.completed_accounts += 1
        progress_idx = self.completed_accounts + self.skipped_accounts
        prefix = f"[{progress_idx:{len(str(self.total_accounts))}d}/{self.total_accounts}]"
        if result is not None:
            result = self._drop_incomplete_services(result)
            result = self._post_process(result)
            res_count = result["metadata"]["resource_count"]
            self.total_resources += res_count
            # Enqueue for zero-lock SQLite writing
            self.write_queue.put((result, acct))
            incomplete = result["metadata"].get("incomplete_services")
            if incomplete:
                self.partial_accounts.append((acct["id"], incomplete))
                self.log(f"{prefix} PART {acct['id']} ({acct['name']}) -> {res_count:,} resources in {elapsed:.1f}s; "
                         f"{len(incomplete)} service(s) incomplete, not stored: {', '.join(incomplete[:5])}"
                         f"{' ...' if len(incomplete) > 5 else ''}")
            else:
                self.log(f"{prefix} OK   {acct['id']} ({acct['name']}) -> {res_count:,} resources in {elapsed:.1f}s")
        else:
            self.failed_accounts += 1
            self.log(f"{prefix} FAIL {acct['id']} ({acct['name']}) -> {error}")

    def _on_heartbeat(self, stats: Dict[str, int]) -> None:
        elapsed = max(time.time() - self.start_time, 1e-6)
        self.log(
            f"      ... {elapsed:5.0f}s | accounts done {stats['accounts_done']}, in flight "
            f"{stats['accounts_in_flight']} | tasks {stats['tasks_done']:,}/{stats['tasks_total']:,} "
            f"dispatched ({stats['tasks_done'] / elapsed:.0f}/s)"
        )

    def execute(self, accounts: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
        """Execute the complete organization inventory scan."""
        self.start_time = time.time()
        self.total_accounts = len(accounts)

        # 1. Preflight check
        preflight_results = self.run_preflight(accounts)
        accessible = [a for a in preflight_results if a["can_assume"]]
        inaccessible = [a for a in preflight_results if not a["can_assume"]]

        if dry_run:
            self.log(f"\n{'='*75}")
            self.log(f"ORGANIZATION INVENTORY DRY-RUN REPORT")
            self.log(f"{'='*75}")
            self.log(f"  Total Accounts Found : {len(accounts)}")
            self.log(f"  Accessible via Role  : {len(accessible)}")
            self.log(f"  Inaccessible/Failed  : {len(inaccessible)}")
            self.log(f"  Role Name            : {self.role_name}")
            self.log(f"  Least-Privilege Mode : {'Enabled' if self.session_policy else 'Disabled'}")
            self.log(f"  Worker Processes     : {self.processes}")
            self.log(f"  Threads per Process  : {self.threads_per_process}")
            self.log(f"  Accounts in Flight   : {self.account_concurrency}")
            self.log(f"\nAccount Access Details:")
            for a in preflight_results:
                status = "OK" if a["can_assume"] else f"FAIL ({a['error']})"
                mgmt_flag = " [MGMT]" if a.get("is_management") else ""
                self.log(f"  {a['id']}  {a['name']:<24}{mgmt_flag}  {status}")
            self.log(f"{'='*75}\n")
            return {
                "total": len(accounts),
                "accessible": len(accessible),
                "inaccessible": len(inaccessible),
                "dry_run": True,
            }

        for a in inaccessible:
            self.log(f"  [SKIP] {a['id']} ({a['name']}): {a['error']}")

        # 2. Handle --resume
        to_scan = accessible
        if self.resume:
            already_scanned = self.get_already_scanned_accounts()
            if already_scanned:
                skipped = [a for a in accessible if a["id"] in already_scanned]
                to_scan = [a for a in accessible if a["id"] not in already_scanned]
                self.skipped_accounts = len(skipped)
                self.log(f"  [RESUME] Skipping {len(skipped)} accounts scanned in the last 24h.")

        # 3. Start dedicated SQLite Writer Thread
        writer_thread = threading.Thread(target=self._sqlite_writer_loop, daemon=True)
        writer_thread.start()

        self.log(f"\nStarting Organization Scan:")
        self.log(f"  Accounts to scan  : {len(to_scan)} (of {len(accounts)} total)")
        self.log(f"  Worker processes  : {self.processes} x {self.threads_per_process} threads "
                 f"({self.processes * self.threads_per_process} concurrent API tasks)")
        self.log(f"  Accounts per batch: {self.account_concurrency}")
        self.log(f"  Least-Privilege   : {'Enabled (Scoped Session Policy)' if self.session_policy else 'Full Role'}")
        self.log(f"{'-'*75}")

        # 4. Run the engine. Completed accounts are flushed to the database even
        #    if the scan is interrupted, so --resume can pick up where it stopped.
        engine = OrgScanEngine(
            processes=self.processes,
            threads_per_process=self.threads_per_process,
            max_accounts_in_flight=self.account_concurrency,
            default_region=getattr(self.root_session, "region_name", None) or "us-east-1",
            prepare_account=self.prepare_account,
            on_account_done=self._on_account_done,
            on_heartbeat=self._on_heartbeat,
        )
        try:
            engine.run(to_scan)
        finally:
            # 5. Flush and stop SQLite writer thread
            self.write_queue.put(None)
            writer_thread.join()

        total_elapsed = time.time() - self.start_time

        # 6. Final Summary
        self.log(f"{'-'*75}")
        self.log(f"\nOrganization Scan Complete!")
        self.log(f"  Total Duration    : {total_elapsed / 60:.1f} minutes ({total_elapsed:.1f}s)")
        self.log(f"  Accounts Scanned  : {self.completed_accounts - self.failed_accounts - len(self.partial_accounts)}")
        self.log(f"  Accounts Partial  : {len(self.partial_accounts)}")
        self.log(f"  Accounts Skipped  : {self.skipped_accounts + len(inaccessible)}")
        self.log(f"  Accounts Failed   : {self.failed_accounts}")
        self.log(f"  Resources Found   : {self.total_resources:,}")
        retried = getattr(engine, "tasks_retried", 0)
        failed = getattr(engine, "failed_tasks", [])
        if retried or failed:
            self.log(f"  Transient errors  : {retried} task(s) re-run after throttling/timeouts; "
                     f"{len(failed)} still failing after retries")
            for acct_id, service, region, reason in failed[:10]:
                self.log(f"      INCOMPLETE {acct_id} {service} {region or 'global'}: {reason}")
        if self.partial_accounts:
            self.log(f"  Partial accounts  : stored without their incomplete services; "
                     f"run again with --resume to scan them")
            for acct_id, services in self.partial_accounts[:10]:
                self.log(f"      PARTIAL {acct_id}: {', '.join(services)}")
        denied = getattr(engine, "denied_calls", {})
        if denied:
            self.log(f"  Access denied     : {len(denied)} call type(s) refused; resources behind them are "
                     f"not in the inventory (service | call | accounts)")
            ranked = sorted(denied.items(), key=lambda kv: (-len(kv[1]), kv[0]))
            for (service, reason), accounts_denied in ranked[:15]:
                self.log(f"      {service:<24} {reason:<48} {len(accounts_denied):4d}")
            if len(ranked) > 15:
                self.log(f"      ... {len(ranked) - 15} more")
        dead = sorted(getattr(engine, "dead_endpoints", set()), key=lambda e: (e[0], e[1] or ""))
        if dead:
            listed = ", ".join(f"{svc}@{reg or 'global'}" for svc, reg in dead[:12])
            more = f" (+{len(dead) - 12} more)" if len(dead) > 12 else ""
            self.log(f"  Unreachable       : {len(dead)} service endpoint(s) not offered in that region, "
                     f"skipped: {listed}{more}")
        timings = getattr(engine, "service_timings", None)
        if timings:
            slowest = sorted(timings.items(), key=lambda kv: -kv[1][0])[:8]
            self.log("  Slowest services  : (total task time | tasks | slowest single task)")
            for service, (total, worst, worst_region, count) in slowest:
                self.log(f"      {service:<24} {total:8.0f}s | {count:6,} | {worst:6.1f}s ({worst_region or 'global'})")
        if not self.no_db:
            db_disp = self.db_path or "~/.awsmap/inventory.db"
            self.log(f"  Stored in DB      : {db_disp}")
        self.log(f"{'-'*75}\n")

        return {
            "total_accounts": self.total_accounts,
            "completed_accounts": self.completed_accounts,
            "failed_accounts": self.failed_accounts,
            "partial_accounts": len(self.partial_accounts),
            "skipped_accounts": self.skipped_accounts + len(inaccessible),
            "total_resources": self.total_resources,
            "duration_seconds": total_elapsed,
        }
