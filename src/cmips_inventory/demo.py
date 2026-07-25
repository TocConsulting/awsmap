"""
Demo database generator for cmipsmap.

Creates a realistic synthetic AWS inventory database covering all 150+ services,
multiple accounts, and multiple scans with drift - so users can try cmipsmap query,
ask, examples, and diff features without needing an AWS account.
"""

import json
import os
import random
import uuid
import zlib
from datetime import datetime, timedelta, timezone

from cmips_inventory.db import get_connection, store_scan
from cmips_inventory.nlq import _CMIPSMAP_TYPES


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCOUNTS = [
    ("111122223333", "production", "prod"),
    ("444455556666", "staging", "staging"),
    ("777788889999", "development", "dev"),
]

REGIONS = [
    "us-east-1", "us-east-2", "us-west-2",
    "eu-west-1", "eu-central-1",
    "ap-southeast-1",
]

ENVIRONMENTS = ["production", "staging", "development", "sandbox"]
TEAMS = ["platform", "backend", "frontend", "data", "security", "devops", "ml"]
OWNERS = ["alice", "bob", "charlie", "diana", "eric", "fatima"]
PROJECTS = ["web-app", "api", "data-pipeline", "ml-training", "monitoring", "auth"]
COST_CENTERS = ["CC-100", "CC-200", "CC-300", "CC-400"]

# VPC CIDRs per account
VPC_CIDRS = {
    "111122223333": ["10.0.0.0/16", "10.1.0.0/16", "172.31.0.0/16"],
    "444455556666": ["10.10.0.0/16", "10.11.0.0/16", "172.31.0.0/16"],
    "777788889999": ["10.20.0.0/16", "172.31.0.0/16"],
}


# ---------------------------------------------------------------------------
# Value generators
# ---------------------------------------------------------------------------

def _hex(n):
    return ''.join(random.choices('0123456789abcdef', k=n))


def _uuid():
    """Deterministic UUID4-formatted string drawn from the seeded RNG.

    uuid.uuid4() pulls from os.urandom and ignores random.seed(), which would
    break --seed reproducibility, so we build the UUID from seeded bytes instead.
    """
    return str(uuid.UUID(bytes=bytes(random.getrandbits(8) for _ in range(16)), version=4))


def _name(prefix, seq):
    env = random.choice(["prod", "stg", "dev", "test"])
    return f"{prefix}-{env}-{seq:02d}"


def _private_ip():
    return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _public_ip():
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


# Stable "now" anchor for deterministic timestamps. generate_demo_db() sets this
# to today's UTC midnight so that same-seed runs on the same day produce a
# byte-identical database. (Timestamps still age by whole days, so demo data
# always looks recent.) When unset, falls back to the real current time.
_NOW_ANCHOR = None


def _now():
    """Current time, anchored to _NOW_ANCHOR when set (for reproducibility)."""
    return _NOW_ANCHOR if _NOW_ANCHOR is not None else datetime.now(timezone.utc)


def _past_dt(days_back=365):
    delta = timedelta(days=random.randint(1, days_back),
                      hours=random.randint(0, 23),
                      minutes=random.randint(0, 59))
    dt = _now() - delta
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _weighted(choices_weights):
    values, weights = zip(*choices_weights)
    return random.choices(values, weights=weights, k=1)[0]


def _tags(name_val=None, extra=None):
    """Generate realistic tags. ~15% of resources have no tags."""
    if random.random() < 0.15:
        return {}
    tags = {}
    if name_val:
        tags["Name"] = name_val
    tags["Environment"] = random.choice(ENVIRONMENTS)
    tags["Team"] = random.choice(TEAMS)
    if random.random() > 0.3:
        tags["Owner"] = random.choice(OWNERS)
    if random.random() > 0.5:
        tags["Project"] = random.choice(PROJECTS)
    if random.random() > 0.6:
        tags["CostCenter"] = random.choice(COST_CENTERS)
    if extra:
        tags.update(extra)
    return tags


def _arn(service, region, account_id, rtype, rid):
    if region:
        return f"arn:aws:{service}:{region}:{account_id}:{rtype}/{rid}"
    return f"arn:aws:{service}::{account_id}:{rtype}/{rid}"


# ---------------------------------------------------------------------------
# Cross-reference pool - tracks generated IDs for inter-resource references
# ---------------------------------------------------------------------------

class RefPool:
    """Tracks generated resource IDs for cross-references between resources."""

    def __init__(self):
        self._pool = {}  # (account_id, service, type) -> [id, ...]
        self._vpcs = {}  # account_id -> [(vpc_id, cidr, region), ...]
        self._subnets = {}  # account_id -> [(subnet_id, vpc_id, region, az), ...]
        self._sgs = {}  # account_id -> [(sg_id, vpc_id, region), ...]

    def add(self, account_id, service, rtype, rid):
        key = (account_id, service, rtype)
        self._pool.setdefault(key, []).append(rid)

    def get(self, account_id, service, rtype):
        key = (account_id, service, rtype)
        items = self._pool.get(key, [])
        return random.choice(items) if items else None

    def get_all(self, account_id, service, rtype):
        return self._pool.get((account_id, service, rtype), [])


# ---------------------------------------------------------------------------
# Tier 1 - High-fidelity generators for critical services
# ---------------------------------------------------------------------------

def _gen_vpc(account_id, pool):
    """Generate VPC resources: VPCs, subnets, route tables, IGWs, NACLs, etc."""
    resources = []
    cidrs = VPC_CIDRS.get(account_id, ["10.0.0.0/16", "172.31.0.0/16"])

    for i, cidr in enumerate(cidrs):
        is_default = (cidr == "172.31.0.0/16")
        region = random.choice(REGIONS[:3]) if not is_default else "us-east-1"
        vpc_id = f"vpc-{_hex(17)}"
        pool.add(account_id, "vpc", "vpc", vpc_id)
        pool._vpcs.setdefault(account_id, []).append((vpc_id, cidr, region))

        name = "default" if is_default else _name("vpc", i)
        resources.append({
            "service": "vpc", "type": "vpc", "id": vpc_id,
            "arn": _arn("ec2", region, account_id, "vpc", vpc_id),
            "name": name, "region": region, "account_id": account_id,
            "is_default": is_default,
            "details": {
                "cidr_block": cidr, "state": "available",
                "is_default": is_default,
                "dhcp_options_id": f"dopt-{_hex(17)}",
                "instance_tenancy": "default",
            },
            "tags": _tags(name) if not is_default else {"Name": "default"},
        })

        # Subnets - 2-4 per VPC
        azs = [f"{region}a", f"{region}b", f"{region}c"]
        for j in range(random.randint(2, 4)):
            subnet_id = f"subnet-{_hex(17)}"
            az = azs[j % len(azs)]
            pool.add(account_id, "vpc", "subnet", subnet_id)
            pool._subnets.setdefault(account_id, []).append((subnet_id, vpc_id, region, az))
            octet = j + 1
            sub_cidr = cidr.replace(".0.0/16", f".{octet}.0/24")
            sub_name = f"{'default-' if is_default else ''}{az}"
            resources.append({
                "service": "vpc", "type": "subnet", "id": subnet_id,
                "arn": _arn("ec2", region, account_id, "subnet", subnet_id),
                "name": sub_name, "region": region, "account_id": account_id,
                "is_default": is_default,
                "details": {
                    "vpc_id": vpc_id, "cidr_block": sub_cidr,
                    "availability_zone": az, "state": "available",
                    "map_public_ip_on_launch": is_default,
                    "available_ips": random.randint(200, 250),
                },
                "tags": _tags(sub_name) if not is_default else {},
            })

        # Route table
        rtb_id = f"rtb-{_hex(17)}"
        resources.append({
            "service": "vpc", "type": "route-table", "id": rtb_id,
            "arn": _arn("ec2", region, account_id, "route-table", rtb_id),
            "name": f"{'default-' if is_default else ''}rtb-{name}",
            "region": region, "account_id": account_id, "is_default": is_default,
            "details": {"vpc_id": vpc_id, "routes": random.randint(2, 6)},
            "tags": {},
        })

        # Internet gateway
        igw_id = f"igw-{_hex(17)}"
        resources.append({
            "service": "vpc", "type": "internet-gateway", "id": igw_id,
            "arn": _arn("ec2", region, account_id, "internet-gateway", igw_id),
            "name": igw_id, "region": region, "account_id": account_id,
            "is_default": is_default,
            "details": {"vpc_id": vpc_id, "state": "attached"},
            "tags": {},
        })

        # Network ACL
        nacl_id = f"acl-{_hex(17)}"
        resources.append({
            "service": "vpc", "type": "network-acl", "id": nacl_id,
            "arn": _arn("ec2", region, account_id, "network-acl", nacl_id),
            "name": nacl_id, "region": region, "account_id": account_id,
            "is_default": is_default,
            "details": {"vpc_id": vpc_id, "is_default": is_default, "entries": random.randint(4, 10)},
            "tags": {},
        })

        # NAT gateway (non-default VPCs only)
        if not is_default and random.random() > 0.3:
            nat_id = f"nat-{_hex(17)}"
            resources.append({
                "service": "vpc", "type": "nat-gateway", "id": nat_id,
                "arn": _arn("ec2", region, account_id, "natgateway", nat_id),
                "name": f"nat-{name}", "region": region, "account_id": account_id,
                "details": {
                    "vpc_id": vpc_id, "state": "available",
                    "connectivity_type": "public",
                    "subnet_id": pool._subnets[account_id][-1][0],
                },
                "tags": _tags(f"nat-{name}"),
            })

        # DHCP options
        dhcp_id = f"dopt-{_hex(17)}"
        resources.append({
            "service": "vpc", "type": "dhcp-options", "id": dhcp_id,
            "arn": _arn("ec2", region, account_id, "dhcp-options", dhcp_id),
            "name": dhcp_id, "region": region, "account_id": account_id,
            "is_default": is_default,
            "details": {"domain_name": f"{region}.compute.internal"},
            "tags": {},
        })

    # VPC endpoints - a few per account
    for _ in range(random.randint(2, 5)):
        vpce_id = f"vpce-{_hex(17)}"
        vpc_info = random.choice(pool._vpcs[account_id])
        svc = random.choice(["s3", "dynamodb", "secretsmanager", "logs", "ecr.api"])
        resources.append({
            "service": "vpc", "type": "vpc-endpoint", "id": vpce_id,
            "arn": _arn("ec2", vpc_info[2], account_id, "vpc-endpoint", vpce_id),
            "name": f"vpce-{svc}", "region": vpc_info[2], "account_id": account_id,
            "details": {
                "vpc_id": vpc_info[0], "service_name": f"com.amazonaws.{vpc_info[2]}.{svc}",
                "state": "available", "type": random.choice(["Interface", "Gateway"]),
            },
            "tags": _tags(f"vpce-{svc}"),
        })

    return resources


