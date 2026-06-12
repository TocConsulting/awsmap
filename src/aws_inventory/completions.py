"""
Shell completion functions for awsmap CLI.

Each function takes (ctx, param, incomplete) and returns a list of
CompletionItem objects. All functions are wrapped in try/except so
completion never crashes the shell.
"""

import configparser
import os

from click.shell_completion import CompletionItem


# All AWS regions (hardcoded to avoid AWS API calls during completion)
_AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "af-south-1",
    "ap-east-1", "ap-south-1", "ap-south-2", "ap-southeast-1", "ap-southeast-2",
    "ap-southeast-3", "ap-southeast-4", "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "ca-central-1", "ca-west-1",
    "eu-central-1", "eu-central-2", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-south-1", "eu-south-2", "eu-north-1",
    "il-central-1",
    "me-south-1", "me-central-1",
    "sa-east-1",
]


def complete_services(ctx, param, incomplete):
    """Complete AWS service names from available collectors."""
    try:
        from aws_inventory.collector import get_available_services
        return [
            CompletionItem(s)
            for s in get_available_services()
            if s.startswith(incomplete)
        ]
    except Exception:
        return []


def complete_regions(ctx, param, incomplete):
    """Complete AWS region names."""
    return [
        CompletionItem(r)
        for r in _AWS_REGIONS
        if r.startswith(incomplete)
    ]


def complete_profiles(ctx, param, incomplete):
    """Complete AWS profile names from ~/.aws/credentials and ~/.aws/config."""
    try:
        profiles = set()
        for path in ["~/.aws/credentials", "~/.aws/config"]:
            full = os.path.expanduser(path)
            if os.path.exists(full):
                cp = configparser.ConfigParser()
                cp.read(full)
                for section in cp.sections():
                    # ~/.aws/config uses "profile X" sections
                    name = section.replace("profile ", "") if section.startswith("profile ") else section
                    if name != "DEFAULT":
                        profiles.add(name)
        return [
            CompletionItem(p)
            for p in sorted(profiles)
            if p.startswith(incomplete)
        ]
    except Exception:
        return []


def complete_query_names(ctx, param, incomplete):
    """Complete pre-built query names from .sql files."""
    try:
        from aws_inventory.queries_lib import list_named_queries
        return [
            CompletionItem(name, help=desc)
            for name, desc, _ in list_named_queries()
            if name.startswith(incomplete)
        ]
    except Exception:
        return []


def complete_accounts(ctx, param, incomplete):
    """Complete account identifiers from the database."""
    try:
        from aws_inventory.config import get_config
        from aws_inventory.db import get_accounts, get_connection
        db_path = get_config("db")
        conn = get_connection(db_path)
        accounts = get_accounts(conn)
        conn.close()
        items = []
        seen = set()
        for account_id, alias, profile in accounts:
            for val in [alias, profile, account_id]:
                if val and val not in seen and val.startswith(incomplete):
                    seen.add(val)
                    label = f"{alias or profile or account_id}"
                    items.append(CompletionItem(val, help=label))
        return items
    except Exception:
        return []


def complete_config_keys(ctx, param, incomplete):
    """Complete configuration key names."""
    try:
        from aws_inventory.config import _VALID_KEYS
        return [
            CompletionItem(k)
            for k in sorted(_VALID_KEYS)
            if k.startswith(incomplete)
        ]
    except Exception:
        return []


def complete_example_services(ctx, param, incomplete):
    """Complete service names from the examples library."""
    try:
        from aws_inventory.examples import list_services as examples_list_services
        return [
            CompletionItem(svc, help=label)
            for svc, label, _count in examples_list_services()
            if svc.startswith(incomplete)
        ]
    except Exception:
        return []


def complete_scan_selectors(ctx, param, incomplete):
    """Complete scan selectors (latest/previous/first and recent scan ids)."""
    try:
        items = [CompletionItem(s) for s in ("latest", "previous", "first")
                 if s.startswith(incomplete)]
        from aws_inventory.config import get_config
        from aws_inventory.db import get_connection, list_scans
        conn = get_connection(get_config("db"))
        for scan_id, timestamp, acct, alias, profile, count, _ in list_scans(conn)[:10]:
            if scan_id.startswith(incomplete):
                items.append(CompletionItem(scan_id, help=f"{timestamp} {alias or profile or acct}"))
        conn.close()
        return items
    except Exception:
        return []


def complete_waste_rules(ctx, param, incomplete):
    """Complete waste rule keys."""
    try:
        from aws_inventory.waste import RULES
        return [
            CompletionItem(r["key"], help=r["title"])
            for r in RULES
            if r["key"].startswith(incomplete)
        ]
    except Exception:
        return []


def complete_example_numbers(ctx, param, incomplete):
    """Complete question numbers with the question text as description."""
    try:
        from aws_inventory.examples import list_questions
        service = ctx.params.get("service")
        if not service:
            return []
        questions = list_questions(service)
        if not questions:
            return []
        return [
            CompletionItem(str(i), help=q)
            for i, q in enumerate(questions, 1)
            if str(i).startswith(incomplete)
        ]
    except Exception:
        return []