def _gen_ec2(account_id, pool, count_range=(15, 35)):
    """Generate EC2 resources: instances, volumes, snapshots, AMIs, SGs, etc."""
    resources = []
    vpcs = pool._vpcs.get(account_id, [])
    subnets = pool._subnets.get(account_id, [])

    if not vpcs:
        return resources

    # Security groups - including some open ones for the query
    sg_count = random.randint(10, 20)
    for i in range(sg_count):
        sg_id = f"sg-{_hex(17)}"
        vpc_info = random.choice(vpcs)
        region = vpc_info[2]
        pool.add(account_id, "ec2", "security-group", sg_id)
        pool._sgs.setdefault(account_id, []).append((sg_id, vpc_info[0], region))
        is_default = (i == 0 and vpc_info[1] == "172.31.0.0/16")
        sg_name = "default" if is_default else _name("sg", i)

        # Build inbound_rules string - some open to 0.0.0.0/0 for the query
        if random.random() < 0.2:
            inbound_str = f"tcp/22 from 0.0.0.0/0, tcp/443 from 0.0.0.0/0"
        elif random.random() < 0.3:
            inbound_str = f"tcp/443 from 0.0.0.0/0"
        else:
            inbound_str = f"tcp/443 from 10.0.0.0/8, tcp/22 from 10.0.0.0/8"

        resources.append({
            "service": "ec2", "type": "security-group", "id": sg_id,
            "arn": _arn("ec2", region, account_id, "security-group", sg_id),
            "name": sg_name, "region": region, "account_id": account_id,
            "is_default": is_default,
            "details": {
                "vpc_id": vpc_info[0], "description": f"Security group {sg_name}",
                "ingress_rules": random.randint(1, 8),
                "egress_rules": random.randint(1, 3),
                # The open-security-groups query uses $.inbound_rules with LIKE '%0.0.0.0/0%'
                "inbound_rules": inbound_str,
            },
            "tags": _tags(sg_name) if not is_default else {},
        })

    # EC2 instances
    instance_types = ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge",
                      "c5.large", "c5.xlarge", "r5.large", "r5.xlarge", "m6i.large"]
    n_instances = random.randint(*count_range)
    prefixes = ["web", "api", "worker", "batch", "bastion", "app", "proxy", "cache"]
    for i in range(n_instances):
        iid = f"i-{_hex(17)}"
        subnet_info = random.choice(subnets)
        region = subnet_info[2]
        state = _weighted([("running", 0.65), ("stopped", 0.25), ("terminated", 0.10)])
        name = _name(random.choice(prefixes), i)
        has_public = random.random() > 0.5
        pool.add(account_id, "ec2", "instance", iid)
        resources.append({
            "service": "ec2", "type": "instance", "id": iid,
            "arn": _arn("ec2", region, account_id, "instance", iid),
            "name": name, "region": region, "account_id": account_id,
            "details": {
                "instance_type": random.choice(instance_types),
                "state": state,
                "private_ip": _private_ip(),
                "public_ip": _public_ip() if has_public else None,
                "vpc_id": subnet_info[1],
                "subnet_id": subnet_info[0],
                "launch_time": _past_dt(400),
                "platform": _weighted([("linux", 0.85), ("windows", 0.15)]),
                "architecture": _weighted([("x86_64", 0.7), ("arm64", 0.3)]),
            },
            "tags": _tags(name),
        })

    # EBS volumes - some attached, some available (for unused-volumes query)
    instances = pool.get_all(account_id, "ec2", "instance")
    vol_types = ["gp3", "gp2", "io1", "io2", "st1", "sc1"]
    n_volumes = random.randint(25, 50)
    for i in range(n_volumes):
        vol_id = f"vol-{_hex(17)}"
        region = random.choice(subnets)[2]
        # ~80% attached, ~20% available (waste)
        if random.random() < 0.8 and instances:
            state = "in-use"
            attachments = [random.choice(instances)]
        else:
            state = "available"
            attachments = []
        encrypted = random.random() > 0.2  # ~20% unencrypted for ebs-unencrypted query
        resources.append({
            "service": "ec2", "type": "volume", "id": vol_id,
            "arn": _arn("ec2", region, account_id, "volume", vol_id),
            "name": f"vol-{i:03d}", "region": region, "account_id": account_id,
            "details": {
                "size_gb": random.choice([8, 20, 50, 100, 200, 500]),
                "volume_type": random.choice(vol_types),
                "state": state,
                "iops": random.choice([3000, 4000, 6000, 10000, 16000]),
                "encrypted": encrypted,
                "availability_zone": f"{region}{random.choice('abc')}",
                "attachments": attachments,
            },
            "tags": _tags(f"vol-{i:03d}"),
        })

    # EBS snapshots
    for i in range(random.randint(8, 20)):
        snap_id = f"snap-{_hex(17)}"
        region = random.choice(REGIONS[:3])
        resources.append({
            "service": "ec2", "type": "snapshot", "id": snap_id,
            "arn": _arn("ec2", region, account_id, "snapshot", snap_id),
            "name": f"snap-{i:03d}", "region": region, "account_id": account_id,
            "details": {
                "volume_id": f"vol-{_hex(17)}",
                "size_gb": random.choice([8, 20, 50, 100]),
                "state": "completed",
                "encrypted": random.random() > 0.3,
                "start_time": _past_dt(180),
                "description": f"Snapshot {i}",
            },
            "tags": _tags(f"snap-{i:03d}"),
        })

    # AMIs
    for i in range(random.randint(3, 8)):
        ami_id = f"ami-{_hex(17)}"
        region = random.choice(REGIONS[:3])
        resources.append({
            "service": "ec2", "type": "ami", "id": ami_id,
            "arn": _arn("ec2", region, account_id, "image", ami_id),
            "name": f"app-image-{i:02d}", "region": region, "account_id": account_id,
            "details": {
                "state": "available",
                "architecture": random.choice(["x86_64", "arm64"]),
                "platform": _weighted([("linux", 0.85), ("windows", 0.15)]),
                "virtualization_type": "hvm",
                "root_device_type": "ebs",
                "public": False,
                "creation_date": _past_dt(300),
            },
            "tags": _tags(f"app-image-{i:02d}"),
        })

    # Key pairs
    for i in range(random.randint(3, 6)):
        kp_id = f"key-{_hex(17)}"
        region = random.choice(REGIONS[:3])
        kp_name = f"deploy-key-{random.choice(['prod','staging','dev','shared'])}-{i}"
        resources.append({
            "service": "ec2", "type": "key-pair", "id": kp_id,
            "arn": _arn("ec2", region, account_id, "key-pair", kp_id),
            "name": kp_name, "region": region, "account_id": account_id,
            "details": {
                "key_type": random.choice(["rsa", "ed25519"]),
                "fingerprint": ':'.join(_hex(2) for _ in range(16)),
                "create_time": _past_dt(500),
            },
            "tags": _tags(kp_name),
        })

    # Elastic IPs - some unassociated for unused-eips query
    for i in range(random.randint(4, 8)):
        eip_id = f"eipalloc-{_hex(17)}"
        region = random.choice(REGIONS[:3])
        ip = _public_ip()
        associated = random.random() > 0.35  # ~35% unused
        resources.append({
            "service": "ec2", "type": "elastic-ip", "id": eip_id,
            "arn": _arn("ec2", region, account_id, "elastic-ip", eip_id),
            "name": ip, "region": region, "account_id": account_id,
            "details": {
                "public_ip": ip,
                "private_ip": _private_ip() if associated else None,
                "instance_id": random.choice(instances) if associated and instances else None,
                "network_interface_id": f"eni-{_hex(17)}" if associated else None,
                "domain": "vpc",
            },
            "tags": _tags(ip),
        })

    # Network interfaces
    for i in range(random.randint(5, 12)):
        eni_id = f"eni-{_hex(17)}"
        subnet_info = random.choice(subnets)
        resources.append({
            "service": "ec2", "type": "network-interface", "id": eni_id,
            "arn": _arn("ec2", subnet_info[2], account_id, "network-interface", eni_id),
            "name": eni_id, "region": subnet_info[2], "account_id": account_id,
            "details": {
                "vpc_id": subnet_info[1], "subnet_id": subnet_info[0],
                "private_ip": _private_ip(),
                "status": random.choice(["in-use", "available"]),
                "interface_type": random.choice(["interface", "nat_gateway", "efa"]),
                "attachment_instance": random.choice(instances) if instances and random.random() > 0.3 else None,
            },
            "tags": {},
        })

    return resources


def _gen_s3(account_id, pool):
    """Generate S3 buckets with details matching pre-built queries."""
    resources = []
    prefixes = ["data", "logs", "assets", "backups", "config", "reports",
                "artifacts", "media", "static", "landing"]
    n = random.randint(12, 22)
    for i in range(n):
        bucket_name = f"{random.choice(prefixes)}-{account_id[:4]}-{_hex(6)}"
        region = random.choice(REGIONS)
        is_public = random.random() < 0.1  # ~10% public for query
        versioning_on = random.random() > 0.4
        logging_on = random.random() > 0.4
        encrypted = random.random() > 0.15

        resources.append({
            "service": "s3", "type": "bucket", "id": bucket_name,
            "arn": f"arn:aws:s3:::{bucket_name}",
            "name": bucket_name, "region": region, "account_id": account_id,
            "details": {
                "creation_date": _past_dt(700),
                "versioning": "Enabled" if versioning_on else "Suspended",
                "encryption": "AES256" if encrypted else None,
                # Match what public-s3-buckets.sql expects
                "public_access": 1 if is_public else 0,
                # Also store what the collector produces
                "public_access_blocked": not is_public,
                # Match what s3-no-logging.sql expects
                "logging": 1 if logging_on else 0,
            },
            "tags": _tags(bucket_name),
        })
    return resources


def _gen_iam(account_id, pool):
    """Generate IAM resources - users, roles, policies, groups."""
    resources = []

    # IAM groups
    group_names = ["admins", "developers", "readonly", "devops", "data-team", "security"]
    for gname in group_names:
        pool.add(account_id, "iam", "group", gname)
        if gname == "admins":
            policies = ["arn:aws:iam::aws:policy/AdministratorAccess"]
        elif gname == "readonly":
            policies = ["arn:aws:iam::aws:policy/ReadOnlyAccess"]
        else:
            policies = [f"arn:aws:iam::{account_id}:policy/{gname}-policy"]
        resources.append({
            "service": "iam", "type": "group", "id": gname,
            "arn": f"arn:aws:iam::{account_id}:group/{gname}",
            "name": gname, "region": None, "account_id": account_id,
            "details": {
                "path": "/", "create_date": _past_dt(800),
                "attached_policies": policies, "user_count": 0,
            },
            "tags": {},
        })

    # IAM users
    user_names = ["alice", "bob", "charlie", "diana", "eric", "fatima",
                  "grace", "hassan", "iris", "jake", "ci-deploy", "terraform",
                  "monitoring-svc", "backup-agent", "old-intern"]
    for uname in user_names:
        pool.add(account_id, "iam", "user", uname)
        # Admin users for admin-users query
        is_admin = uname in ("alice", "bob")
        # MFA disabled for some - users-without-mfa query
        has_mfa = random.random() > 0.3 or uname in ("alice", "bob")
        if uname == "old-intern":
            has_mfa = False
        # Access keys for old-access-keys query
        has_keys = uname not in ("old-intern", "iris")
        key_count = random.randint(1, 2) if has_keys else 0
        # Inactive user for iam-inactive-users query
        is_inactive = uname == "old-intern"
        # Groups
        if is_admin:
            groups = ["admins"]
            attached = ["arn:aws:iam::aws:policy/AdministratorAccess"]
        elif uname.startswith("ci-") or uname == "terraform":
            groups = ["devops"]
            attached = [f"arn:aws:iam::{account_id}:policy/deploy-policy"]
        else:
            groups = [random.choice(["developers", "readonly", "data-team"])]
            attached = []

        resources.append({
            "service": "iam", "type": "user", "id": uname,
            "arn": f"arn:aws:iam::{account_id}:user/{uname}",
            "name": uname, "region": None, "account_id": account_id,
            "details": {
                "path": "/",
                "create_date": _past_dt(900),
                "password_last_used": _past_dt(60) if not is_inactive else None,
                "mfa_enabled": has_mfa,
                "access_keys_count": key_count,
                "attached_policies": attached,
                "groups": groups,
            },
            "tags": {},
        })

    # IAM roles
    role_templates = [
        ("admin-role", True, None),
        ("ec2-instance-role", False, None),
        ("lambda-execution-role", False, None),
        ("ecs-task-role", False, None),
        ("rds-monitoring-role", False, None),
        ("cloudformation-role", False, None),
        ("cross-account-audit", False, "999988887777"),
        ("cross-account-deploy", False, "888877776666"),
        ("github-actions-role", False, None),
        ("terraform-role", False, None),
    ]
    for rname, is_admin, external_account in role_templates:
        pool.add(account_id, "iam", "role", rname)
        if is_admin:
            attached = ["arn:aws:iam::aws:policy/AdministratorAccess"]
        else:
            attached = [f"arn:aws:iam::{account_id}:policy/{rname}-policy"]
        # Trust policy
        if external_account:
            trust = json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Principal": {
                    "AWS": f"arn:aws:iam::{external_account}:root"
                }, "Action": "sts:AssumeRole"}]
            })
        else:
            trust = json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Principal": {
                    "Service": f"{rname.split('-')[0]}.amazonaws.com"
                }, "Action": "sts:AssumeRole"}]
            })
        resources.append({
            "service": "iam", "type": "role", "id": rname,
            "arn": f"arn:aws:iam::{account_id}:role/{rname}",
            "name": rname, "region": None, "account_id": account_id,
            "details": {
                "path": "/",
                "create_date": _past_dt(700),
                "max_session_duration": 3600,
                "description": f"Role for {rname}",
                "attached_policies": attached,
                "trust_policy": trust,
            },
            "tags": _tags(rname),
        })

    # Extra roles
    for i in range(random.randint(15, 30)):
        rname = f"svc-role-{_hex(6)}"
        pool.add(account_id, "iam", "role", rname)
        resources.append({
            "service": "iam", "type": "role", "id": rname,
            "arn": f"arn:aws:iam::{account_id}:role/{rname}",
            "name": rname, "region": None, "account_id": account_id,
            "details": {
                "path": "/", "create_date": _past_dt(500),
                "max_session_duration": 3600, "description": "",
                "attached_policies": [f"arn:aws:iam::{account_id}:policy/{rname}-policy"],
                "trust_policy": json.dumps({"Version": "2012-10-17", "Statement": []}),
            },
            "tags": _tags(rname) if random.random() > 0.4 else {},
        })

    # IAM policies (customer-managed)
    for i in range(random.randint(8, 15)):
        pname = f"custom-policy-{_hex(4)}"
        resources.append({
            "service": "iam", "type": "policy", "id": pname,
            "arn": f"arn:aws:iam::{account_id}:policy/{pname}",
            "name": pname, "region": None, "account_id": account_id,
            "details": {
                "path": "/", "create_date": _past_dt(600),
                "update_date": _past_dt(60),
                "attachment_count": random.randint(0, 5),
                "default_version_id": "v1",
            },
            "tags": {},
        })

    # Instance profiles
    for i in range(random.randint(3, 6)):
        ip_name = f"ec2-profile-{i}"
        resources.append({
            "service": "iam", "type": "instance-profile", "id": ip_name,
            "arn": f"arn:aws:iam::{account_id}:instance-profile/{ip_name}",
            "name": ip_name, "region": None, "account_id": account_id,
            "details": {
                "path": "/", "create_date": _past_dt(600),
                "roles": [f"ec2-instance-role"],
            },
            "tags": {},
        })

    return resources


def _gen_lambda(account_id, pool):
    """Generate Lambda functions with realistic runtimes and memory."""
    resources = []
    runtimes = ["python3.12", "python3.11", "python3.9", "nodejs20.x", "nodejs18.x",
                "java21", "java17", "go1.x", "dotnet8", "ruby3.3"]
    prefixes = ["process", "transform", "notify", "validate", "sync", "export",
                "ingest", "cleanup", "auth", "webhook", "cron"]

    n = random.randint(15, 35)
    for i in range(n):
        fname = f"{random.choice(prefixes)}-{random.choice(PROJECTS)}-{_hex(4)}"
        region = random.choice(REGIONS[:4])
        runtime = random.choice(runtimes)
        mem = random.choice([128, 256, 512, 1024, 1536, 2048, 3008])
        pool.add(account_id, "lambda", "function", fname)
        resources.append({
            "service": "lambda", "type": "function", "id": fname,
            "arn": f"arn:aws:lambda:{region}:{account_id}:function:{fname}",
            "name": fname, "region": region, "account_id": account_id,
            "details": {
                "runtime": runtime,
                "handler": "index.handler",
                "code_size": random.randint(1000, 50000000),
                "memory_size": mem,
                "timeout": random.choice([3, 15, 30, 60, 300, 900]),
                "last_modified": _past_dt(90),
                "state": "Active",
                "package_type": "Zip",
                "architectures": [random.choice(["x86_64", "arm64"])],
                "ephemeral_storage": 512,
                "layers": random.randint(0, 3),
            },
            "tags": _tags(fname),
        })

    # Lambda layers
    for i in range(random.randint(2, 5)):
        lname = f"shared-layer-{i}"
        region = random.choice(REGIONS[:3])
        resources.append({
            "service": "lambda", "type": "layer", "id": lname,
            "arn": f"arn:aws:lambda:{region}:{account_id}:layer:{lname}",
            "name": lname, "region": region, "account_id": account_id,
            "details": {
                "latest_version": random.randint(1, 12),
                "compatible_runtimes": random.sample(runtimes[:5], 2),
            },
            "tags": {},
        })

    return resources


def _gen_rds(account_id, pool):
    """Generate RDS instances and clusters with details matching pre-built queries."""
    resources = []
    engines = [
        ("mysql", "8.0.35"), ("mysql", "8.0.33"),
        ("postgres", "16.1"), ("postgres", "15.4"), ("postgres", "14.10"),
        ("aurora-mysql", "3.06.0"), ("aurora-postgresql", "15.4"),
        ("mariadb", "10.11.6"), ("sqlserver-se", "16.00.4095.4"),
    ]
    instance_classes = ["db.t3.micro", "db.t3.medium", "db.m5.large",
                        "db.m5.xlarge", "db.r5.large", "db.r5.xlarge"]

    n = random.randint(5, 10)
    for i in range(n):
        engine, version = random.choice(engines)
        db_id = f"db-{random.choice(['app','api','analytics','reporting','cache'])}-{_hex(4)}"
        region = random.choice(REGIONS[:4])
        is_public = random.random() < 0.1  # ~10% public for rds-public query
        is_encrypted = random.random() > 0.15  # ~15% unencrypted for query
        is_multi_az = random.random() > 0.3  # ~30% single-AZ for query
        vpc = pool.get(account_id, "vpc", "vpc")

        resources.append({
            "service": "rds", "type": "db-instance", "id": db_id,
            "arn": f"arn:aws:rds:{region}:{account_id}:db:{db_id}",
            "name": db_id, "region": region, "account_id": account_id,
            "details": {
                "engine": engine, "engine_version": version,
                "instance_class": random.choice(instance_classes),
                "status": "available",
                "storage_type": random.choice(["gp3", "io1", "gp2"]),
                "allocated_storage": random.choice([20, 50, 100, 200, 500]),
                "multi_az": is_multi_az,
                "publicly_accessible": is_public,
                # Store both field names: what collector produces AND what query expects
                "encrypted": is_encrypted,
                "storage_encrypted": is_encrypted,
                "endpoint": f"{db_id}.{_hex(12)}.{region}.rds.amazonaws.com",
                "port": 3306 if "mysql" in engine or "maria" in engine else 5432,
                "vpc_id": vpc,
                "cluster_identifier": None,
            },
            "tags": _tags(db_id),
        })

    # DB clusters
    for i in range(random.randint(1, 3)):
        engine = random.choice([("aurora-mysql", "3.06.0"), ("aurora-postgresql", "15.4")])
        cluster_id = f"cluster-{_hex(6)}"
        region = random.choice(REGIONS[:3])
        resources.append({
            "service": "rds", "type": "db-cluster", "id": cluster_id,
            "arn": f"arn:aws:rds:{region}:{account_id}:cluster:{cluster_id}",
            "name": cluster_id, "region": region, "account_id": account_id,
            "details": {
                "engine": engine[0], "engine_version": engine[1],
                "engine_mode": "provisioned", "status": "available",
                "multi_az": True, "encrypted": True, "storage_encrypted": True,
                "endpoint": f"{cluster_id}.cluster-{_hex(12)}.{region}.rds.amazonaws.com",
                "reader_endpoint": f"{cluster_id}.cluster-ro-{_hex(12)}.{region}.rds.amazonaws.com",
                "port": 3306 if "mysql" in engine[0] else 5432,
                "members": random.randint(2, 4),
                "serverless_v2_scaling": None,
            },
            "tags": _tags(cluster_id),
        })

    # DB snapshots
    for i in range(random.randint(3, 8)):
        snap_id = f"rds-snap-{_hex(8)}"
        region = random.choice(REGIONS[:3])
        resources.append({
            "service": "rds", "type": "db-snapshot", "id": snap_id,
            "arn": f"arn:aws:rds:{region}:{account_id}:snapshot:{snap_id}",
            "name": snap_id, "region": region, "account_id": account_id,
            "details": {
                "db_instance_identifier": f"db-app-{_hex(4)}",
                "engine": "postgres", "engine_version": "15.4",
                "status": "available",
                "allocated_storage": random.choice([20, 50, 100]),
                "encrypted": random.random() > 0.3,
                "snapshot_create_time": _past_dt(90),
            },
            "tags": _tags(snap_id),
        })

    # DB subnet groups
    for i in range(random.randint(2, 4)):
        sg_name = f"db-subnet-{_hex(4)}"
        region = random.choice(REGIONS[:3])
        resources.append({
            "service": "rds", "type": "db-subnet-group", "id": sg_name,
            "arn": f"arn:aws:rds:{region}:{account_id}:subgrp:{sg_name}",
            "name": sg_name, "region": region, "account_id": account_id,
            "details": {
                "description": f"Subnet group {sg_name}",
                "vpc_id": pool.get(account_id, "vpc", "vpc"),
                "status": "Complete",
                "subnets": pool.get_all(account_id, "vpc", "subnet")[:3],
            },
            "tags": {},
        })

    return resources


def _gen_secretsmanager(account_id, pool):
    """Generate Secrets Manager secrets - some without rotation for the query."""
    resources = []
    names = ["db/production/master", "db/staging/master", "api/stripe-key",
             "api/sendgrid-key", "deploy/github-token", "app/jwt-secret",
             "monitoring/pagerduty", "ci/docker-hub"]
    for sname in names:
        region = random.choice(REGIONS[:3])
        rotation = random.random() > 0.4  # ~40% without rotation
        resources.append({
            "service": "secretsmanager", "type": "secret", "id": sname,
            "arn": f"arn:aws:secretsmanager:{region}:{account_id}:secret:{sname}-{_hex(6)}",
            "name": sname, "region": region, "account_id": account_id,
            "details": {
                "description": f"Secret {sname}",
                "kms_key_id": f"arn:aws:kms:{region}:{account_id}:key/{_uuid()}",
                "rotation_enabled": rotation,
                "rotation_lambda_arn": f"arn:aws:lambda:{region}:{account_id}:function:rotate-secret" if rotation else None,
                "last_rotated_date": _past_dt(30) if rotation else None,
                "last_accessed_date": _past_dt(7),
            },
            "tags": _tags(sname),
        })
    return resources


def _gen_kms(account_id, pool):
    """Generate KMS keys and aliases."""
    resources = []
    for i in range(random.randint(4, 8)):
        key_id = _uuid()
        region = random.choice(REGIONS[:3])
        resources.append({
            "service": "kms", "type": "key", "id": key_id,
            "arn": f"arn:aws:kms:{region}:{account_id}:key/{key_id}",
            "name": f"key-{i}", "region": region, "account_id": account_id,
            "details": {
                "key_state": "Enabled", "key_usage": "ENCRYPT_DECRYPT",
                "key_spec": "SYMMETRIC_DEFAULT", "origin": "AWS_KMS",
                "creation_date": _past_dt(500),
                "description": f"Customer managed key {i}",
                "enabled": True, "multi_region": False,
                "aliases": [f"alias/app-key-{i}"],
            },
            "tags": _tags(f"key-{i}"),
        })
    return resources


def _gen_elbv2(account_id, pool):
    """Generate load balancers and target groups."""
    resources = []
    vpcs = pool._vpcs.get(account_id, [])
    if not vpcs:
        return resources

    for i in range(random.randint(3, 7)):
        lb_name = f"{random.choice(['web','api','internal','grpc'])}-alb-{_hex(4)}"
        vpc_info = random.choice(vpcs)
        region = vpc_info[2]
        lb_arn = f"arn:aws:elasticloadbalancing:{region}:{account_id}:loadbalancer/app/{lb_name}/{_hex(16)}"
        lb_type = _weighted([("application-load-balancer", 0.6),
                             ("network-load-balancer", 0.3),
                             ("gateway-load-balancer", 0.1)])
        resources.append({
            "service": "elbv2", "type": lb_type, "id": lb_arn,
            "arn": lb_arn,
            "name": lb_name, "region": region, "account_id": account_id,
            "details": {
                "dns_name": f"{lb_name}-{_hex(10)}.{region}.elb.amazonaws.com",
                "scheme": random.choice(["internet-facing", "internal"]),
                "vpc_id": vpc_info[0],
                "state": "active",
                "type": lb_type.replace("-", " ").title(),
                "availability_zones": [f"{region}a", f"{region}b"],
            },
            "tags": _tags(lb_name),
        })

        # Target group per LB
        tg_name = f"tg-{lb_name}"
        tg_arn = f"arn:aws:elasticloadbalancing:{region}:{account_id}:targetgroup/{tg_name}/{_hex(16)}"
        resources.append({
            "service": "elbv2", "type": "target-group", "id": tg_arn,
            "arn": tg_arn,
            "name": tg_name, "region": region, "account_id": account_id,
            "details": {
                "protocol": random.choice(["HTTP", "HTTPS", "TCP"]),
                "port": random.choice([80, 443, 8080, 3000]),
                "vpc_id": vpc_info[0],
                "target_type": random.choice(["instance", "ip", "lambda"]),
                "health_check_path": "/health",
                "healthy_targets": random.randint(0, 5),
                "unhealthy_targets": random.randint(0, 2),
            },
            "tags": _tags(tg_name),
        })

    return resources


# ---------------------------------------------------------------------------
# Tier 2 - Structured templates for services with examples but no queries
# ---------------------------------------------------------------------------

# Map of (service, type) -> details template
# Each value in the template is either a static value or a tuple (generator_name, args)
TIER2_TEMPLATES = {
    # Analytics
    ("athena", "workgroup"): {"state": "ENABLED", "output_location": "s3://athena-results/"},
    ("athena", "named-query"): {"database": "default", "query_string": "SELECT 1"},
    ("athena", "data-catalog"): {"type": "HIVE"},
    ("glue", "database"): {"catalog_id": "{account_id}", "location_uri": "s3://data-lake/"},
    ("glue", "job"): {"command": "glueetl", "max_retries": 3, "timeout": 120, "worker_type": "G.1X", "number_of_workers": 5},
    ("glue", "crawler"): {"state": "READY", "database_name": "datalake", "schedule": "cron(0 1 * * ? *)"},
    ("glue", "connection"): {"connection_type": "JDBC", "physical_connection_requirements": {}},
    ("glue", "table"): {"database_name": "datalake", "table_type": "EXTERNAL_TABLE", "storage_location": "s3://data-lake/tables/"},

    # Containers
    ("ecs", "cluster"): {"status": "ACTIVE", "running_tasks": 5, "pending_tasks": 0, "active_services": 3, "registered_container_instances": 0, "capacity_providers": ["FARGATE"]},
    ("ecs", "service"): {"status": "ACTIVE", "desired_count": 3, "running_count": 3, "launch_type": "FARGATE", "scheduling_strategy": "REPLICA"},
    ("ecs", "task-definition"): {"status": "ACTIVE", "network_mode": "awsvpc", "requires_compatibilities": ["FARGATE"], "cpu": "256", "memory": "512"},
    ("ecs", "capacity-provider"): {"status": "ACTIVE", "auto_scaling_group_provider": None},
    ("eks", "cluster"): {"status": "ACTIVE", "version": "1.29", "platform_version": "eks.8", "endpoint": "https://EXAMPLE.gr7.us-east-1.eks.amazonaws.com"},
    ("eks", "addon"): {"status": "ACTIVE", "addon_version": "v1.16.0-eksbuild.1"},
    ("eks", "nodegroup"): {"status": "ACTIVE", "capacity_type": "ON_DEMAND", "instance_types": ["m5.large"], "desired_size": 3, "min_size": 2, "max_size": 5},
    ("ecr", "repository"): {"image_tag_mutability": "MUTABLE", "scan_on_push": True, "encryption_type": "AES256", "image_count": 15},
    ("ecr-public", "repository"): {"image_tag_mutability": "MUTABLE"},

    # Networking
    ("cloudfront", "distribution"): {"status": "Deployed", "enabled": True, "domain_name": "d1234.cloudfront.net", "price_class": "PriceClass_100", "http_version": "http2", "is_ipv6_enabled": True},
    ("route53", "hosted-zone"): {"record_count": 25, "private_zone": False, "comment": "Main domain"},
    ("route53", "health-check"): {"type": "HTTPS", "fqdn": "example.com", "port": 443, "request_interval": 30},
    ("route53domains", "domain"): {"auto_renew": True, "transfer_lock": True, "expiration_date": "2027-01-01"},
    ("apigateway", "rest-api"): {"api_key_source": "HEADER", "endpoint_configuration": "REGIONAL"},
    ("apigatewayv2", "http-api"): {"protocol_type": "HTTP", "api_endpoint": "https://api-id.execute-api.us-east-1.amazonaws.com"},
    ("directconnect", "connection"): {"state": "available", "bandwidth": "1Gbps", "location": "EqDC2"},

    # Security
    ("wafv2", "web-acl-regional"): {"capacity": 100, "rules": 5, "default_action": "allow"},
    ("guardduty", "detector"): {"status": "ENABLED", "finding_publishing_frequency": "FIFTEEN_MINUTES"},
    ("inspector2", "coverage"): {"status": "ENABLED", "resource_type": "EC2"},
    ("securityhub", "hub"): {"auto_enable_controls": True, "subscribed_at": "2024-01-15"},
    ("accessanalyzer", "analyzer"): {"type": "ACCOUNT", "status": "ACTIVE"},
    ("cognito", "user-pool"): {"status": "ACTIVE", "estimated_number_of_users": 1500, "mfa_configuration": "OPTIONAL"},
    ("cognito", "identity-pool"): {"allow_unauthenticated_identities": False},
    ("acm", "certificate"): {"status": "ISSUED", "type": "AMAZON_ISSUED", "key_algorithm": "RSA_2048", "renewal_eligibility": "ELIGIBLE", "in_use": True, "not_after": "2026-12-01", "domain_name": "*.example.com", "validation_method": "DNS"},
    ("acm-pca", "certificate-authority"): {"status": "ACTIVE", "type": "ROOT"},
    ("shield", "protection"): {"resource_type": "CLOUDFRONT_DISTRIBUTION"},
    ("macie2", "classification-job"): {"job_status": "RUNNING", "job_type": "SCHEDULED"},
    ("detective", "graph"): {"status": "ENABLED"},
    ("sso", "instance"): {"status": "ACTIVE"},
    ("sso", "permission-set"): {"session_duration": "PT1H", "relay_state": None},

    # Management & Monitoring
    ("cloudwatch", "metric-alarm"): {"state_value": "OK", "metric_name": "CPUUtilization", "namespace": "AWS/EC2", "comparison_operator": "GreaterThanThreshold", "threshold": 80.0, "period": 300, "evaluation_periods": 3},
    ("cloudwatch", "dashboard"): {"dashboard_body_length": 2500},
    ("logs", "log-group"): {"retention_days": 30, "stored_bytes": 1073741824, "metric_filter_count": 2},
    ("logs", "metric-filter"): {"filter_pattern": "[ip, id, user, timestamp, request, status_code, size]"},
    ("cloudtrail", "trail"): {"is_multi_region": True, "is_logging": True, "has_custom_event_selectors": True, "s3_bucket": "cloudtrail-logs"},
    ("ssm", "parameter"): {"type": "SecureString", "version": 3, "tier": "Standard"},
    ("ssm", "document"): {"document_type": "Command", "document_format": "YAML", "platform_types": ["Linux"]},
    ("config", "config-rule"): {"compliance_type": "COMPLIANT", "source_owner": "AWS"},
    ("config", "configuration-recorder"): {"recording": True, "all_supported": True},
    ("sns", "topic"): {"subscriptions_confirmed": 3, "subscriptions_pending": 0, "policy": "default"},
    ("sns", "subscription"): {"protocol": "email", "endpoint": "alerts@example.com", "confirmation_pending": False},
    ("sqs", "queue"): {"approximate_message_count": 0, "visibility_timeout": 30, "maximum_message_size": 262144, "message_retention_period": 345600, "delay_seconds": 0, "fifo": False},
    ("events", "rule"): {"state": "ENABLED", "schedule_expression": "rate(5 minutes)", "event_bus_name": "default"},
    ("events", "event-bus"): {"policy": "default"},
    ("xray", "group"): {"filter_expression": "service(\"api\")"},
    ("xray", "sampling-rule"): {"priority": 1000, "fixed_rate": 0.05, "reservoir_size": 1},
    ("grafana", "workspace"): {"status": "ACTIVE", "grafana_version": "9.4", "authentication_providers": ["SAML"]},
    ("amp", "workspace"): {"status": "ACTIVE"},
    ("synthetics", "canary"): {"status": "RUNNING", "runtime_version": "syn-nodejs-puppeteer-7.0", "schedule_expression": "rate(5 minutes)"},
    ("ce", "anomaly-monitor"): {"monitor_type": "DIMENSIONAL", "monitor_dimension": "SERVICE"},
    ("budgets", "budget"): {"budget_type": "COST", "time_unit": "MONTHLY", "limit_amount": "10000", "limit_unit": "USD"},
    ("health", "event"): {"event_type_category": "accountNotification", "status_code": "open", "service": "EC2"},
    ("organizations", "account"): {"email": "admin@example.com", "status": "ACTIVE", "joined_method": "CREATED"},
    ("organizations", "organizational-unit"): {"name": "Production"},

    # Serverless & Integration
    ("stepfunctions", "state-machine"): {"status": "ACTIVE", "type": "STANDARD", "definition_length": 1500},
    ("kinesis", "stream"): {"status": "ACTIVE", "shard_count": 2, "retention_period_hours": 24, "stream_mode": "ON_DEMAND"},
    ("firehose", "delivery-stream"): {"status": "ACTIVE", "delivery_stream_type": "DirectPut", "destination_description": "S3"},
    ("kafka", "cluster"): {"state": "ACTIVE", "kafka_version": "3.6.0", "number_of_broker_nodes": 3, "instance_type": "kafka.m5.large"},
    ("eventbridge-scheduler", "schedule"): {"state": "ENABLED", "schedule_expression": "rate(1 hour)"},
    ("eventbridge-pipes", "pipe"): {"current_state": "RUNNING", "desired_state": "RUNNING"},
    ("schemas", "registry"): {"registry_name": "discovered-schemas"},

    # Storage
    ("efs", "file-system"): {"performance_mode": "generalPurpose", "throughput_mode": "bursting", "life_cycle_state": "available", "size_in_bytes": 1073741824, "encrypted": True},
    ("fsx", "file-system-lustre"): {"lifecycle": "AVAILABLE", "storage_capacity": 1200, "storage_type": "SSD"},
    ("backup", "vault"): {"number_of_recovery_points": 45, "encryption_key_arn": "arn:aws:kms:us-east-1:111122223333:key/example"},
    ("backup", "plan"): {"version_id": "1", "rules_count": 2},
    ("dlm", "lifecycle-policy"): {"state": "ENABLED", "policy_type": "EBS_SNAPSHOT_MANAGEMENT"},

    # Database extras
    ("dynamodb", "table"): {"table_status": "ACTIVE", "billing_mode": "PAY_PER_REQUEST", "item_count": 150000, "table_size_bytes": 52428800, "global_secondary_indexes": 2, "stream_enabled": True},
    ("elasticache", "cluster"): {"engine": "redis", "engine_version": "7.1", "cache_node_type": "cache.r6g.large", "num_cache_nodes": 3, "status": "available"},
    ("elasticache", "replication-group"): {"status": "available", "cluster_enabled": True, "num_node_groups": 2},
    ("memorydb", "cluster"): {"status": "available", "engine_version": "7.1", "node_type": "db.r6g.large"},
    ("docdb", "cluster"): {"engine": "docdb", "engine_version": "5.0.0", "status": "available", "db_cluster_members": 3},
    ("neptune", "cluster"): {"engine": "neptune", "engine_version": "1.3.0.0", "status": "available"},
    ("redshift", "cluster"): {"cluster_status": "available", "node_type": "dc2.large", "number_of_nodes": 2, "db_name": "analytics", "encrypted": True},
    ("opensearch", "domain"): {"engine_version": "OpenSearch_2.11", "cluster_config": "r6g.large.search", "instance_count": 3, "ebs_enabled": True, "ebs_volume_size": 100},
    ("keyspaces", "keyspace"): {"replication_strategy": "SINGLE_REGION"},
    ("dax", "cluster"): {"status": "available", "node_type": "dax.r5.large", "total_nodes": 3},

    # DevTools
    ("cloudformation", "stack"): {"stack_status": "CREATE_COMPLETE", "template_description": "Application infrastructure", "outputs_count": 5},
    ("cloudformation", "stack-set"): {"status": "ACTIVE", "permission_model": "SELF_MANAGED"},
    ("codebuild", "project"): {"source_type": "GITHUB", "environment_type": "LINUX_CONTAINER", "compute_type": "BUILD_GENERAL1_MEDIUM"},
    ("codepipeline", "pipeline"): {"stage_count": 4, "version": 3},
    ("codedeploy", "application"): {"compute_platform": "Server"},
    ("codeartifact", "repository"): {"domain_name": "my-domain", "external_connections": 1},

    # AI/ML
    ("sagemaker", "endpoint"): {"endpoint_status": "InService", "instance_type": "ml.m5.xlarge", "instance_count": 2},
    ("sagemaker", "notebook-instance"): {"instance_type": "ml.t3.medium", "status": "InService"},
    ("sagemaker", "model"): {"primary_container": "image-classification"},
    ("bedrock", "custom-model"): {"model_status": "ACTIVE", "base_model_identifier": "anthropic.claude-3-sonnet"},
    ("bedrock", "knowledge-base"): {"status": "ACTIVE", "storage_type": "OPENSEARCH_SERVERLESS"},
    ("bedrock", "guardrail"): {"status": "READY", "version": "1"},
    ("lexv2", "bot"): {"bot_status": "Available", "data_privacy": True},
    ("rekognition", "collection"): {"face_count": 500},
    ("textract", "adapter"): {"status": "ACTIVE"},
    ("transcribe", "vocabulary"): {"language_code": "en-US", "vocabulary_state": "READY"},
    ("translate", "terminology"): {"source_language": "en", "target_languages": ["fr", "de", "es"]},
    ("comprehend", "entity-recognizer"): {"status": "TRAINED", "language_code": "en"},
    ("polly", "lexicon"): {"language_code": "en-US", "lexeme_count": 50},
    ("personalize", "dataset-group"): {"status": "ACTIVE"},
    ("kendra", "index"): {"status": "ACTIVE", "edition": "ENTERPRISE_EDITION"},
    ("frauddetector", "detector"): {"status": "ACTIVE"},

    # Media
    ("mediaconvert", "queue"): {"status": "ACTIVE", "type": "ON_DEMAND"},
    ("medialive", "channel"): {"state": "IDLE", "channel_class": "STANDARD"},
    ("mediapackage", "channel"): {"description": "Live channel"},
    ("ivs", "channel"): {"latency_mode": "LOW", "type": "STANDARD", "authorized": False},

    # Other
    ("workspaces", "workspace"): {"state": "AVAILABLE", "bundle_id": "wsb-12345", "compute_type": "VALUE", "running_mode": "AUTO_STOP"},
    ("amplify", "app"): {"platform": "WEB", "repository": "https://github.com/org/app"},
    ("connect", "instance"): {"instance_status": "ACTIVE", "identity_management_type": "SAML"},
    ("transfer", "server"): {"state": "ONLINE", "protocols": ["SFTP"], "identity_provider_type": "SERVICE_MANAGED"},
    ("mq", "broker"): {"broker_state": "RUNNING", "engine_type": "ACTIVEMQ", "engine_version": "5.17.6", "host_instance_type": "mq.m5.large", "deployment_mode": "ACTIVE_STANDBY_MULTI_AZ"},
    ("sesv2", "identity"): {"identity_type": "DOMAIN", "sending_enabled": True, "dkim_status": "SUCCESS"},
    ("ram", "resource-share"): {"status": "ACTIVE", "allow_external_principals": False},
    ("appflow", "flow"): {"flow_status": "Active", "source_connector_type": "Salesforce", "destination_connector_type": "S3"},
    ("servicediscovery", "namespace"): {"type": "DNS_PRIVATE"},
    ("servicediscovery", "service"): {"dns_config": "A", "instances_count": 3},
    ("lightsail", "instance"): {"state": "running", "blueprint_id": "amazon_linux_2", "bundle_id": "nano_3_0"},
    ("lightsail", "database"): {"state": "available", "engine": "mysql", "engine_version": "8.0"},
    ("autoscaling", "auto-scaling-group"): {"min_size": 2, "max_size": 10, "desired_capacity": 4, "health_check_type": "ELB"},
    ("batch", "compute-environment"): {"state": "ENABLED", "type": "MANAGED", "status": "VALID"},
    ("batch", "job-queue"): {"state": "ENABLED", "status": "VALID", "priority": 1},
    ("apprunner", "service"): {"status": "RUNNING", "source_type": "ECR"},
    ("imagebuilder", "pipeline"): {"status": "ENABLED", "platform": "Linux"},
    ("quicksight", "dashboard"): {"version_number": 3},
    ("quicksight", "data-set"): {"import_mode": "SPICE", "row_count": 100000},
    ("lakeformation", "resource"): {"resource_type": "DATABASE"},
    ("emr", "cluster"): {"state": "WAITING", "release_label": "emr-7.0.0", "instance_count": 5},
    ("mwaa", "environment"): {"status": "AVAILABLE", "airflow_version": "2.8.1", "environment_class": "mw1.medium"},
    ("datazone", "domain"): {"status": "AVAILABLE"},
    ("fis", "experiment-template"): {"action_count": 3, "stop_condition_count": 1},
    ("location", "map"): {"map_name": "ExampleMap", "data_source": "Esri"},
    ("appconfig", "application"): {"description": "Main application configuration"},
    ("appconfig", "environment"): {"state": "READY_FOR_DEPLOYMENT"},
    ("resiliencehub", "app"): {"compliance_status": "POLICY_BREACHED", "assessment_schedule": "DAILY"},
    ("securitylake", "data-lake"): {"status": "ENABLED"},
    ("devicefarm", "project"): {"default_job_timeout_minutes": 150},
    ("iot", "thing"): {"thing_type_name": "sensor", "version": 1},
    ("iotsitewise", "asset"): {"asset_status": "ACTIVE"},
    ("gamelift", "fleet"): {"status": "ACTIVE", "fleet_type": "ON_DEMAND", "instance_type": "c5.large"},
    ("outposts", "outpost"): {"life_cycle_status": "ACTIVE", "availability_zone": "us-east-1a"},
    ("serverlessrepo", "application"): {"author": "AWS"},
    ("servicecatalog", "portfolio"): {"provider_name": "IT-Platform"},
    ("servicecatalog", "product"): {"product_type": "CLOUD_FORMATION_TEMPLATE"},
    ("compute-optimizer", "ec2-recommendation"): {"finding": "OVER_PROVISIONED", "current_instance_type": "m5.xlarge", "recommended_instance_type": "m5.large"},
    ("service-quotas", "service-quota"): {"service_code": "ec2", "quota_code": "L-1216C47A", "value": 5000.0, "adjustable": True},
    ("resource-groups", "group"): {"group_type": "AWS::CloudFormation::Stack"},
    ("resource-explorer-2", "index"): {"type": "AGGREGATOR", "state": "ACTIVE"},
    ("auditmanager", "assessment"): {"status": "ACTIVE", "compliance_type": "AWS_Control_Tower"},
    ("networkmanager", "global-network"): {"state": "AVAILABLE"},
    ("globalaccelerator", "accelerator"): {"status": "DEPLOYED", "ip_address_type": "IPV4", "enabled": True},
    ("route53resolver", "resolver-endpoint"): {"direction": "INBOUND", "status": "OPERATIONAL", "ip_address_count": 2},
    ("vpc-lattice", "service"): {"status": "ACTIVE", "auth_type": "AWS_IAM"},
    ("dms", "replication-instance"): {"replication_instance_status": "available", "replication_instance_class": "dms.r5.large", "engine_version": "3.5.2"},
    ("ds", "directory"): {"type": "MicrosoftAD", "edition": "Standard", "stage": "Active"},
    ("dsql", "cluster"): {"status": "ACTIVE"},
    ("redshift-serverless", "namespace"): {"status": "AVAILABLE", "db_name": "dev"},
    ("redshift-serverless", "workgroup"): {"status": "AVAILABLE", "base_capacity": 32},
    ("opensearch-serverless", "collection"): {"status": "ACTIVE", "type": "SEARCH"},
    ("emr-serverless", "application"): {"state": "CREATED", "type": "SPARK", "release_label": "emr-7.0.0"},
    ("application-autoscaling", "scalable-target"): {"service_namespace": "ecs", "resource_id": "service/cluster/svc", "scalable_dimension": "ecs:service:DesiredCount", "min_capacity": 2, "max_capacity": 10},
    ("timestream-influxdb", "db-instance"): {"status": "AVAILABLE", "db_instance_type": "db.influx.medium", "db_storage_type": "InfluxIOIncludedT1", "allocated_storage": 20},
    ("cleanrooms", "collaboration"): {"status": "ACTIVE", "member_count": 2},
    ("network-firewall", "firewall"): {"firewall_status": "READY", "vpc_id": "vpc-example"},
    ("network-firewall", "firewall-policy"): {"number_of_firewalls": 1},
    ("pipes", "pipe"): {"current_state": "RUNNING"},
    ("scheduler", "schedule"): {"state": "ENABLED", "schedule_expression": "rate(1 hour)"},
    ("fms", "policy"): {"security_service_type": "WAF", "remediation_enabled": True},
    ("cloudhsmv2", "cluster"): {"state": "ACTIVE", "hsm_type": "hsm1.medium"},
    ("storagegateway", "gateway"): {"gateway_type": "FILE_S3", "gateway_state": "RUNNING"},
    ("datasync", "task"): {"status": "AVAILABLE"},
    ("mediaconnect", "flow"): {"status": "ACTIVE", "source_type": "STANDARD"},
    ("mediastore", "container"): {"status": "ACTIVE", "access_logging_enabled": True},
    ("mediatailor", "playback-configuration"): {"ad_decision_server_url": "https://ads.example.com"},
    ("appflow", "connector-profile"): {"connection_mode": "Public", "connector_type": "Salesforce"},
    ("appsync", "graphql-api"): {"authentication_type": "AMAZON_COGNITO_USER_POOLS", "xray_enabled": True},
    ("elasticbeanstalk", "application"): {"description": "Web application"},
    ("elasticbeanstalk", "environment"): {"status": "Ready", "health": "Green", "platform": "Python 3.11", "tier": "WebServer"},
}


# ---------------------------------------------------------------------------
# ID pattern generators per (service, type) - for realistic resource IDs
# ---------------------------------------------------------------------------

# Default: UUID-based
# This dict overrides with service-specific patterns
ID_PREFIXES = {
    "accessanalyzer": "analyzer",
    "appconfig": "app", "apprunner": "svc", "appsync": "api",
    "amp": "ws", "amplify": "app",
    "batch": "ce", "backup": "vault",
    "cloudformation": "stack", "cloudfront": "E",
    "cloudtrail": "trail", "cloudwatch": "alarm",
    "codebuild": "proj", "codepipeline": "pipe",
    "config": "recorder", "connect": "instance",
    "datazone": "dzd", "detective": "graph",
    "directconnect": "dxcon",
    "dlm": "policy", "dms": "dms",
    "dsql": "cluster",
    "events": "rule", "efs": "fs",
    "eks": "cluster",
    "elasticache": "cluster", "elasticbeanstalk": "app",
    "emr": "j", "firehose": "stream",
    "fis": "template", "fsx": "fs",
    "gamelift": "fleet", "grafana": "g",
    "guardduty": "detector",
    "imagebuilder": "pipeline",
    "inspector2": "coverage",
    "iot": "thing", "ivs": "channel",
    "kafka": "cluster", "kendra": "index",
    "kinesis": "stream",
    "lexv2": "bot",
    "lightsail": "ls",
    "location": "map", "logs": "/aws/",
    "macie2": "job", "mediaconvert": "queue",
    "medialive": "channel",
    "memorydb": "cluster", "mq": "broker",
    "mwaa": "env", "neptune": "cluster",
    "opensearch": "domain",
    "outposts": "op",
    "personalize": "dsg", "polly": "lexicon",
    "quicksight": "dashboard",
    "rekognition": "collection",
    "resiliencehub": "app",
    "sagemaker": "endpoint",
    "securityhub": "hub",
    "securitylake": "lake",
    "servicecatalog": "port",
    "servicediscovery": "ns",
    "sesv2": "identity",
    "sso": "ssoins",
    "stepfunctions": "arn",
    "synthetics": "canary",
    "textract": "adapter",
    "transcribe": "vocab",
    "transfer": "s",
    "translate": "terminology",
    "vpc-lattice": "svc",
    "wafv2": "webacl",
    "workspaces": "ws",
    "xray": "group",
}


def _gen_id(service, rtype):
    """Generate a realistic resource ID for a given service/type."""
    prefix = ID_PREFIXES.get(service, "res")
    if service == "logs" and rtype == "log-group":
        return f"/aws/{random.choice(['lambda','ecs','apigateway','rds'])}/{_hex(6)}"
    if service == "stepfunctions":
        return f"state-machine-{_hex(8)}"
    return f"{prefix}-{_hex(8)}"


# ---------------------------------------------------------------------------
# Resource generation engine
# ---------------------------------------------------------------------------

def _gen_tier2_resources(account_id, pool):
    """Generate resources for Tier 2 services using templates."""
    resources = []

    # Track which (service, type) pairs are handled by Tier 1
    tier1_services = {"vpc", "ec2", "s3", "iam", "lambda", "rds",
                      "secretsmanager", "kms", "elbv2"}

    for (svc, rtype), details_template in TIER2_TEMPLATES.items():
        if svc in tier1_services:
            continue

        # Determine if global or regional
        global_services = {"iam", "organizations", "route53", "route53domains",
                           "cloudfront", "shield", "budgets", "ce", "health",
                           "networkmanager", "globalaccelerator"}
        is_global = svc in global_services

        # How many resources to generate
        count = random.randint(2, 5)

        for i in range(count):
            rid = _gen_id(svc, rtype)
            region = None if is_global else random.choice(REGIONS[:4])
            name = f"{rtype}-{_hex(4)}"

            # Process details template - replace placeholders
            details = {}
            for k, v in details_template.items():
                if isinstance(v, str) and "{account_id}" in v:
                    details[k] = v.format(account_id=account_id)
                else:
                    details[k] = v

            pool.add(account_id, svc, rtype, rid)
            resources.append({
                "service": svc, "type": rtype, "id": rid,
                "arn": _arn(svc, region or "us-east-1", account_id, rtype, rid),
                "name": name, "region": region, "account_id": account_id,
                "details": details,
                "tags": _tags(name),
            })

    return resources


def _gen_tier3_resources(account_id, pool, generated_pairs=None):
    """Generate generic resources for any service/type NOT already generated.

    Args:
        generated_pairs: set of (service, type) tuples already generated by Tier 1/2.
    """
    resources = []

    if generated_pairs is None:
        generated_pairs = set()

    global_services = {"iam", "organizations", "route53", "route53domains",
                       "cloudfront", "shield", "budgets", "ce", "health",
                       "networkmanager", "globalaccelerator"}

    for svc, types in _CMIPSMAP_TYPES.items():
        for rtype in types:
            if (svc, rtype) in generated_pairs:
                continue

            is_global = svc in global_services
            count = random.randint(1, 3)
            for i in range(count):
                rid = _gen_id(svc, rtype)
                region = None if is_global else random.choice(REGIONS[:4])
                name = f"{rtype}-{_hex(4)}"

                resources.append({
                    "service": svc, "type": rtype, "id": rid,
                    "arn": _arn(svc, region or "us-east-1", account_id, rtype, rid),
                    "name": name, "region": region, "account_id": account_id,
                    "details": {
                        "status": random.choice(["active", "available", "enabled", "ready"]),
                        "created_date": _past_dt(400),
                    },
                    "tags": _tags(name),
                })

    return resources


# ---------------------------------------------------------------------------
# Drift mutation engine
# ---------------------------------------------------------------------------

def _apply_drift(resources, mutation_rate=0.08):
    """Apply realistic mutations to a resource list to simulate drift.

    Returns a new list with some resources removed, some added, some modified.
    """
    new_resources = []
    added = []
    removed_ids = set()

    for r in resources:
        roll = random.random()

        # ~3% removed
        if roll < 0.03:
            removed_ids.add(r["id"])
            continue

        # ~mutation_rate% modified
        if roll < 0.03 + mutation_rate:
            r = _mutate_resource(r)

        new_resources.append(r)

    # ~5% new resources (based on existing count)
    n_new = max(1, int(len(resources) * 0.05))
    for _ in range(n_new):
        # Deep-clone a random resource and change its ID to make it "new"
        template = random.choice(resources)
        new_r = json.loads(json.dumps(template, default=str))
        new_id = _gen_id(new_r["service"], new_r["type"])
        new_r["id"] = new_id
        new_r["name"] = f"{new_r['type']}-new-{_hex(4)}"
        old_arn = new_r.get("arn", "")
        if "/" in old_arn:
            new_r["arn"] = old_arn.rsplit("/", 1)[0] + "/" + new_id
        if new_r.get("tags"):
            new_r["tags"]["Name"] = new_r["name"]
        added.append(new_r)

    return new_resources + added


def _mutate_resource(r):
    """Apply a realistic mutation to a single resource."""
    r = json.loads(json.dumps(r, default=str))
    svc = r["service"]
    details = r["details"]

    # State transitions
    if "state" in details:
        states = {"running": "stopped", "stopped": "running",
                  "available": "in-use", "in-use": "available",
                  "ACTIVE": "INACTIVE", "ENABLED": "DISABLED"}
        old = details["state"]
        details["state"] = states.get(old, old)

    # Tag mutations
    if random.random() < 0.5:
        r["tags"]["LastModified"] = _past_dt(5)
    if random.random() < 0.3 and "Environment" in r["tags"]:
        r["tags"]["Environment"] = random.choice(ENVIRONMENTS)

    # Service-specific mutations
    if svc == "ec2" and r["type"] == "instance" and "instance_type" in details:
        upgrades = {"t3.micro": "t3.small", "t3.small": "t3.medium",
                    "m5.large": "m5.xlarge", "c5.large": "c5.xlarge"}
        old_type = details["instance_type"]
        details["instance_type"] = upgrades.get(old_type, old_type)

    if svc == "lambda" and "runtime" in details:
        runtime_upgrades = {
            "python3.9": "python3.12", "python3.11": "python3.12",
            "nodejs18.x": "nodejs20.x", "java17": "java21",
        }
        old_rt = details["runtime"]
        details["runtime"] = runtime_upgrades.get(old_rt, old_rt)

    if svc == "rds" and "allocated_storage" in details:
        details["allocated_storage"] = int(details["allocated_storage"] * 1.5)

    return r


# ---------------------------------------------------------------------------
# Main generator - orchestrates everything
# ---------------------------------------------------------------------------

def generate_demo_db(db_path, n_accounts=3, n_scans=3, seed=42, progress=None):
    """Generate a complete demo database.

    Args:
        db_path: Path to the SQLite database file
        n_accounts: Number of accounts (1-5, uses first N from ACCOUNTS)
        n_scans: Number of scans per account (1-5)
        seed: Random seed for reproducibility
        progress: Optional callback(message) for progress updates

    Returns:
        Dict with generation statistics
    """
    random.seed(seed)

    accounts = ACCOUNTS[:n_accounts]

    # Anchor all generated timestamps to today's UTC midnight so that two runs
    # with the same seed on the same day produce a byte-identical database.
    # Using midnight (not the exact instant) keeps the data reproducible while
    # still letting it age by whole days, so it always looks recent.
    global _NOW_ANCHOR
    _NOW_ANCHOR = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)

    # Scan timestamps: spread across the last 60 days
    now = _NOW_ANCHOR
    scan_offsets = []
    if n_scans == 1:
        scan_offsets = [0]
    elif n_scans == 2:
        scan_offsets = [30, 0]
    elif n_scans == 3:
        scan_offsets = [45, 15, 0]
    elif n_scans == 4:
        scan_offsets = [60, 30, 10, 0]
    else:
        scan_offsets = [75, 45, 25, 10, 0]

    conn = get_connection(db_path)
    total_resources = 0
    total_scans = 0
    services_seen = set()

    for account_id, alias, profile in accounts:
        if progress:
            progress(f"Generating account: {alias} [{account_id}]")

        # Build baseline resources (Scan 1).
        # Use zlib.crc32 (deterministic) rather than hash(), whose string hashing
        # is salted per-process (PYTHONHASHSEED) and would break --seed reproducibility.
        random.seed(seed + zlib.crc32(account_id.encode()))
        pool = RefPool()

        # Tier 1 - critical services in dependency order
        baseline = []
        baseline.extend(_gen_vpc(account_id, pool))
        baseline.extend(_gen_ec2(account_id, pool))
        baseline.extend(_gen_s3(account_id, pool))
        baseline.extend(_gen_iam(account_id, pool))
        baseline.extend(_gen_lambda(account_id, pool))
        baseline.extend(_gen_rds(account_id, pool))
        baseline.extend(_gen_secretsmanager(account_id, pool))
        baseline.extend(_gen_kms(account_id, pool))
        baseline.extend(_gen_elbv2(account_id, pool))

        # Tier 2 - template-based services
        baseline.extend(_gen_tier2_resources(account_id, pool))

        # Track which (service, type) pairs are already generated
        generated_pairs = {(r["service"], r["type"]) for r in baseline}

        # Tier 3 - auto-generated remaining services (fills gaps)
        baseline.extend(_gen_tier3_resources(account_id, pool, generated_pairs))

        services_seen.update(r["service"] for r in baseline)

        if progress:
            progress(f"  Baseline: {len(baseline)} resources across "
                     f"{len(set(r['service'] for r in baseline))} services")

        # Generate scans with drift
        current_resources = baseline
        for scan_idx, days_ago in enumerate(scan_offsets):
            ts = now - timedelta(days=days_ago, hours=random.randint(0, 12))
            timestamp = ts.strftime('%Y-%m-%d %H:%M:%S UTC')

            # Apply drift for scans after the first
            if scan_idx > 0:
                current_resources = _apply_drift(current_resources)

            # Build scan result in the format store_scan() expects
            services_in_scan = sorted(set(r["service"] for r in current_resources))
            regions_in_scan = sorted(set(r.get("region") or "global" for r in current_resources))

            result = {
                "metadata": {
                    "account_id": account_id,
                    "timestamp": timestamp,
                    "scan_duration_seconds": round(random.uniform(60, 180), 2),
                    "services_scanned": len(services_in_scan),
                    "regions_scanned": len(regions_in_scan),
                    "resource_count": len(current_resources),
                },
                "resources": current_resources,
            }

            store_scan(conn, result, profile=profile, account_alias=alias,
                       scanned_services=services_in_scan)
            total_scans += 1
            total_resources += len(current_resources)

            if progress:
                label = f"{days_ago}d ago" if days_ago > 0 else "now"
                progress(f"  Scan {scan_idx + 1}/{len(scan_offsets)} ({label}): "
                         f"{len(current_resources)} resources")

    conn.close()

    return {
        "db_path": db_path,
        "accounts": len(accounts),
        "scans": total_scans,
        "total_resource_rows": total_resources,
        "services_covered": len(services_seen),
    }
