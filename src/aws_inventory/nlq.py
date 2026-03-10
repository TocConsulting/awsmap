"""
Natural Language Query (NLQ) engine for awsmap.

Converts natural-language questions about AWS inventory into SQL queries
using a built-in zero-dependency parser.
"""

import difflib
import json
import os
import re
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 1. Service/Type taxonomy — DATA for fuzzy name matching only
# ---------------------------------------------------------------------------

_AWSMAP_TYPES = {
    "accessanalyzer": ["analyzer", "archive-rule"],
    "acm": ["certificate"],
    "acm-pca": ["certificate-authority", "permission"],
    "amp": ["workspace", "alert-manager", "rule-groups-namespace"],
    "amplify": ["app", "branch", "domain"],
    "apigateway": ["rest-api", "api-key", "stage", "usage-plan", "vpc-link"],
    "apigatewayv2": ["http-api", "websocket-api", "domain-name", "stage", "vpc-link"],
    "appconfig": ["application", "environment", "configuration-profile", "deployment-strategy"],
    "apprunner": ["service", "connection", "vpc-connector"],
    "appsync": ["graphql-api", "data-source", "function", "api-key", "domain-name"],
    "athena": ["named-query", "workgroup", "data-catalog"],
    "autoscaling": ["auto-scaling-group", "launch-configuration", "scaling-policy"],
    "backup": ["vault", "plan", "framework", "report-plan"],
    "batch": ["compute-environment", "job-queue", "job-definition", "scheduling-policy"],
    "bedrock": ["custom-model", "knowledge-base", "agent", "data-source", "guardrail"],
    "budgets": ["budget", "budget-action"],
    "cloudformation": ["stack", "stack-set"],
    "cloudfront": ["distribution", "cache-policy", "function", "origin-access-control", "origin-access-identity"],
    "cloudtrail": ["trail", "event-data-store"],
    "cloudwatch": ["metric-alarm", "composite-alarm", "dashboard", "metric-stream"],
    "codebuild": ["project", "report-group"],
    "codedeploy": ["application", "deployment-group", "deployment-config"],
    "codepipeline": ["pipeline"],
    "cognito": ["user-pool", "user-pool-client", "identity-pool"],
    "compute-optimizer": ["lambda-recommendation", "ec2-recommendation", "asg-recommendation", "ebs-recommendation"],
    "config": ["configuration-recorder", "delivery-channel", "config-rule", "conformance-pack", "configuration-aggregator"],
    "connect": ["instance", "contact-flow", "queue", "routing-profile"],
    "datazone": ["domain", "project", "environment"],
    "dax": ["cluster", "parameter-group", "subnet-group"],
    "detective": ["graph", "member"],
    "directconnect": ["connection", "gateway", "lag", "virtual-interface-private", "virtual-interface-public", "virtual-interface-transit"],
    "dms": ["replication-instance", "endpoint", "replication-task", "certificate", "replication-subnet-group"],
    "docdb": ["cluster", "instance"],
    "dsql": ["cluster"],
    "dynamodb": ["table", "stream", "global-table", "backup"],
    "ec2": ["instance", "security-group", "volume", "key-pair", "elastic-ip", "network-interface", "snapshot", "ami", "placement-group", "transit-gateway-attachment"],
    "ecr": ["repository"],
    "ecr-public": ["repository"],
    "ecs": ["cluster", "service", "task-definition", "capacity-provider"],
    "efs": ["file-system", "access-point", "replication-configuration"],
    "eks": ["cluster", "addon", "nodegroup", "fargate-profile"],
    "elasticache": ["cluster", "replication-group", "serverless-cache", "user-group"],
    "elasticbeanstalk": ["application", "environment", "application-version"],
    "elb": ["classic-load-balancer"],
    "elbv2": ["target-group", "application-load-balancer", "network-load-balancer", "gateway-load-balancer", "listener"],
    "events": ["rule", "event-bus", "archive", "connection", "api-destination"],
    "firehose": ["delivery-stream"],
    "fsx": ["file-system-lustre", "file-system-windows", "file-system-ontap", "file-system-openzfs", "volume-ontap", "volume-openzfs", "backup"],
    "glue": ["database", "job", "crawler", "connection", "registry", "table"],
    "grafana": ["workspace"],
    "guardduty": ["detector", "filter", "ip-set", "threat-intel-set"],
    "iam": ["user", "role", "policy", "group", "instance-profile", "saml-provider", "oidc-provider"],
    "imagebuilder": ["pipeline", "image-recipe", "container-recipe", "component", "distribution-configuration", "infrastructure-configuration"],
    "kafka": ["cluster", "configuration", "connector", "serverless-cluster"],
    "kendra": ["index", "data-source"],
    "kinesis": ["stream", "stream-consumer"],
    "kms": ["key", "alias"],
    "lambda": ["function", "layer", "event-source-mapping"],
    "lightsail": ["instance", "database", "bucket", "distribution", "load-balancer", "certificate", "domain", "static-ip", "key-pair", "disk", "container-service"],
    "logs": ["log-group", "destination", "metric-filter", "subscription-filter"],
    "macie2": ["classification-job", "findings-filter", "custom-data-identifier", "allow-list", "member"],
    "mediaconvert": ["job-template", "preset", "queue"],
    "medialive": ["channel", "input", "input-security-group"],
    "mediapackage": ["channel", "origin-endpoint"],
    "memorydb": ["cluster", "acl", "user"],
    "mq": ["broker", "configuration"],
    "mwaa": ["environment"],
    "neptune": ["cluster", "instance"],
    "network-firewall": ["firewall", "firewall-policy", "rule-group"],
    "opensearch": ["domain", "serverless-collection"],
    "opensearch-serverless": ["collection", "access-policy", "security-policy", "vpc-endpoint"],
    "organizations": ["account", "organization", "organizational-unit", "policy", "root"],
    "quicksight": ["analysis", "dashboard", "data-set", "data-source"],
    "ram": ["resource-share"],
    "rds": ["db-instance", "db-cluster", "db-subnet-group", "db-parameter-group", "db-snapshot", "db-cluster-snapshot", "db-proxy", "option-group"],
    "redshift": ["cluster", "parameter-group", "subnet-group"],
    "redshift-serverless": ["namespace", "workgroup", "snapshot"],
    "resource-explorer-2": ["index", "view"],
    "route53": ["hosted-zone", "health-check", "query-logging-config"],
    "route53domains": ["domain"],
    "route53resolver": ["resolver-endpoint", "resolver-rule", "firewall-rule-group", "firewall-domain-list", "query-log-config"],
    "s3": ["bucket", "table-bucket", "table", "namespace"],
    "sagemaker": ["model", "endpoint", "notebook-instance", "training-job", "domain", "feature-group"],
    "secretsmanager": ["secret"],
    "securityhub": ["hub", "insight", "enabled-standard", "automation-rule"],
    "servicecatalog": ["portfolio", "product"],
    "servicediscovery": ["namespace", "service", "instance"],
    "sns": ["topic", "subscription"],
    "sqs": ["queue"],
    "ssm": ["parameter", "document", "association", "maintenance-window", "patch-baseline"],
    "sso": ["instance", "permission-set", "user", "group"],
    "stepfunctions": ["state-machine", "activity"],
    "storagegateway": ["gateway", "file-share", "volume", "tape"],
    "synthetics": ["canary", "group"],
    "timestream-influxdb": ["db-instance", "db-parameter-group"],
    "transfer": ["server", "user", "workflow", "connector", "certificate", "profile", "agreement", "host-key", "web-app"],
    "vpc": ["vpc", "subnet", "route-table", "internet-gateway", "network-acl", "dhcp-options", "vpc-endpoint", "nat-gateway", "transit-gateway", "transit-gateway-attachment", "vpc-peering"],
    "vpc-lattice": ["service", "service-network", "target-group", "listener"],
    "wafv2": ["web-acl-regional", "web-acl-cloudfront", "ip-set-regional", "rule-group-regional"],
    "workspaces": ["workspace", "directory"],
    "xray": ["group", "sampling-rule"],
}

# Generic resource relationships - used for inherited property checking
# Format: (service, type) -> list of relationships
# Each relationship defines how to check properties on related resources
_RESOURCE_RELATIONSHIPS = {
    ("iam", "user"): [
        {
            "related_field": "$.groups",      # Field containing related resource references
            "related_service": "iam",
            "related_type": "group",
            "inherit_checks": ["$.attached_policies"],  # Properties to also check on related resources
        }
    ],
}

# Type disambiguation rules - when multiple type words appear, which takes priority?
# Format: service -> list of (keywords, type, priority) tuples
# Higher priority wins. Used to resolve ambiguity like "IAM users and their policies"
_TYPE_PRIORITY = {
    "iam": [
        (["instance", "profile"], "instance-profile", 4),  # "instance profile" has highest priority
        (["user"], "user", 3),
        (["role"], "role", 2),
        (["group"], "group", 2),
        (["policy", "polic"], "policy", 1),  # "policy" has lowest priority
    ],
    "ecs": [
        (["service"], "service", 2),     # "service" has higher priority
        (["cluster"], "cluster", 1),     # "cluster" can be a GROUP BY field
    ],
}

# Service-specific patterns that need special handling
# Format: list of (keywords, service, type, constraints) tuples
_SERVICE_PATTERNS = {
    # Multi-word types where word order matters
    "multi_word_types": [
        (["athena", "named", "quer"], "athena", "named-query", {"remove_name_filter": True}),
        (["subscription", "filter"], "logs", "subscription-filter", {}),
        (["logs", "subscription"], "logs", "subscription-filter", {}),
        (["log", "subscription"], "logs", "subscription-filter", {}),
        (["step", "function"], "stepfunctions", "state-machine", {}),
        # CloudWatch alarms now handled by enhanced _score_svc_type() with issubset() logic
    ],
    # Service aliases - keyword combinations that map to different service names
    # NOTE: Order matters - more specific patterns should come LAST to override generic ones
    "service_aliases": [
        (["ecr", "public"], "ecr-public", None, {}),
        (["elb", "target", "group"], "elbv2", "target-group", {}),  # ELB target groups (more specific)
        (["route53", "resolver", "endpoint"], "route53resolver", "resolver-endpoint", {}),
        (["route53", "resolver", "rule"], "route53resolver", "resolver-rule", {}),
        (["route53", "resolver"], "route53resolver", None, {}),
        (["data", "zone", "project"], "datazone", "project", {}),
        (["data", "zone", "domain"], "datazone", "domain", {}),
        (["data", "zone"], "datazone", None, {}),
        (["timestream", "database"], "timestream-influxdb", "db-instance", {}),
        (["timestream"], "timestream-influxdb", None, {}),
        # VPC Lattice patterns LAST so they override generic matches
        (["vpc", "lattice", "service"], "vpc-lattice", "service", {}),
        (["vpc", "lattice", "target"], "vpc-lattice", "target-group", {}),
        (["vpc", "lattice"], "vpc-lattice", None, {}),
    ],
    # Services that should query all types (no type constraint)
    "query_all_types": [
        (["waf", "acl"], "wafv2", None, {}),
        (["ec2", "resource"], "ec2", None, {}),  # Matches "EC2 resources" or "EC2 resource"
    ],
    # Service corrections - when wrong service detected, correct it
    "service_corrections": [
        (["grafana"], "grafana", None, {"if_service": "workspaces"}),
        (["vpc", "subnet"], "vpc", "subnet", {"if_type": "vpc"}),
    ],
}

# ---------------------------------------------------------------------------
# Schema cache for _normalize_filter_fields
# ---------------------------------------------------------------------------

# Cache for DB schema fields: (service, type) -> set of field names
# Avoids repeated DB queries for the same service/type
_SCHEMA_CACHE = {}

# ---------------------------------------------------------------------------
# Dedup filter guard
# ---------------------------------------------------------------------------

def _add_filter(intent, filt):
    """Append filter only if no duplicate field+op+value already exists."""
    for existing in intent.get("filters", []):
        if (existing.get("field") == filt.get("field")
            and existing.get("op") == filt.get("op")
            and existing.get("value") == filt.get("value")):
            return
    intent["filters"].append(filt)

# ---------------------------------------------------------------------------
# Synonym / alias system
# ---------------------------------------------------------------------------

_SYNONYMS = [
    # (phrase, service, type)  — sorted by phrase length DESC for multi-word-first matching
    ("load balancers", "elbv2", "application-load-balancer"),
    ("load balancer", "elbv2", "application-load-balancer"),
    ("key pairs", "ec2", "key-pair"),
    ("key pair", "ec2", "key-pair"),
    ("dns zones", "route53", "hosted-zone"),
    ("dns zone", "route53", "hosted-zone"),
    ("event rules", "events", "rule"),
    ("containers", "ecs", "service"),
    ("container", "ecs", "service"),
    ("databases", "rds", "db-instance"),
    ("database", "rds", "db-instance"),
    ("secrets", "secretsmanager", "secret"),
    ("secret", "secretsmanager", "secret"),
    ("disks", "ec2", "volume"),
    ("disk", "ec2", "volume"),
    ("repos", "ecr", "repository"),
    ("repo", "ecr", "repository"),
    ("certs", "acm", "certificate"),
    ("cert", "acm", "certificate"),
    ("certificates", "acm", "certificate"),
    ("pipelines", "codepipeline", "pipeline"),
    ("pipeline", "codepipeline", "pipeline"),
    ("stacks", "cloudformation", "stack"),
    ("stack", "cloudformation", "stack"),
    ("distributions", "cloudfront", "distribution"),
    ("distribution", "cloudfront", "distribution"),
    ("queues", "sqs", "queue"),
    ("queue", "sqs", "queue"),
    ("topics", "sns", "topic"),
    ("topic", "sns", "topic"),
]

# ---------------------------------------------------------------------------
# Generic "using X" pattern
# ---------------------------------------------------------------------------

# (service_context, keyword_re, detail_field, value_prefix)
# service_context=None means matches any service
_USING_MAP = [
    # Lambda runtimes — already handled by existing runtime extraction,
    # so we only add RDS / ElastiCache engine mappings here.
    ("rds",         r"\baurora\b",     "$.engine", "aurora"),
    ("rds",         r"\bmysql\b",      "$.engine", "mysql"),
    ("rds",         r"\bpostgres\b",   "$.engine", "postgres"),
    ("rds",         r"\bmariadb\b",    "$.engine", "mariadb"),
    ("rds",         r"\boracle\b",     "$.engine", "oracle"),
    ("rds",         r"\bsqlserver\b",  "$.engine", "sqlserver"),
    ("rds",         r"\bsql\s+server\b", "$.engine", "sqlserver"),
    ("elasticache", r"\bredis\b",      "$.engine", "redis"),
    ("elasticache", r"\bmemcached\b",  "$.engine", "memcached"),
]

# ---------------------------------------------------------------------------
# Generic numeric field patterns
# ---------------------------------------------------------------------------

_NUMERIC_FIELD_PATTERNS = [
    ("allocated_storage",     "$.allocated_storage"),
    ("item_count",            "$.item_count"),
    ("size_bytes",            "$.size_bytes"),
    ("iops",                  "$.iops"),
    ("port",                  "$.port"),
    ("num_cache_nodes",       "$.num_cache_nodes"),
    ("read_capacity",         "$.read_capacity"),
    ("write_capacity",        "$.write_capacity"),
    ("available_ip_count",    "$.available_ip_address_count"),
    ("metric_filter_count",   "$.metric_filter_count"),
    ("approximate_messages",  "$.approximate_number_of_messages"),
    ("running_tasks_count",   "$.running_tasks_count"),
    ("pending_tasks_count",   "$.pending_tasks_count"),
    ("active_services_count", "$.active_services_count"),
    ("evaluation_periods",    "$.evaluation_periods"),
    ("record_count",          "$.resource_record_set_count"),
    ("max_message_size",      "$.max_message_size"),
    ("replica_count",         "$.replica_count"),
    ("shard_count",           "$.shard_count"),
    ("node_count",            "$.node_count"),
    ("desired_count",         "$.desired_count"),
    ("min_size",              "$.min_size"),
    ("max_size",              "$.max_size"),
    ("desired_capacity",      "$.desired_capacity"),
    ("layer_count",           "$.layers_count"),
    ("ingress_rules_count",   "$.ingress_rules_count"),
    ("egress_rules_count",    "$.egress_rules_count"),
    ("parameter_count",       "$.parameter_count"),
    ("table_count",           "$.table_count"),
]

# ---------------------------------------------------------------------------
# Time field mapping for relative time queries
# ---------------------------------------------------------------------------

_TIME_FIELDS = {
    "created":   ["$.create_date", "$.creation_date", "$.created_date"],
    "modified":  ["$.last_modified", "$.last_modified_date"],
    "expiring":  ["$.not_after"],
}

# ---------------------------------------------------------------------------
# Keyword-value patterns
# ---------------------------------------------------------------------------

_KEYWORD_VALUE_PATTERNS = [
    # (keyword_re, detail_field, value_re)
    (r"\binstance\s+class\s+(db\.\S+)",        "$.db_instance_class",    None),
    (r"\bcache\s+node\s+type\s+(cache\.\S+)",  "$.cache_node_type",      None),
    (r"\bnode\s+type\s+(cache\.\S+)",          "$.cache_node_type",      None),
    (r"\bscheduling\s+strategy\s+(REPLICA|DAEMON)", "$.scheduling_strategy", None),
    (r"\bdeployment\s+controller\s+(ECS|CODE_DEPLOY|EXTERNAL)", "$.deployment_controller_type", None),
    (r"\bstorage\s+type\s+(gp2|gp3|io1|io2|standard|aurora)", "$.storage_type", None),
    (r"\bscheme\s+(internet-facing|internal)", "$.scheme",               None),
    (r"\bwith\s+type\s+(STANDARD|EXPRESS)",    "$.type",                 None),
    (r"\bimage\s+tag\s+mutability\s+(IMMUTABLE|MUTABLE)", "$.image_tag_mutability", None),
]

# ---------------------------------------------------------------------------
# Vocabulary set for typo tolerance
# ---------------------------------------------------------------------------

_VOCAB = set()
for _svc, _types in _AWSMAP_TYPES.items():
    _VOCAB.add(_svc)
    for _w in _svc.replace("-", " ").split():
        _VOCAB.add(_w)
    for _t in _types:
        _VOCAB.add(_t)
        for _w in _t.replace("-", " ").split():
            _VOCAB.add(_w)
# Common resource words
_VOCAB |= {
    "function", "functions", "bucket", "buckets", "instance", "instances",
    "role", "roles", "user", "users", "policy", "policies", "group", "groups",
    "table", "tables", "volume", "volumes", "key", "keys", "alarm", "alarms",
    "rule", "rules", "queue", "queues", "topic", "topics", "stack", "stacks",
    "cluster", "clusters", "service", "services", "layer", "layers",
    "secret", "secrets", "certificate", "certificates", "distribution",
    "distributions", "subnet", "subnets", "security", "trail", "trails",
    "pipeline", "pipelines", "repository", "repositories",
    "lambda", "dynamodb", "cloudwatch", "cloudformation", "cloudfront",
    "cloudtrail", "elasticache", "secretsmanager", "codepipeline",
    "show", "list", "find", "count", "give", "region", "account",
    "using", "with", "without", "per", "sorted", "named",
}

# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def _normalize_service(service):
    """Fuzzy-match a service name to a canonical _AWSMAP_TYPES key."""
    if service is None:
        return None
    service = service.lower().strip().replace("_", "-").replace(" ", "-")
    if service in _AWSMAP_TYPES:
        return service
    # Fuzzy match
    matches = difflib.get_close_matches(service, _AWSMAP_TYPES.keys(), n=1, cutoff=0.6)
    if matches:
        return matches[0]
    # SequenceMatcher-scored prefix match
    best, best_score = None, 0
    for key in _AWSMAP_TYPES:
        score = difflib.SequenceMatcher(None, service, key).ratio()
        if score > best_score:
            best, best_score = key, score
    if best and best_score >= 0.5:
        return best
    return service


def _normalize_type(rtype, service):
    """Fuzzy-match a resource type name within a service's type list."""
    if rtype is None:
        return None
    rtype = rtype.lower().strip().replace("_", "-").replace(" ", "-")
    if service and service in _AWSMAP_TYPES:
        types = _AWSMAP_TYPES[service]
        # Exact match
        if rtype in types:
            return rtype
        # Fuzzy match
        matches = difflib.get_close_matches(rtype, types, n=1, cutoff=0.6)
        if matches:
            return matches[0]
        # Suffix match (e.g. "alarm" -> "metric-alarm")
        for t in types:
            if t.endswith("-" + rtype) or t.endswith(rtype):
                return t
        # Prefix match (e.g. "db-inst" -> "db-instance")
        for t in types:
            if t.startswith(rtype):
                return t
    # Search all services
    all_types = []
    for svc, tlist in _AWSMAP_TYPES.items():
        all_types.extend(tlist)
    matches = difflib.get_close_matches(rtype, all_types, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return rtype


# ---------------------------------------------------------------------------
# 7. Latest-scan WHERE clause
# ---------------------------------------------------------------------------

_LATEST_SCAN = "is_current=1"


def _scan_where(account_id=None):
    """Build the current-resources filter, optionally scoped to one account."""
    if account_id:
        return f"is_current=1 AND account_id='{account_id}'"
    return _LATEST_SCAN


# ---------------------------------------------------------------------------
# 8. Schema context builder
# ---------------------------------------------------------------------------

def build_schema_context(conn, account_id=None):
    """Query the DB for detail field names per service/type, for schema hints."""
    where = f"WHERE {_scan_where(account_id)}" if account_id else f"WHERE {_LATEST_SCAN}"
    cursor = conn.execute(
        f"SELECT DISTINCT service, type FROM resources {where} ORDER BY service, type"
    )
    pairs = cursor.fetchall()
    hints = []
    for svc, rtype in pairs:
        row = conn.execute(
            f"SELECT details FROM resources WHERE service=? AND type=? AND {_scan_where(account_id)} LIMIT 1",
            (svc, rtype)
        ).fetchone()
        if row and row[0]:
            try:
                detail = json.loads(row[0])
                if isinstance(detail, dict) and detail:
                    fields = ", ".join(sorted(detail.keys()))
                    hints.append(f"{svc}/{rtype}: {fields}")
            except (json.JSONDecodeError, TypeError):
                pass
    return "\n".join(hints) if hints else ""


# ---------------------------------------------------------------------------
# 9. _validate_intent — minimal validation and normalization
# ---------------------------------------------------------------------------

_CORE_COLUMNS = frozenset({"account_id", "region", "name", "service", "type", "is_default", "id", "tags"})
_PLACEHOLDER_RE = re.compile(r"^(YOUR_|MY_|THE_|EXAMPLE|PLACEHOLDER|SAMPLE|TEST_VALUE|<)", re.I)


def _coerce_field(field):
    """Normalize a field name: lowercase core columns, prefix unknowns with '$.'."""
    if not field:
        return field
    if field.startswith("$.") or field.startswith("tags."):
        return field
    if field.lower() in _CORE_COLUMNS:
        return field.lower()
    # Unknown bare field → treat as a detail JSON field
    return f"$.{field}"


def _normalize_intent_fields(intent):
    """Normalize field references and clean up basic intent structure."""
    # Normalize all field references (core columns → lowercase, others → $.)
    for filt in intent.get("filters", []):
        filt["field"] = _coerce_field(filt.get("field", ""))
    intent["select_fields"] = [_coerce_field(f) for f in intent.get("select_fields", [])]
    intent["group_by"] = [_coerce_field(f) for f in intent.get("group_by", [])]
    for o in intent.get("order_by", []):
        o["field"] = _coerce_field(o.get("field", ""))

    # Remove filters with placeholder/template values
    intent["filters"] = [
        f for f in intent.get("filters", [])
        if not (isinstance(f.get("value"), str) and _PLACEHOLDER_RE.match(f["value"]))
    ]

    # Clear catch-all types: "resources"/"resource" means all types
    rtype_raw = (intent.get("type") or "").lower()
    if rtype_raw.rstrip("s") == "resource":
        intent["type"] = None

    # type = service name fix (e.g. type="lambda" → service="lambda", type=None)
    if intent.get("type") and intent["type"] in _AWSMAP_TYPES:
        if not intent.get("service"):
            intent["service"] = intent["type"]
        intent["type"] = None

    # Normalize service name
    if intent.get("service"):
        intent["service"] = _normalize_service(intent["service"])

    # Normalize type name
    if intent.get("type"):
        intent["type"] = _normalize_type(intent["type"], intent.get("service"))


def _resolve_service_type_conflicts(intent):
    """Cross-validate service/type and resolve conflicts."""
    # Cross-validate service/type, fix if type belongs to a different service
    svc = intent.get("service")
    rtype = intent.get("type")
    if svc and rtype and svc in _AWSMAP_TYPES:
        if rtype not in _AWSMAP_TYPES[svc]:
            for s, tlist in _AWSMAP_TYPES.items():
                if rtype in tlist:
                    intent["service"] = s
                    break
            else:
                normalized = _normalize_type(rtype, svc)
                if normalized:
                    intent["type"] = normalized


def _infer_missing_service_type(intent, question):
    """Infer missing service/type from question text and handle group_by logic."""
    q = question.lower() if question else ""

    # Skip type inference for "all SERVICE resources" queries
    is_all_resources = re.search(r'\ball\s+[\w-]+\s+resources?\b', q) if q else False

    # Infer type from service when only one type exists
    svc = intent.get("service")
    if svc and not intent.get("type") and svc in _AWSMAP_TYPES and not is_all_resources:
        types = _AWSMAP_TYPES[svc]
        if len(types) == 1:
            intent["type"] = types[0]

    # "which regions have" / "which region" → distinct over region
    if "which region" in q and intent["action"] not in ("distinct",):
        intent["action"] = "distinct"
        if "region" not in intent.get("select_fields", []):
            intent.setdefault("select_fields", []).insert(0, "region")
        # Remove any spurious region eq filters
        intent["filters"] = [
            f for f in intent.get("filters", [])
            if not (f.get("field") == "region" and f.get("op") == "eq")
        ]

    # "which accounts have" → distinct over account_id
    if "which account" in q and intent["action"] not in ("distinct",):
        intent["action"] = "distinct"
        if "account_id" not in intent.get("select_fields", []):
            intent.setdefault("select_fields", []).insert(0, "account_id")
        intent["filters"] = [
            f for f in intent.get("filters", [])
            if not (f.get("field") == "account_id" and f.get("op") == "eq")
        ]

    # "per X" / "by X" → add group_by when missing
    # SKIP if "sorted" appears ("sorted by X" = ORDER BY, not GROUP BY)
    if intent["action"] in ("count", "list") and not intent.get("group_by") and "sorted" not in q and not intent.get("order_by"):
        per_map = [
            ("per region", "region"),
            ("per account", "account_id"),
            ("per service", "service"),
            ("per type", "type"),
        ]
        for phrase, field in per_map:
            if phrase in q:
                intent.setdefault("group_by", [])
                if field not in intent["group_by"]:
                    intent["group_by"].append(field)

    # Fix action: group_by implies count
    if intent.get("group_by") and intent["action"] not in ("count",):
        intent["action"] = "count"

    # NOTE: Filter removal for GROUP BY conflicts is handled in _extract_grouping()
    # with OR group preservation. We only handle service/type clearing here.
    if intent.get("group_by"):
        gb = set(intent["group_by"])
        # When grouping by "service", clear the implicit service/type scope
        if "service" in gb:
            intent["service"] = None
            intent["type"] = None
        # When grouping by "type", clear the implicit type scope
        if "type" in gb:
            intent["type"] = None

    # Try to recover missing type from question words (generic fuzzy match)
    svc = intent.get("service")
    # Skip type recovery for wafv2 (intentionally left None to query all ACL types)
    # Skip type recovery for "all SERVICE resources" queries
    if svc and not intent.get("type") and svc in _AWSMAP_TYPES and q and svc != "wafv2" and not is_all_resources:
        types = _AWSMAP_TYPES[svc]
        if len(types) > 1:
            q_words = set(re.findall(r"[a-z0-9]+", q))
            # Add simple plural stemming
            stemmed = {w[:-1] for w in q_words if w.endswith("s") and len(w) > 2}
            stemmed |= {w[:-2] for w in q_words if w.endswith("es") and len(w) > 3}
            q_words |= stemmed
            for t in types:
                t_words = set(t.replace("-", " ").split())
                t_bare = t.replace("-", "")
                if t in q_words or t_bare in q_words or t_words & q_words:
                    intent["type"] = t
                    break

    # Distinct with group_by but no select_fields → move group_by
    if intent["action"] == "distinct" and intent.get("group_by") and not intent.get("select_fields"):
        intent["select_fields"] = intent["group_by"]
        intent["group_by"] = []

    # Final safeguard: sorted queries should be LIST, not COUNT
    # If order_by is from "sorted by X" pattern, force action to "list"
    if q and intent.get("order_by") and "sorted" in q and not intent.get("group_by"):
        intent["action"] = "list"


def _validate_intent(intent, conn, account_id=None, question=None):
    """
    Normalize and cross-validate the parsed intent. Mutates in place.

    Orchestrates 3 specialized validation functions for clean separation of concerns.
    """
    _normalize_intent_fields(intent)
    _resolve_service_type_conflicts(intent)
    _infer_missing_service_type(intent, question)

    # Normalize filter fields against actual DB detail fields
    if conn and intent.get("service") and intent.get("type"):
        _normalize_filter_fields(intent, conn, account_id)

    return intent


def _fetch_schema_fields(conn, service, rtype, account_id):
    """Fetch and return set of detail field names for a service/type from DB."""
    try:
        row = conn.execute(
            f"SELECT details FROM resources WHERE service=? AND type=? AND {_scan_where(account_id)} LIMIT 1",
            (service, rtype)
        ).fetchone()
    except Exception:
        return set()

    if not row or not row[0]:
        return set()
    try:
        detail = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return set()
    if not isinstance(detail, dict):
        return set()

    return set(detail.keys())


def _normalize_filter_fields(intent, conn, account_id):
    """Normalize $. field references against actual DB detail fields (with caching)."""
    svc = intent.get("service")
    rtype = intent.get("type")
    if not svc or not rtype:
        return

    # Check cache first
    cache_key = (svc, rtype)
    if cache_key in _SCHEMA_CACHE:
        db_fields = _SCHEMA_CACHE[cache_key]
    else:
        # Query DB and cache result
        db_fields = _fetch_schema_fields(conn, svc, rtype, account_id)
        _SCHEMA_CACHE[cache_key] = db_fields

    if not db_fields:
        return

    def _fix_field(field_name):
        if not field_name.startswith("$."):
            return field_name
        bare = field_name[2:]
        if bare in db_fields:
            return field_name
        # Try with _ replaced by -
        alt = bare.replace("-", "_")
        if alt in db_fields:
            return "$." + alt
        alt = bare.replace("_", "-")
        if alt in db_fields:
            return "$." + alt
        # Fuzzy match
        matches = difflib.get_close_matches(bare, db_fields, n=1, cutoff=0.7)
        if matches:
            return "$." + matches[0]
        return field_name

    for f in intent.get("filters", []):
        f["field"] = _fix_field(f["field"])
    intent["select_fields"] = [_fix_field(f) for f in intent.get("select_fields", [])]
    intent["group_by"] = [_fix_field(f) for f in intent.get("group_by", [])]
    for o in intent.get("order_by", []):
        o["field"] = _fix_field(o["field"])


# ---------------------------------------------------------------------------
# 10. SQL builder
# ---------------------------------------------------------------------------

def _field_to_sql(field):
    """Convert a field notation to SQL expression."""
    if field.startswith("$."):
        return f"json_extract(details,'{field}')"
    if field.startswith("tags."):
        tag_key = field[5:]
        return f"json_extract(tags,'$.{tag_key}')"
    return field


def _field_alias(field, use_short_aliases=False):
    """Create a column alias for a field."""
    if field.startswith("$."):
        bare = field[2:]
        # Short aliases for combination queries (per X and Y combination)
        if use_short_aliases:
            short = {"runtime": "rt", "memory_size": "mem"}
            return short.get(bare, bare)
        # Standard aliases
        if bare == "cidr_block":
            return "cidr"
        return bare
    if field.startswith("tags."):
        # Return just the tag name in lowercase (e.g., "tags.Environment" → "environment")
        return field.split(".")[1].lower()
    return field


def _is_numeric(value):
    """Check if value should be treated as numeric in SQL."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    return False


def _sql_value(value):
    """Format a value for SQL, quoting strings and leaving numbers bare."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str) and _is_numeric(value):
        return str(value)
    return f"'{value.replace(chr(39), chr(39)*2)}'"


def _build_filter_clause(f):
    """Build a single WHERE clause from a filter dict."""
    field = f["field"]
    op = f["op"]
    value = f.get("value")
    value2 = f.get("value2")
    sql_field = _field_to_sql(field)

    if op == "eq":
        return f"{sql_field}={_sql_value(value)}"
    elif op == "ne":
        # For json_extract fields, need NULL-safe comparison
        if field.startswith("$.") or field.startswith("tags."):
            return f"({sql_field} IS NULL OR {sql_field}!={_sql_value(value)})"
        return f"{sql_field}!={_sql_value(value)}"
    elif op == "gt":
        return f"{sql_field}>{_sql_value(value)}"
    elif op == "lt":
        return f"{sql_field}<{_sql_value(value)}"
    elif op == "gte":
        return f"{sql_field}>={_sql_value(value)}"
    elif op == "lte":
        return f"{sql_field}<={_sql_value(value)}"
    elif op == "like":
        return f"{sql_field} LIKE '{value}'"
    elif op == "not_like":
        # For json_extract fields, NULL means no data - exclude from "without X" queries
        # Only match explicit values that don't contain the pattern
        if field.startswith("$.") or field.startswith("tags."):
            return f"({sql_field} IS NOT NULL AND {sql_field} NOT LIKE '{value}')"
        return f"{sql_field} NOT LIKE '{value}'"
    elif op == "between":
        v1 = value
        v2 = value2
        if isinstance(value, list) and len(value) >= 2:
            v1, v2 = value[0], value[1]
        return f"{sql_field} BETWEEN {_sql_value(v1)} AND {_sql_value(v2)}"
    elif op == "is_null":
        return f"{sql_field} IS NULL"
    elif op == "is_null_or_false":
        # For encryption fields: check both NULL and 0/false values
        return f"({sql_field} IS NULL OR {sql_field}=0 OR {sql_field}='false')"
    elif op == "is_not_null":
        return f"{sql_field} IS NOT NULL"
    elif op == "is_empty":
        # For tags field (check both "tags" and "$.tags"), use tags column directly
        if field == "tags" or field == "$.tags":
            return f"(tags IS NULL OR tags='{{}}' OR tags='null')"
        # For JSON detail fields, also check for empty array '[]'
        if field.startswith("$."):
            return f"({sql_field} IS NULL OR {sql_field}='' OR {sql_field}='[]')"
        return f"({sql_field} IS NULL OR {sql_field}='')"
    else:
        return f"{sql_field}={_sql_value(value)}"


def build_sql(intent, account_id=None):
    """
    Build a SQL query from a validated intent dict.

    Supports generic relationship expansion for inheritable fields via
    _RESOURCE_RELATIONSHIPS metadata. Currently used for IAM user/group relationships.
    """
    scan = _scan_where(account_id)

    where_clauses = []

    # Service/type filters
    # Handle multi-service queries: "count Lambda and S3 per region"
    if "_multi_service_types" in intent:
        # Build OR clause for multiple service/type pairs
        svc_type_clauses = []
        for svc, typ in intent["_multi_service_types"]:
            svc_type_clauses.append(f"(service='{svc}' AND type='{typ}')")
        where_clauses.append(f"({' OR '.join(svc_type_clauses)})")
    else:
        # Single service/type (standard case)
        service = intent.get("service")
        rtype = intent.get("type")
        if service:
            where_clauses.append(f"service='{service}'")
        if rtype:
            where_clauses.append(f"type='{rtype}'")

    # Build filters with AND/OR logic
    filters = intent.get("filters", [])
    if filters:
        # Split into AND and OR groups
        and_parts = []
        or_groups = []
        current_or = []

        for f in filters:
            logic = f.get("logic", "and")
            clause = _build_filter_clause(f)

            if logic == "or":
                if and_parts and not current_or:
                    # Start OR group with the last AND part
                    current_or.append(and_parts.pop())
                current_or.append(clause)
            else:
                if current_or:
                    # Close previous OR group
                    or_groups.append(current_or)
                    current_or = []
                and_parts.append(clause)

        if current_or:
            or_groups.append(current_or)

        # ═══════════════════════════════════════════════════════════════════════════
        # Generic relationship handling framework
        # ═══════════════════════════════════════════════════════════════════════════
        #
        # Expands filters on inheritable fields to check related resources.
        # This framework uses _RESOURCE_RELATIONSHIPS metadata to define parent-child
        # relationships where child resources inherit properties from parents.
        #
        # How it works:
        #   - When filtering on an "inheritable" field (like $.attached_policies),
        #     the query is expanded to also check related resources (like groups)
        #   - Uses EXISTS subqueries to check if the property exists in related resources
        #   - Supports both positive ("has X") and negative ("doesn't have X") checks
        #
        # Current usage:
        #   - IAM users inherit policies from their groups (see _RESOURCE_RELATIONSHIPS)
        #   - Query: "IAM users with admin policies" checks both direct user policies
        #     and policies attached to groups the user belongs to
        #
        # How to extend:
        #   Add entries to _RESOURCE_RELATIONSHIPS dict (defined earlier in file):
        #   ```python
        #   _RESOURCE_RELATIONSHIPS = {
        #       ("service", "parent_type"): [{
        #           "related_service": "service",
        #           "related_type": "child_type",
        #           "related_field": "$.field_linking_parent_to_child",
        #           "inherit_checks": ["$.inheritable_field1", "$.inheritable_field2"]
        #       }]
        #   }
        #   ```
        #
        # Example:
        #   EC2 instances could inherit tags from their parent Auto Scaling Group
        #   by adding an entry for ("autoscaling", "auto-scaling-group")
        #
        # ═══════════════════════════════════════════════════════════════════════════
        relationships = _RESOURCE_RELATIONSHIPS.get((service, rtype), [])
        if relationships:
            expanded_parts = []
            for part in and_parts:
                expanded = False
                for rel in relationships:
                    for inherit_field in rel["inherit_checks"]:
                        if inherit_field in part:
                            # This filter checks an inheritable field - expand to include related resources
                            related_field = rel["related_field"]
                            related_svc = rel["related_service"]
                            related_type = rel["related_type"]

                            # Determine if this is a positive (LIKE) or negative (NOT LIKE) check
                            is_negative = " NOT LIKE " in part or " IS NOT NULL AND " in part

                            # For negative checks, we need to build the positive condition and wrap in NOT
                            # Extract the actual LIKE condition from the filter
                            if is_negative:
                                # Find the value being checked (e.g., '%AdministratorAccess%')
                                # Part is like: "(field IS NOT NULL AND field NOT LIKE 'value')"
                                value_match = re.search(r"LIKE '([^']+)'", part)
                                if value_match:
                                    value = value_match.group(1)
                                    field_sql = f"json_extract(details,'{inherit_field}')"

                                    # Build positive checks for both direct and related
                                    direct_positive = f"{field_sql} LIKE '{value}'"
                                    related_positive = f"json_extract(g.details,'{inherit_field}') LIKE '{value}'"

                                    exists_clause = (
                                        f"EXISTS ("
                                        f"SELECT 1 FROM resources g "
                                        f"WHERE g.service='{related_svc}' AND g.type='{related_type}' "
                                        f"AND g.account_id=resources.account_id "
                                        f"AND json_extract(resources.details,'{related_field}') LIKE '%'||g.name||'%' "
                                        f"AND {related_positive}"
                                        f")"
                                    )

                                    # Negative: NOT (has in direct OR has in related)
                                    expanded_parts.append(f"NOT ({direct_positive} OR {exists_clause})")
                                else:
                                    expanded_parts.append(part)
                            else:
                                # Positive: has in direct OR has in related
                                related_check = part.replace('json_extract(details,', 'json_extract(g.details,')
                                exists_clause = (
                                    f"EXISTS ("
                                    f"SELECT 1 FROM resources g "
                                    f"WHERE g.service='{related_svc}' AND g.type='{related_type}' "
                                    f"AND g.account_id=resources.account_id "
                                    f"AND json_extract(resources.details,'{related_field}') LIKE '%'||g.name||'%' "
                                    f"AND {related_check}"
                                    f")"
                                )
                                expanded_parts.append(f"({part} OR {exists_clause})")

                            expanded = True
                            break
                    if expanded:
                        break

                if not expanded:
                    expanded_parts.append(part)

            and_parts = expanded_parts

        # Add AND parts
        where_clauses.extend(and_parts)

        # Add OR groups (each wrapped in parentheses)
        for group in or_groups:
            where_clauses.append(f"({' OR '.join(group)})")

    # Always add latest scan
    where_clauses.append(scan)

    # Add custom filters (e.g., tag count)
    if "_custom_filters" in intent:
        for cf in intent["_custom_filters"]:
            if cf["type"] == "tag_count_gte":
                # SQLite JSON key count: count keys in tags object
                where_clauses.append(
                    f"json_type(tags)='object' AND "
                    f"(SELECT COUNT(*) FROM json_each(tags))>={cf['value']}"
                )

    # IAM roles that trust external accounts
    if "_trust_external_accounts" in intent:
        # Check if trust_policy contains AWS principal with external account ARNs
        # Trust policy format: {"Principal":{"AWS":"arn:aws:iam::ACCOUNT_ID:root"}}
        # Strategy: Replace :iam::OWN_ACCOUNT: pattern, then check if :iam:: still exists
        # This correctly handles self-trust vs external-trust distinction
        where_clauses.append(
            "json_extract(details,'$.trust_policy') IS NOT NULL "
            "AND json_extract(details,'$.trust_policy') LIKE '%\"AWS\"%' "
            "AND json_extract(details,'$.trust_policy') LIKE '%:iam::%' "
            "AND REPLACE(json_extract(details,'$.trust_policy'), ':iam::' || account_id || ':', ':REMOVED:') LIKE '%:iam::%'"
        )

    # Add relationship filter (NOT EXISTS for "X without any Y")
    if "_relationship_filter" in intent:
        rel = intent["_relationship_filter"]
        if rel["type"] == "not_exists":
            child_svc = rel["child_service"]
            child_type = rel["child_type"]
            parent_svc = intent.get("service", "")
            parent_type = intent.get("type", "")

            # Generic link field: try common patterns
            # Pattern: child has $.{parent_type}_id or $.{parent_svc}_id
            link_fields = [
                f"$.{parent_type}_id",
                f"$.{parent_svc}_id",
                f"$.{parent_type.replace('-', '_')}_id",
            ]

            # Try each link field with OR (at least one should match)
            link_conditions = " OR ".join(
                f"json_extract(child.details,'{lf}')=resources.id" for lf in link_fields
            )

            not_exists_clause = (
                f"NOT EXISTS ("
                f"SELECT 1 FROM resources child "
                f"WHERE child.service='{child_svc}' "
                f"AND child.type='{child_type}' "
                f"AND child.account_id=resources.account_id "
                f"AND ({link_conditions})"
                f")"
            )
            where_clauses.append(not_exists_clause)

    where = " AND ".join(where_clauses)

    # Determine action
    action = intent.get("action", "list")
    group_by = intent.get("group_by", [])
    select_fields = intent.get("select_fields", [])
    order_by = intent.get("order_by", [])
    limit = intent.get("limit")

    # Build SELECT
    if action == "distinct":
        if select_fields:
            dist_fields = ", ".join(_field_to_sql(f) for f in select_fields)
            select = f"SELECT DISTINCT {dist_fields}"
        else:
            select = "SELECT DISTINCT account_id, name, region"
    elif group_by:
        use_short = intent.get("_combination_query", False)
        group_exprs = []
        for gf in group_by:
            sql_f = _field_to_sql(gf)
            alias = _field_alias(gf, use_short_aliases=use_short)
            if gf.startswith("$.") or gf.startswith("tags."):
                group_exprs.append(f"{sql_f} AS {alias}")
            else:
                group_exprs.append(sql_f)
        group_exprs_str = ", ".join(group_exprs)
        select = f"SELECT {group_exprs_str}, COUNT(*) AS count"
    elif action == "count":
        select = "SELECT COUNT(*) AS count"
    else:
        # List action
        cols = ["account_id", "name", "region"]

        # Organizations accounts: use id column (actual account ID) instead of account_id (management account)
        if service == "organizations" and rtype == "account":
            cols = ["id AS account_id", "name", "region"]

        # Check for "all global resources" pattern: add service, type to SELECT
        is_global_all = (
            not service and not rtype
            and any(
                f.get("field") == "region" and f.get("op") == "eq" and f.get("value") == "global"
                for f in filters
            )
        )
        if is_global_all:
            cols = ["account_id", "name", "service", "type"]

        # Check for "all SERVICE resources" pattern: add type to SELECT
        # E.g., "show me all vpc resources" → SELECT account_id, name, region, type
        if service and not rtype:
            cols.append("type")

        # Check for "Name tag" pattern: replace name with tags.Name
        has_name_tag_select = "tags.Name" in select_fields
        if has_name_tag_select:
            # Replace name column with the tag value
            cols = ["account_id", f"json_extract(tags,'$.Name') AS name_tag", "region"]
            select_fields = [f for f in select_fields if f != "tags.Name"]

        # Add extra select fields
        for sf in select_fields:
            sql_f = _field_to_sql(sf)
            alias = _field_alias(sf)
            if sf.startswith("$.") or sf.startswith("tags."):
                cols.append(f"{sql_f} AS {alias}")
            else:
                if sf not in cols:
                    cols.append(sf)

        select = f"SELECT {', '.join(cols)}"

    sql = f"{select} FROM resources WHERE {where}"

    # GROUP BY
    if group_by:
        use_short = intent.get("_combination_query", False)
        group_sql = ", ".join(
            _field_alias(gf, use_short_aliases=use_short) if (gf.startswith("$.") or gf.startswith("tags.")) else gf
            for gf in group_by
        )
        sql += f" GROUP BY {group_sql}"

    # ORDER BY
    if order_by:
        order_parts = []
        for o in order_by:
            sql_f = _field_to_sql(o["field"])
            direction = o.get("direction", "asc").upper()
            order_parts.append(f"{sql_f} {direction}")
        sql += f" ORDER BY {', '.join(order_parts)}"
    elif group_by:
        sql += " ORDER BY count DESC"

    # LIMIT
    if limit:
        sql += f" LIMIT {limit}"

    return sql


# ---------------------------------------------------------------------------
# 11. Built-in NL parser — zero-dependency, works without any LLM
# ---------------------------------------------------------------------------

# AWS region regex (covers all current regions including gov/cn/ap/me/af/il)
_REGION_RE = re.compile(
    r'\b(us-east-\d|us-west-\d|eu-west-\d|eu-central-\d|eu-north-\d|eu-south-\d'
    r'|ap-northeast-\d|ap-southeast-\d|ap-south-\d|ap-east-\d'
    r'|ca-central-\d|ca-west-\d|sa-east-\d|me-south-\d|me-central-\d'
    r'|af-south-\d|il-central-\d|us-gov-east-\d|us-gov-west-\d'
    r'|cn-north-\d|cn-northwest-\d|global)\b'
)

# Semantic keyword → filter mapping (pure DATA, no service-specific logic)
_KW_FILTERS: dict[str, dict] = {
    "non-default":          {"field": "$.is_default", "op": "eq", "value": 0},
    "default":              {"field": "$.is_default", "op": "eq", "value": 1},
    "public":               {"field": "$.public_access_blocked", "op": "eq", "value": 0},
    "private":              {"field": "$.public_access_blocked", "op": "eq", "value": 1},
    "fifo":                 {"field": "$.fifo_queue", "op": "eq", "value": 1},
    "multi-az":             {"field": "$.multi_az", "op": "eq", "value": 1},
    "private zone":         {"field": "$.private_zone", "op": "eq", "value": 1},
    "versioning enabled":   {"field": "$.versioning", "op": "eq", "value": "Enabled"},
    "without versioning":   {"field": "$.versioning", "op": "ne", "value": "Enabled"},
    "no encryption":        {"field": "$.encryption", "op": "is_null"},
    "with no encryption":   {"field": "$.encryption", "op": "is_null"},
    "no vpc":               {"field": "$.vpc_id", "op": "is_null"},
    "no vpc configuration": {"field": "$.vpc_id", "op": "is_null"},
    "without environment":  {"field": "$.environment", "op": "is_empty"},
    "with environment":     {"field": "$.environment", "op": "is_not_null"},
    "no dead letter":       {"field": "$.dead_letter_config", "op": "is_null"},
    "with no dead letter":  {"field": "$.dead_letter_config", "op": "is_null"},
    "without dead letter":  {"field": "$.dead_letter_config", "op": "is_null"},
    "with dead letter":     {"field": "$.dead_letter_config", "op": "is_not_null"},
    "without reserved concurrency": {"field": "$.reserved_concurrency", "op": "is_null"},
    "with reserved concurrency":    {"field": "$.reserved_concurrency", "op": "is_not_null"},
    "without lifecycle":    {"field": "$.lifecycle_rules", "op": "is_null"},
    "with lifecycle":       {"field": "$.lifecycle_rules", "op": "is_not_null"},
    "without tags":         {"field": "tags", "op": "is_empty"},
    "no tags":              {"field": "tags", "op": "is_empty"},
    "with tags":            {"field": "tags", "op": "is_not_null"},
    "admin":                {"field": "$.attached_policies", "op": "like", "value": "%AdministratorAccess%"},
    "without admin":        {"field": "$.attached_policies", "op": "not_like", "value": "%AdministratorAccess%"},
    "not using python":     {"field": "$.runtime", "op": "not_like", "value": "python%"},
    "that are enabled":     {"field": "$.enabled", "op": "eq", "value": 1},
    "that are not enabled": {"field": "$.enabled", "op": "ne", "value": 1},
    "not enabled":          {"field": "$.enabled", "op": "ne", "value": 1},
    "that are disabled":    {"field": "$.enabled", "op": "is_null_or_false"},
    "are disabled":         {"field": "$.enabled", "op": "is_null_or_false"},
    "disabled":             {"field": "$.enabled", "op": "is_null_or_false"},
    "with aes256 encryption": {"field": "$.encryption", "op": "like", "value": "%AES256%"},
    "with encryption":      {"field": "$.encryption", "op": "is_not_null"},
    "without encryption":   {"field": "$.encryption", "op": "is_null_or_false"},
    "empty description":    {"field": "$.description", "op": "is_empty"},
    "no description":       {"field": "$.description", "op": "is_empty"},
    "with description":     {"field": "$.description", "op": "is_not_null"},
    "not in any groups":    {"field": "$.groups", "op": "is_empty"},
    "not attached":         {"field": "$.attachment_count", "op": "eq", "value": 0},
    "without mfa delete":   {"field": "$.mfa_delete", "op": "is_null_or_false"},
    "without object lock":  {"field": "$.object_lock_enabled", "op": "is_null_or_false"},
    "without detailed monitoring": {"field": "$.monitoring_state", "op": "ne", "value": "enabled"},
    "without point-in-time recovery": {"field": "$.point_in_time_recovery_enabled", "op": "is_null_or_false"},
    "with x-ray tracing disabled": {"field": "$.tracing_config", "op": "is_null"},
    "x-ray tracing disabled": {"field": "$.tracing_config", "op": "is_null"},
    # Note: "unattached" and "unused" are context-dependent (handled below in _builtin_parse)
}


def _q_words(question: str):
    """Return a set of lowercase words from the question, with plural stemming and typo correction."""
    # Split camelCase but preserve all-caps acronyms (EC2, RDS, S3, etc.)
    q = re.sub(r'([a-z])([A-Z])', r'\1 \2', question)  # split at lowercase→uppercase
    raw = set(re.findall(r'[a-z][a-z0-9]*', q.lower()))
    stemmed = {w[:-1] for w in raw if w.endswith("s") and len(w) > 3}
    stemmed |= {w[:-2] for w in raw if w.endswith("es") and len(w) > 4}
    result = raw | stemmed
    # Typo tolerance: for words ≥4 chars not in _VOCAB, try fuzzy match
    corrections = set()
    for w in raw:
        if len(w) >= 4 and w not in _VOCAB:
            matches = difflib.get_close_matches(w, _VOCAB, n=1, cutoff=0.8)
            if matches:
                corrections.add(matches[0])
    # Also stem corrections
    corr_stemmed = {w[:-1] for w in corrections if w.endswith("s") and len(w) > 3}
    corr_stemmed |= {w[:-2] for w in corrections if w.endswith("es") and len(w) > 4}
    return result | corrections | corr_stemmed


def _has_word_or_compound(qw: set, target: str) -> bool:
    """Check if target word/phrase exists in qw, handling compound words.

    Examples:
        - qw={"cloud", "watch"}, target="cloudwatch" → True (compound)
        - qw={"alarm"}, target="alarm" → True (exact)
        - qw={"apigateway"}, target="apigateway" → True (exact)
        - qw={"timestream", "influxdb"}, target="timestream-influxdb" → True (hyphenated compound)
    """
    # Direct match (with or without hyphens)
    if target in qw or target.replace("-", "") in qw:
        return True

    # Compound word match: check if any two words in qw can form target (with or without hyphens)
    target_no_hyphen = target.replace("-", "")
    for word1 in qw:
        for word2 in qw:
            if word1 != word2 and word1 + word2 == target_no_hyphen:
                return True

    return False


def _score_svc_type(qw: set, svc: str, types: list) -> tuple[int, str | None]:
    """Return (score, best_type) for a service+type pair against question words."""
    # Service words (with stemming to handle "events"→"event", "logs"→"log")
    sw_raw = set(re.findall(r"[a-z0-9]+", svc))
    sw = sw_raw | {w[:-1] for w in sw_raw if w.endswith("s") and len(w) > 3}
    svc_score = len(sw & qw) * 3

    # Exact service name match gets massive boost (e.g., "vpc" in question → vpc service)
    if svc in qw or svc.replace("-", "") in qw:
        svc_score += 15

    # Check if service is a compound word where parts can be found in query
    # E.g., "cloudwatch" can be formed from "cloud" + "watch" both in qw
    for word1 in qw:
        for word2 in qw:
            if word1 != word2 and word1 + word2 == svc:
                svc_score += 12  # Good boost for compound word match
                break

    # Penalize services with generic names when question uses those words generically
    generic_words = {"resource", "explorer", "network"}
    svc_words = set(svc.split("-"))
    if (svc_words & generic_words) and not any(w for w in qw if w in svc_words and w not in generic_words):
        svc_score = max(1, svc_score - 8)

    # Prefer shorter service names (less generic): penalty for long service names
    if len(svc) > 18:
        svc_score -= 1

    best_type, best_ts = None, 0
    for t in types:
        t_bare = t.replace("-", "")
        t_words = set(t.replace("-", " ").split())

        # PRIORITY 1: All type words present in query (composite-alarm, route-table, etc.)
        # Prefer types with MORE words for specificity (route-table > vpc)
        if t_words and t_words.issubset(qw):
            ts = 5 + len(t_words)  # Base score + bonus for more words
        # PRIORITY 2: Exact type match (with or without hyphens)
        elif t in qw or t_bare in qw:
            ts = 3
        # PRIORITY 3: Partial word match
        elif t_words & qw:
            ts = len(t_words & qw) * 2
        else:
            ts = 0
        if ts > best_ts:
            best_type, best_ts = t, ts

    return svc_score + best_ts, best_type


# ============================================================================
# INTENT EXTRACTORS - Focused functions for parsing different query aspects
# ============================================================================

def _detect_action(q: str, qw: set, intent: dict) -> None:
    """Detect query action: count, distinct, or list."""
    # Use word boundary for "count" to avoid matching "account"
    count_trigger = any(kw in q for kw in ("how many", "total number")) or re.search(r'\bcount\b', q)

    # "number of" triggers COUNT unless preceded by "show/list/give/find"
    # "show me X with number of nodes > 4" → LIST (has "show" before "number of")
    # "number of Lambda functions" → COUNT (asking for count)
    if "number of" in q and not count_trigger:
        # Check if this is a LIST query with numeric filter or a COUNT query
        if any(re.search(rf'\b{word}\b.*number of', q) for word in ("show", "list", "give", "find")):
            # List action with numeric filter - don't trigger count
            count_trigger = False
        else:
            # Asking for a count - trigger count
            count_trigger = True

    # If "count" appears but query starts with show/list/give/find, it's a LIST query
    # "show me subnets with available IP count > 100" → LIST (not COUNT)
    # Check for both "show" and "show me" patterns
    if count_trigger:
        list_starts = ("show ", "show me ", "list ", "give ", "give me ", "find ")
        if any(q.startswith(word) for word in list_starts):
            count_trigger = False

    if count_trigger:
        intent["action"] = "count"

    # Override count if "and show them" / "and list them" is present
    # "how many X and show them" → list (user wants to see the items, not just count)
    if intent.get("action") == "count" and any(p in q for p in ("and show", "and list", "show them", "list them")):
        intent["action"] = "list"

    # "have the most" / "has the most" → GROUP BY + ORDER BY DESC
    # Plural "have" + "the most" = LIMIT 1 (which regions have THE most)
    # Singular "has" = no LIMIT (which service has the most resources)
    if "have the most" in q or "has the most" in q:
        intent["action"] = "count"
        # Detect what field to group by
        if "region" in qw:
            intent["group_by"].append("region")
        elif "account" in qw:
            intent["group_by"].append("account_id")
        elif "service" in qw:
            intent["group_by"].append("service")
        # Add LIMIT 1 ONLY for plural "have the most" (not "has the most")
        if "have the most" in q:
            intent["limit"] = 1
    elif "which region" in q and "most" not in q:
        intent["action"] = "distinct"
        intent["select_fields"].append("region")
    elif "which account" in q and "most" not in q:
        intent["action"] = "distinct"
        intent["select_fields"].append("account_id")
    elif "which service" in q and "most" not in q:
        intent["action"] = "distinct"
        intent["select_fields"].append("service")


def _detect_service_type(q: str, qw: set, intent: dict) -> None:
    """Detect service and type using scored matching against _AWSMAP_TYPES."""
    # Skip service detection for generic "resources" queries (without service qualifier)
    # But allow "EC2 resources", "Lambda resources", etc. to continue
    if "resource" in qw and not any(s in qw for s in ("ram", "explorer", "compute", "optimizer")):
        # Check if there's a service qualifier (e.g., "EC2 resources", "Lambda resources")
        # Handle hyphenated service names by checking component words
        has_service_qualifier = any(
            svc in qw or svc.replace("-", "") in qw or _has_word_or_compound(qw, svc)
            for svc in _AWSMAP_TYPES.keys()
        )
        if not has_service_qualifier:
            # Generic resource query - leave service/type as None
            return

    # Filter out words that appear after name-search keywords to avoid confusion
    # E.g., "S3 buckets with name containing logs" should not detect service='logs'
    filtered_qw = qw.copy()
    for pattern in (r'containing\s+(\w+)', r'named\s+(\w+)', r'with\s+name\s+containing\s+(\w+)'):
        for m in re.finditer(pattern, q):
            word = m.group(1).lower()
            filtered_qw.discard(word)

    # Filter out "global" when it's part of a region filter pattern
    # E.g., "DynamoDB tables not in global" should not detect type='global-table'
    if re.search(r'\b(?:not\s+in|outside|except)\s+global\b', q):
        filtered_qw.discard("global")

    # Filter out generic descriptor words that shouldn't match service/type names
    # E.g., "users with admin permissions" - "permissions" shouldn't match acm-pca/permission
    generic_descriptors = {"permission", "permissions", "access", "policy", "policies"}
    if any(word in q for word in ("with admin", "without admin", "admin permission", "admin access")):
        filtered_qw -= generic_descriptors

    # Filter out "account" when it's part of "per account" GROUP BY pattern
    # E.g., "count subnets per account" should detect subnets, not organizations/account
    if " per account" in q or " by account" in q:
        filtered_qw.discard("account")

    # Detect "all SERVICE resources" pattern - clear type to show all resource types for that service
    # E.g., "show me all vpc resources" → service='vpc', type=None
    all_svc_resources = re.search(r'\ball\s+(\w+)\s+resources?\b', q)
    if all_svc_resources:
        svc_word = all_svc_resources.group(1)
        if svc_word in _AWSMAP_TYPES or svc_word.replace("-", "") in _AWSMAP_TYPES:
            # Will be handled later to clear type after service detection
            pass

    # Filter out type words that appear in filter context after "with"
    # E.g., "ECS clusters with active services > 0" → detect "cluster", ignore "services"
    # Pattern: "show X with Y" where Y describes a filter, not a resource type
    with_filter_match = re.search(r'\bwith\s+(?:active\s+)?(\w+)\s+(?:greater|less|count|equal)', q)
    if with_filter_match:
        filter_word = with_filter_match.group(1)
        # Remove plural form too
        filtered_qw.discard(filter_word)
        if filter_word.endswith('s'):
            filtered_qw.discard(filter_word[:-1])

    # ── Synonym/alias matching (before generic scoring) ──────────────────
    # Only fires when no explicit service name is present in the question
    has_explicit_service = any(
        svc in qw or svc.replace("-", "") in qw or _has_word_or_compound(qw, svc)
        for svc in _AWSMAP_TYPES.keys()
    )
    synonym_matched = False
    if not has_explicit_service:
        for phrase, syn_svc, syn_type in _SYNONYMS:
            if phrase in q:
                intent["service"] = syn_svc
                intent["type"] = syn_type
                synonym_matched = True
                break

    # ── EARLY FORCED DETECTIONS (before generic scoring) ──────────────────

    # CloudWatch alarms/dashboards - must detect early to avoid "Lambda" in "AWS/Lambda namespace"
    # Use _force_service_type flag to prevent generic scoring from overriding
    force_service = synonym_matched
    if (_has_word_or_compound(qw, "cloudwatch") or "cw" in qw) and ("alarm" in qw or "alarms" in qw):
        intent["service"] = "cloudwatch"
        intent["type"] = "metric-alarm"
        force_service = True
    elif (_has_word_or_compound(qw, "cloudwatch") or "cw" in qw) and ("dashboard" in qw or "dashboards" in qw):
        intent["service"] = "cloudwatch"
        intent["type"] = "dashboard"
        force_service = True

    # Generic service/type scoring (skip if forced above)
    if not force_service:
        best_svc, best_type, best_score = None, None, 0
        for svc, types in _AWSMAP_TYPES.items():
            score, btype = _score_svc_type(filtered_qw, svc, types)
            if score > best_score:
                best_score, best_svc, best_type = score, svc, btype
        if best_score >= 2:
            intent["service"] = best_svc
            intent["type"] = best_type

    # ── Force IAM service for admin/user queries ──────────────────────────
    # "users with admin" or "admin users" should always be IAM users
    if ("user" in qw or "users" in qw) and ("admin" in qw or "administrator" in qw):
        intent["service"] = "iam"
        intent["type"] = "user"

    # ── Force IAM role for trust-related queries ──────────────────────────
    # "which account is trusted" or "what trusts X" should be IAM role queries
    if any(word in qw for word in ("trusted", "trust", "trusts")):
        # Only force if asking about external/other accounts or if service is ambiguous
        if any(word in qw for word in ("external", "other", "which", "what")):
            intent["service"] = "iam"
            intent["type"] = "role"

    # ── Force EC2 service for elastic IP queries ──────────────────────────
    # "count unused elastic IPs per account" should be EC2, not organizations
    if ("elastic" in qw and "ip" in qw) or "eip" in qw:
        intent["service"] = "ec2"
        intent["type"] = "elastic-ip"

    # ── Force logs service for log group queries ──────────────────────────
    # "CloudWatch log groups" should be logs service, not cloudwatch
    if ("log" in qw or "logs" in qw) and "group" in qw:
        intent["service"] = "logs"
        intent["type"] = "log-group"

    # ── Force specific service/type for commonly misdetected resources ────

    # API Gateway v2
    if ("api" in qw or "apigateway" in qw) and ("v2" in qw or "domain" in qw):
        intent["service"] = "apigatewayv2"
        if "domain" in qw:
            intent["type"] = "domain-name"

    # Compute Optimizer
    if "compute" in qw and "optimizer" in qw:
        intent["service"] = "compute-optimizer"

    # Route53 domains
    # "Route53 registered domains" → route53 service (no type)
    # "Route53 domains" with other context → route53domains service
    if "route53" in qw and "domain" in qw:
        if "registered" in qw:
            # "registered domains" queries all route53 resources
            intent["service"] = "route53"
            intent["type"] = None
        else:
            intent["service"] = "route53domains"
            intent["type"] = "domain"
        if "recommendation" in qw or "recommendations" in qw:
            intent["type"] = "lambda-recommendation"

    # QuickSight - force type when missing (handle compound word: Quick + Sight)
    if _has_word_or_compound(qw, "quicksight"):
        intent["service"] = "quicksight"
        if "analysis" in qw or "analyses" in qw:
            intent["type"] = "analysis"
        elif "dataset" in qw or "datasets" in qw:
            intent["type"] = "dataset"
        elif "data" in qw and "source" in qw:
            intent["type"] = "data-source"
        # Default to analysis if no specific type mentioned (unless "all resources" query)
        elif not intent.get("type") and "resource" not in qw:
            intent["type"] = "analysis"

    # Resource Explorer
    if "resource" in qw and "explorer" in qw:
        intent["service"] = "resource-explorer-2"
        if "index" in qw or "indexes" in qw:
            intent["type"] = "index"

    # CloudFront origin access identities/controls
    if "cloudfront" in qw or intent.get("service") == "cloudfront":
        if "origin" in qw and "access" in qw:
            if "identity" in qw or "identities" in qw:
                intent["type"] = "origin-access-identity"
            elif "control" in qw:
                intent["type"] = "origin-access-control"

    # Organizations - distinguish policy/root/organization/ou/account
    if "organizations" in qw or intent.get("service") == "organizations":
        if "account" in qw or "accounts" in qw:
            intent["type"] = "account"
        elif "policy" in qw or "policies" in qw:
            intent["type"] = "policy"
        elif "root" in qw or "roots" in qw:
            intent["type"] = "root"
        elif "organizational" in qw and "unit" in qw:
            intent["type"] = "organizational-unit"
        elif "organization" in qw and "policy" not in qw and "root" not in qw and "account" not in qw and "resource" not in qw:
            intent["type"] = "organization"

    # Security groups - force EC2, not network-firewall!
    if ("security" in qw and "group" in qw) or "sg" in qw:
        intent["service"] = "ec2"
        intent["type"] = "security-group"

    # ── Fix type confusion in "X without Y" patterns ──────────────────────
    # "VPCs without subnets" should query VPCs, not subnets
    # "subnets without route tables" should query subnets, not route tables
    if "without" in q:
        without_idx = q.index("without")
        before_without = q[:without_idx].lower()
        # Re-score only with words before "without"
        qw_before = _q_words(before_without)
        if intent.get("service") and qw_before:
            # Re-score with only words before "without"
            svc = intent["service"]
            if svc in _AWSMAP_TYPES:
                types = _AWSMAP_TYPES[svc]
                best_type_before, best_ts = None, 0
                for t in types:
                    t_bare = t.replace("-", "")
                    t_words = set(t.replace("-", " ").split())
                    if t in qw_before or t_bare in qw_before:
                        ts = 3
                    elif t_words & qw_before:
                        ts = len(t_words & qw_before) * 2
                    else:
                        ts = 0
                    if ts > best_ts:
                        best_type_before, best_ts = t, ts
                # If we found a type before "without", use it
                if best_type_before and best_ts > 0:
                    intent["type"] = best_type_before

    # ── "all global resources" → clear service/type, add region=global ───────
    # Skip if "not in global" (negation will be handled in step 4)
    if "global" in qw and "resource" in qw and "not" not in q[:q.find("global") if "global" in q else 0]:
        intent["service"] = None
        intent["type"] = None
        intent["filters"].append({"field": "region", "op": "eq", "value": "global"})

    # ── Apply generic service/type patterns from metadata ────────────────

    # Apply type priority disambiguation for current service
    # Use filtered_qw to respect filter context (e.g., "clusters with active services")
    if intent.get("service") in _TYPE_PRIORITY:
        best_type, best_priority = None, 0
        for keywords, type_name, priority in _TYPE_PRIORITY[intent["service"]]:
            if any(kw in filtered_qw or any(w.startswith(kw) for w in filtered_qw) for kw in keywords):
                if priority > best_priority:
                    best_type, best_priority = type_name, priority
        if best_type:
            intent["type"] = best_type

    # Apply multi-word type patterns
    for keywords, svc, typ, constraints in _SERVICE_PATTERNS["multi_word_types"]:
        if all(kw in qw or any(w.startswith(kw) for w in qw) for kw in keywords):
            if svc:
                intent["service"] = svc
            if typ:
                intent["type"] = typ
            if constraints.get("remove_name_filter"):
                intent["filters"] = [f for f in intent.get("filters", []) if f.get("field") != "name"]

    # Apply service aliases
    for keywords, svc, typ, _ in _SERVICE_PATTERNS["service_aliases"]:
        if all(kw in qw for kw in keywords):
            intent["service"] = svc
            if typ:
                intent["type"] = typ

    # Apply query-all-types patterns (remove type constraint)
    for keywords, svc, _, _ in _SERVICE_PATTERNS["query_all_types"]:
        if all(kw in qw for kw in keywords):
            intent["service"] = svc
            intent["type"] = None

    # Apply service corrections
    for keywords, svc, typ, constraints in _SERVICE_PATTERNS["service_corrections"]:
        if all(kw in qw for kw in keywords):
            # Skip "vpc subnet" correction if "without" is in question (VPCs without subnets)
            if keywords == ["vpc", "subnet"] and "without" in q:
                continue
            # Check if constraint matches
            if "if_service" in constraints and intent.get("service") != constraints["if_service"]:
                continue
            if "if_type" in constraints and intent.get("type") != constraints["if_type"]:
                continue
            intent["service"] = svc
            if typ:
                intent["type"] = typ

    # Generic "named X" pattern - add name filter when service detected and "named" in question
    if intent.get("service") and "named" in q:
        has_name_filter = any(f.get("field") == "name" for f in intent.get("filters", []))
        # Only add if no name filter exists and type doesn't contain "named" (e.g., named-query, named-profile)
        if not has_name_filter and "named" not in (intent.get("type") or ""):
            named_m = re.search(r'\bnamed\s+([\w-]+)', q)
            if named_m:
                intent["filters"].append({"field": "name", "op": "eq", "value": named_m.group(1)})

    # ── "all SERVICE resources" pattern - clear type to get all types ─────
    # E.g., "show me all vpc resources" → service='vpc', type=None
    # Match: "all vpc resources", "all organizations resources", "all resource-explorer-2 resources"
    # MUST run AFTER all service-specific type assignments above
    if ("resource" in qw or "resources" in qw) and intent.get("service") and re.search(r'\ball\s+[\w-]+\s+resources?\b', q):
        intent["type"] = None


def _detect_multi_service_patterns(q: str, qw: set, intent: dict) -> None:
    """Detect 'X and Y per Z' patterns for multi-service queries.

    Example: "count Lambda functions and S3 buckets per region"

    This enables queries that aggregate multiple services/types together.
    Generic implementation using existing _score_svc_type logic.
    """
    # Only for count queries
    if intent.get("action") != "count":
        return

    # Pattern: "resource1 and resource2 per grouping"
    # Allow 1-4 words for each resource phrase, but skip action words
    # Remove action words first to avoid matching "count ecr repositories"
    q_no_action = re.sub(r'^(count|show|list|find|give)\s+', '', q.lower())
    and_pattern = r'(\w+(?:\s+\w+){0,3}?)\s+and\s+(\w+(?:\s+\w+){0,3}?)\s+per'
    and_match = re.search(and_pattern, q_no_action)
    if not and_match:
        return

    resource1 = and_match.group(1)  # "lambda functions"
    resource2 = and_match.group(2)  # "s3 buckets"

    # Try to match each resource phrase to a service/type
    matches = []
    for resource_phrase in (resource1, resource2):
        # Skip overly generic phrases that don't specify a service
        generic_only = {"resource", "resources", "thing", "things", "item", "items"}
        if resource_phrase.strip() in generic_only:
            continue

        # Use _q_words to properly stem plurals ("functions" → "function")
        phrase_words = _q_words(resource_phrase)
        best_svc, best_type, best_score = None, None, 0

        # Use existing _score_svc_type logic
        for svc, types in _AWSMAP_TYPES.items():
            score, matched_type = _score_svc_type(phrase_words, svc, types)
            if score > best_score:
                best_score, best_svc, best_type = score, svc, matched_type

        # Require reasonable match (score >= 2 to avoid weak matches)
        # If service matches but type doesn't, use first type as default
        if best_score >= 2 and best_svc:
            if not best_type and best_svc in _AWSMAP_TYPES:
                best_type = _AWSMAP_TYPES[best_svc][0]
            if best_type:
                matches.append((best_svc, best_type))

    # If we found 2 different service/type pairs, create multi-service query
    if len(matches) == 2 and matches[0] != matches[1]:
        # Clear single service/type
        intent["service"] = None
        intent["type"] = None

        # Store service/type pairs for build_sql
        intent["_multi_service_types"] = matches

        # Determine GROUP BY columns based on service/type diversity
        services = {svc for svc, _ in matches}
        types = {typ for _, typ in matches}

        # Same service, different types → GROUP BY service, region
        if len(services) == 1 and len(types) == 2:
            if "service" not in intent["group_by"]:
                intent["group_by"].insert(0, "service")
        # Different services, same types → GROUP BY service, region
        elif len(services) == 2 and len(types) == 1:
            if "service" not in intent["group_by"]:
                intent["group_by"].insert(0, "service")
        # Different services, different types → GROUP BY service, type, region
        elif len(services) == 2 and len(types) == 2:
            if "service" not in intent["group_by"]:
                intent["group_by"].insert(0, "service")
            if "type" not in intent["group_by"]:
                intent["group_by"].insert(1, "type")


def _extract_relationship_patterns(q: str, qw: set, intent: dict) -> None:
    """Extract 'X without any Y' NOT EXISTS relationship patterns."""
    # Generic pattern: "VPCs without any subnets", "subnets without route tables"
    without_any_m = re.search(r'(\w+)\s+without\s+any\s+(\w+)', q)
    if without_any_m and intent.get("service") and intent.get("type"):
        parent_word = without_any_m.group(1).lower()  # "vpcs"
        child_word = without_any_m.group(2).lower()   # "subnets"

        # Simple plural stemming for child word
        child_singular = child_word
        if child_word.endswith("s") and len(child_word) > 2:
            child_singular = child_word[:-1]  # "subnets" → "subnet"

        # Try to map child_word to a service/type
        parent_svc = intent["service"]
        parent_type = intent["type"]

        # Check if child is a known type in the same service or different service
        child_svc, child_type = None, None

        # First, check within same service
        if parent_svc in _AWSMAP_TYPES:
            for t in _AWSMAP_TYPES[parent_svc]:
                if (child_word in t or child_singular in t or
                    t.replace("-", "") == child_word or t == child_singular):
                    child_svc, child_type = parent_svc, t
                    break

        # If not found, check other services
        if not child_type:
            for svc, types in _AWSMAP_TYPES.items():
                for t in types:
                    if (child_word in t or child_singular in t or
                        t.replace("-", "") == child_word or t == child_singular):
                        child_svc, child_type = svc, t
                        break
                if child_type:
                    break

        # If we found the child type, add NOT EXISTS relationship
        if child_type and child_svc:
            intent["_relationship_filter"] = {
                "type": "not_exists",
                "child_service": child_svc,
                "child_type": child_type
            }


def _extract_region_filters(q: str, qw: set, intent: dict) -> None:
    """Extract region filters (in/not in region), including OR patterns."""
    # Check for OR pattern first: "in us-east-1 or us-west-2"
    regions = list(_REGION_RE.finditer(q))
    if len(regions) >= 2:
        # Check if there's an "or" between the regions
        first_region = regions[0].group(1)
        second_region = regions[1].group(1)
        between = q[regions[0].end():regions[1].start()]
        if "or" in between:
            # Check for negation before first region
            before_first = q[:regions[0].start()]
            is_neg = bool(re.search(r'\b(outside|not\s+in|except)\b', before_first))
            op = "ne" if is_neg else "eq"
            # Add both regions
            # For positive: "in A or B" = (region='A' OR region='B')
            # For negative: "not in A or B" = (region!='A' AND region!='B')
            intent["filters"].append({"field": "region", "op": op, "value": first_region})
            if is_neg:
                # Negation uses AND logic
                intent["filters"].append({"field": "region", "op": op, "value": second_region})
            else:
                # Positive uses OR logic
                intent["filters"].append({"field": "region", "op": op, "value": second_region, "logic": "or"})
            return

    # Single region pattern (original logic)
    region_m = _REGION_RE.search(q)
    if region_m:
        region = region_m.group(1)
        # Skip "global" if it's part of a resource attribute (not a region filter)
        if region == "global":
            region_pos = q.find(region)
            after_global = q[region_pos + len("global"):region_pos + len("global") + 20]
            # Skip if followed by table/secondary/index/replication keywords
            if re.search(r'\s+(table|secondary|index|replication)', after_global):
                return
        # Check for negation: "outside X", "not in X", "except X"
        region_pos = q.find(region)
        before_region = q[:region_pos]
        is_neg = bool(re.search(r'\b(outside|not\s+in|except)\b', before_region))
        op = "ne" if is_neg else "eq"
        intent["filters"].append({"field": "region", "op": op, "value": region})


def _extract_semantic_filters(q: str, qw: set, intent: dict) -> None:
    """Extract semantic keyword filters and context-aware patterns."""
    # Context-aware "public" / "private" filters (service-specific field mappings)
    if "public" in q or "private" in q:
        svc = intent.get("service")
        typ = intent.get("type")

        # VPC subnets: use map_public_ip_on_launch (only for "public subnet" / "private subnet" queries)
        # "auto-assign public IP" queries are handled in _extract_state_filters
        if svc == "vpc" and typ == "subnet":
            if "public subnet" in q and "private" not in q:
                intent["filters"].append({"field": "$.map_public_ip_on_launch", "op": "eq", "value": 1})
            elif "private subnet" in q and "public" not in q:
                intent["filters"].append({"field": "$.map_public_ip_on_launch", "op": "eq", "value": 0})

        # Route53: use private_zone (note: 0=public, 1=private)
        elif svc == "route53" and typ == "hosted-zone":
            if "public" in q and "private zone" not in q:
                intent["filters"].append({"field": "$.private_zone", "op": "eq", "value": 0})
            # "private zone" is handled by _KW_FILTERS

        # EC2 instances: use public_ip for "public IP" queries
        elif svc == "ec2" and typ == "instance":
            if "public" in q and "ip" in qw:
                if "without" in q or "no " in q:
                    intent["filters"].append({"field": "$.public_ip", "op": "is_null"})
                else:
                    intent["filters"].append({"field": "$.public_ip", "op": "is_not_null"})

        # S3 buckets: use public_access_blocked (handled by _KW_FILTERS default)
        # Other services: fall through to _KW_FILTERS default behavior

    # EventBridge rules: use state='ENABLED' instead of enabled=1
    if intent.get("service") == "events" and intent.get("type") == "rule":
        if "enabled" in q or "that are enabled" in q:
            intent["filters"].append({"field": "$.state", "op": "eq", "value": "ENABLED"})

    # Context-aware "unused" / "unattached" filters
    if "unused" in q or "unattached" in q:
        if ("elastic" in qw and "ip" in qw) or "eip" in qw:
            # Elastic IPs: unused = no association
            intent["filters"].append({"field": "$.association_id", "op": "is_null"})
        elif "ebs" in qw or ("volume" in qw and "elastic" not in qw):
            # EBS volumes: unattached = state='available'
            intent["filters"].append({"field": "$.state", "op": "eq", "value": "available"})

    # IAM instance profiles with roles
    if intent.get("service") == "iam" and intent.get("type") == "instance-profile":
        if "with roles" in q or "with role" in q:
            intent["filters"].append({"field": "$.roles", "op": "is_not_null"})

    # IAM roles that trust external accounts
    # "roles who trust external accounts" / "which account is trusted" / "what trusts external"
    if intent.get("service") == "iam" and intent.get("type") == "role":
        if any(p in q for p in ("trust external", "trust other account", "trust external account",
                                 "is trusted", "are trusted", "which account", "which external")):
            # Add marker for SQL builder to add custom WHERE clause
            intent["_trust_external_accounts"] = True

    # SQS queues: use dead_letter_target_arn for "dead letter target configured"
    if intent.get("service") == "sqs" and intent.get("type") == "queue":
        if "dead letter" in q and "target" in q and "configured" in q:
            intent["filters"].append({"field": "$.dead_letter_target_arn", "op": "is_not_null"})

    # Semantic keyword filters from _KW_FILTERS data table
    for kw, filt in _KW_FILTERS.items():
        if kw not in q:
            continue
        # Skip "public"/"private" if handled service-specifically above
        if kw in ("public", "private"):
            svc = intent.get("service")
            typ = intent.get("type")
            # Skip if service-specific handling applied
            if ((svc == "vpc" and typ == "subnet")
                or (svc == "route53" and typ == "hosted-zone" and kw == "public")
                or (svc == "ec2" and typ == "instance" and "ip" in qw)):
                continue
        # Skip "admin" if question uses it in a name-search context
        if kw == "admin" and any(p in q for p in ("admin in the name", "admin in name", "contain admin")):
            continue
        # Skip "admin" if "without admin" is in question (negation takes precedence)
        if kw == "admin" and "without admin" in q:
            continue
        # Skip "environment" keyword if it's part of tag context (tagged with Environment)
        if kw in ("with environment", "without environment") and any(p in q for p in ("tagged with", "tag")):
            continue
        # Skip "not enabled" if "that are not enabled" also present (avoid duplicate)
        if kw == "not enabled" and "that are not enabled" in q:
            continue
        # Skip "that are enabled" for EventBridge rules (use state='ENABLED' instead)
        if kw == "that are enabled" and intent.get("service") == "events" and intent.get("type") == "rule":
            continue
        # Skip "with dead letter" for SQS queues with "target configured" (use dead_letter_target_arn instead)
        if kw == "with dead letter" and intent.get("service") == "sqs" and intent.get("type") == "queue" and "target" in q and "configured" in q:
            continue
        # Skip "default" if also "non-default" present (non-default takes precedence)
        if kw == "default" and "non-default" in q:
            continue
        # Skip "default" if no service context yet (too generic)
        if kw == "default" and not intent.get("service"):
            continue
        # Skip "default" if "is_default" field is explicitly specified
        if kw == "default" and re.search(r'\bis_default\s+[01]\b', q):
            continue
        # Skip "with tags" if "without tags" also present
        if kw == "with tags" and any(x in q for x in ("without tags", "no tags")):
            continue
        # Skip "public" if it's part of service/type name (e.g., "ECR public") or name search
        if kw == "public" and (
            intent.get("service") == "ecr-public"
            or any(p in q for p in ("ecr public", "ecr-public", "public repositories", "containing public", "with name containing public", "name containing public"))
        ):
            continue
        # Skip "default" if it's part of name search context
        if kw == "default" and any(p in q for p in ("containing default", "with name containing default", "default in name", "default in the name")):
            continue
        intent["filters"].append(dict(filt))

    # Context-aware enabled field corrections
    # CloudTrail uses $.is_logging instead of $.enabled
    if intent.get("service") == "cloudtrail" and ("not enabled" in q or "that are not enabled" in q):
        # Replace $.enabled filter with $.is_logging
        for i, f in enumerate(intent.get("filters", [])):
            if f.get("field") == "$.enabled" and f.get("op") in ("ne", "eq"):
                # CloudTrail uses boolean for is_logging
                # "not enabled" means is_logging = false (0), not NULL
                intent["filters"][i] = {"field": "$.is_logging", "op": "eq", "value": False}


def _extract_name_filters(q: str, qw: set, intent: dict) -> None:
    """Extract name filters: 'named X', 'containing X', etc."""
    # "named X" uses exact match, "containing X" uses LIKE
    # Skip if type contains "named" (e.g., named-query, named-profile)
    # Skip if name filter already exists (to avoid duplicates)
    named_exact = re.search(r'\bnamed\s+(\S+)', q)
    has_name_filter = any(f.get("field") == "name" for f in intent.get("filters", []))
    if named_exact and not has_name_filter and not any(p in q for p in ("containing", "or")) and "named" not in (intent.get("type") or ""):
        intent["filters"].append({"field": "name", "op": "eq", "value": named_exact.group(1)})
    else:
        _NAME_RES = [
            re.compile(r'\bname\s+containing\s+(\S+)'),
            re.compile(r'\bcontaining\s+(\S+)\s+in\s+(?:the\s+)?name'),
            re.compile(r'\bwith\s+name\s+containing\s+(\S+)'),
            re.compile(r'\bcontain\s+(\S+)\s+in\s+(?:the\s+)?name'),
            re.compile(r'\bname\s+contains\s+(\S+)'),
        ]
        # OR pattern: "containing X or Y in name" / "named X or Y"
        or_m = re.search(r'\b(?:containing|named)\s+(\S+)\s+or\s+(\S+)(?:\s+in\s+(?:the\s+)?name)?', q)
        if or_m:
            intent["filters"].append({"field": "name", "op": "like", "value": f"%{or_m.group(1)}%"})
            intent["filters"].append({"field": "name", "op": "like", "value": f"%{or_m.group(2)}%", "logic": "or"})
        else:
            for pat in _NAME_RES:
                m = pat.search(q)
                if m:
                    intent["filters"].append({"field": "name", "op": "like", "value": f"%{m.group(1)}%"})
                    break
    # admin in name context
    if "admin" in q and any(p in q for p in ("admin in the name", "admin in name", "contain admin")):
        intent["filters"].append({"field": "name", "op": "like", "value": "%admin%"})

    # "for X service/functions" pattern - filter by service name in role/resource name
    # Special handling for CloudWatch log groups: "for Lambda functions" → name LIKE '/aws/lambda/%'
    if intent.get("service") == "logs" and intent.get("type") == "log-group":
        if "for lambda" in q.lower():
            intent["filters"].append({"field": "name", "op": "like", "value": "/aws/lambda/%"})
        elif "for api gateway" in q.lower():
            intent["filters"].append({"field": "name", "op": "like", "value": "/aws/apigateway/%"})
    else:
        for_service_m = re.search(r'\bfor\s+(\w+)\s+(?:service|functions?)\b', q, re.IGNORECASE)
        if for_service_m and not has_name_filter:
            service_name = for_service_m.group(1)
            intent["filters"].append({"field": "name", "op": "like", "value": f"%{service_name}%"})

    # Runtime filter (including OR patterns: "not using python or nodejs")
    # Check for "not using X or Y" pattern first
    not_runtime_or = re.search(r'\bnot\s+using\s+(python|nodejs|java|go|ruby|dotnet|rust)\s+or\s+(python|nodejs|java|go|ruby|dotnet|rust)', q)
    if not_runtime_or:
        rt1 = not_runtime_or.group(1)
        rt2 = not_runtime_or.group(2)
        intent["filters"].append({"field": "$.runtime", "op": "not_like", "value": f"{rt1}%"})
        intent["filters"].append({"field": "$.runtime", "op": "not_like", "value": f"{rt2}%"})
    elif "not using python" not in q and "not python" not in q:
        rt_m = re.search(r'\b(python|nodejs|java(?:17|21|11)?|go|ruby|dotnet|rust)(\d*\.?\d*)(?:\s+runtime)?\b', q)
        if rt_m:
            rt = rt_m.group(1) + rt_m.group(2)
            intent["filters"].append({"field": "$.runtime", "op": "like", "value": f"{rt}%"})
        elif "python" in qw and "not" not in qw:
            intent["filters"].append({"field": "$.runtime", "op": "like", "value": "python%"})


def _extract_using_patterns(q: str, qw: set, intent: dict) -> None:
    """Extract generic 'using X' patterns from _USING_MAP for RDS engines, ElastiCache engines, etc."""
    svc = intent.get("service")
    if not svc:
        return
    # Check for "using" or "not using" keyword
    using_m = re.search(r'\b(not\s+)?using\s+(.+?)(?:\s+(?:per|in|sorted|and|with|$))', q)
    if not using_m:
        using_m = re.search(r'\b(not\s+)?using\s+(\S+(?:\s+\S+)?)\s*$', q)
    if not using_m:
        return
    is_negated = bool(using_m.group(1))
    using_phrase = using_m.group(2).strip().lower()

    for ctx_svc, kw_re, detail_field, value_prefix in _USING_MAP:
        if ctx_svc and svc != ctx_svc:
            continue
        if re.search(kw_re, using_phrase):
            # Skip if filter already exists for this field
            if any(f.get("field") == detail_field for f in intent.get("filters", [])):
                break
            if is_negated:
                _add_filter(intent, {"field": detail_field, "op": "not_like", "value": f"{value_prefix}%"})
            else:
                _add_filter(intent, {"field": detail_field, "op": "like", "value": f"{value_prefix}%"})
            break


def _extract_relative_time_filters(q: str, qw: set, intent: dict) -> None:
    """Extract relative time filters: 'created in the last N days', 'older than N days', etc."""
    now = datetime.utcnow()

    # "created/modified in the last N days/weeks/months"
    last_m = re.search(r'\b(created|modified)\s+in\s+the\s+last\s+(\d+)\s+(day|week|month|hour)s?', q)
    if last_m:
        action_word = last_m.group(1)
        n = int(last_m.group(2))
        unit = last_m.group(3)
        if unit == "week":
            delta = timedelta(days=n * 7)
        elif unit == "month":
            delta = timedelta(days=n * 30)
        elif unit == "hour":
            delta = timedelta(hours=n)
        else:
            delta = timedelta(days=n)
        cutoff = (now - delta).strftime("%Y-%m-%d")
        fields = _TIME_FIELDS.get(action_word, _TIME_FIELDS["created"])
        for field in fields:
            _add_filter(intent, {"field": field, "op": "gte", "value": cutoff})
        return

    # "older than N days"
    older_m = re.search(r'\bolder\s+than\s+(\d+)\s+(day|week|month)s?', q)
    if older_m:
        n = int(older_m.group(1))
        unit = older_m.group(2)
        if unit == "week":
            delta = timedelta(days=n * 7)
        elif unit == "month":
            delta = timedelta(days=n * 30)
        else:
            delta = timedelta(days=n)
        cutoff = (now - delta).strftime("%Y-%m-%d")
        fields = _TIME_FIELDS["created"]
        for field in fields:
            _add_filter(intent, {"field": field, "op": "lte", "value": cutoff})
        return

    # "expiring within N days"
    expiring_m = re.search(r'\bexpiring\s+within\s+(\d+)\s+(day|week|month)s?', q)
    if expiring_m:
        n = int(expiring_m.group(1))
        unit = expiring_m.group(2)
        if unit == "week":
            delta = timedelta(days=n * 7)
        elif unit == "month":
            delta = timedelta(days=n * 30)
        else:
            delta = timedelta(days=n)
        future = (now + delta).strftime("%Y-%m-%d")
        today = now.strftime("%Y-%m-%d")
        fields = _TIME_FIELDS["expiring"]
        for field in fields:
            _add_filter(intent, {"field": field, "op": "gte", "value": today})
            _add_filter(intent, {"field": field, "op": "lte", "value": future})
        return

    # "created after YYYY-MM-DD" / "created before YYYY-MM-DD"
    date_m = re.search(r'\b(created|modified)\s+(after|before)\s+(\d{4}-\d{2}-\d{2})', q)
    if date_m:
        action_word = date_m.group(1)
        direction = date_m.group(2)
        date_val = date_m.group(3)
        op = "gte" if direction == "after" else "lte"
        fields = _TIME_FIELDS.get(action_word, _TIME_FIELDS["created"])
        for field in fields:
            _add_filter(intent, {"field": field, "op": op, "value": date_val})
        return


def _extract_generic_numeric_field_filters(q: str, qw: set, intent: dict) -> None:
    """Extract generic numeric field filters using _NUMERIC_FIELD_PATTERNS."""
    for field_kw, field_path in _NUMERIC_FIELD_PATTERNS:
        # Replace underscores with spaces for matching
        field_kw_spaced = field_kw.replace("_", " ")
        field_kw_under = field_kw
        # Check if keyword (with underscores or spaces) appears in question
        if field_kw_spaced not in q and field_kw_under not in q:
            continue
        # Skip if a filter for this field path already exists
        if any(f.get("field") == field_path for f in intent.get("filters", [])):
            continue
        # Try gt/gte/lt/lte/eq patterns
        kw_pat = field_kw_spaced.replace(" ", r"[\s_]")
        for op, pats in (
            ("gt",  [rf'{kw_pat}\s+(?:greater|more)\s+than\s+(\d+)', rf'{kw_pat}\s*>\s*(\d+)']),
            ("gte", [rf'{kw_pat}\s+greater\s+than\s+or\s+equal\s+(?:to\s+)?(\d+)', rf'{kw_pat}\s*>=\s*(\d+)']),
            ("lt",  [rf'{kw_pat}\s+(?:less|fewer)\s+than\s+(\d+)', rf'{kw_pat}\s*<\s*(\d+)']),
            ("lte", [rf'{kw_pat}\s+less\s+than\s+or\s+equal\s+(?:to\s+)?(\d+)', rf'{kw_pat}\s*<=\s*(\d+)']),
            ("eq",  [rf'{kw_pat}\s+(?:equal\s+(?:to\s+)?)?(\d+)']),
        ):
            matched = False
            for pat in pats:
                m = re.search(pat, q)
                if m:
                    _add_filter(intent, {"field": field_path, "op": op, "value": int(m.group(1))})
                    matched = True
                    break
            if matched:
                break


def _extract_keyword_value_patterns(q: str, qw: set, intent: dict, question: str = "") -> None:
    """Extract keyword-value patterns from _KEYWORD_VALUE_PATTERNS."""
    # Use original question to preserve case of captured values
    source = question if question else q
    for kw_re, detail_field, _ in _KEYWORD_VALUE_PATTERNS:
        m = re.search(kw_re, source, re.IGNORECASE)
        if m:
            value = m.group(1)
            # Skip if filter already exists for this field
            if any(f.get("field") == detail_field for f in intent.get("filters", [])):
                continue
            _add_filter(intent, {"field": detail_field, "op": "eq", "value": value})


def _extract_numeric_filters(q: str, qw: set, intent: dict) -> None:
    """Extract numeric filters: memory, timeout, retention."""
    for field_kw, field_path in (
        ("memory", "$.memory_size"),
        ("timeout", "$.timeout"),
        ("retention", "$.retention_days"),
    ):
        if field_kw not in qw:
            continue
        # Skip generic "timeout" if it's part of "visibility timeout"
        if field_kw == "timeout" and "visibility timeout" in q:
            continue
        if f"excluding {field_kw} greater than" in q or f"excluding timeout greater than" in q:
            n = re.search(r'excluding\s+\w+\s+greater\s+than\s+(\d+)', q)
            if n:
                intent["filters"].append({"field": field_path, "op": "lte", "value": int(n.group(1))})
            continue
        bt = re.search(rf'{field_kw}.{{0,15}}between\s+(\d+)\s+and\s+(\d+)', q)
        if bt:
            intent["filters"].append({"field": field_path, "op": "between",
                                       "value": int(bt.group(1)), "value2": int(bt.group(2))})
            continue

        # Exact value match: "with memory 128" or "with timeout 30"
        exact_m = re.search(rf'\b(?:with\s+)?{field_kw}\s+(\d+)(?:\s+(?:MB|mb|seconds?|days?))?\b', q)
        if exact_m:
            intent["filters"].append({"field": field_path, "op": "eq", "value": int(exact_m.group(1))})
            continue

        # Reverse order: "with 128 MB memory" (number before field)
        reverse_m = re.search(rf'\bwith\s+(\d+)\s+(?:MB|mb|seconds?|days?)\s+{field_kw}\b', q)
        if reverse_m:
            intent["filters"].append({"field": field_path, "op": "eq", "value": int(reverse_m.group(1))})
            continue

        # Check all patterns, collect all matches
        # Try both directions: "memory > 256" and "> 256 MB memory"
        for op, pats in (
            ("gt",  [r"(?:greater|more)\s+than\s+(\d+)", r">\s*(\d+)"]),
            ("gte", [r"greater than or equal\s+(?:to\s+)?(\d+)", r">=\s*(\d+)"]),
            ("lt",  [r"(?:less|fewer)\s+than\s+(\d+)", r"<\s*(\d+)"]),
            ("lte", [r"less than or equal\s+(?:to\s+)?(\d+)", r"<=\s*(\d+)"]),
        ):
            for pat in pats:
                # Try forward direction: "memory more than 256"
                m = re.search(rf'{field_kw}.{{0,15}}{pat}', q)
                # Try reverse direction: "more than 256 MB memory" (require MB/GB unit)
                if not m:
                    m = re.search(rf'{pat}\s+(?:mb|gb)\s+{field_kw}', q)
                if m:
                    intent["filters"].append({"field": field_path, "op": op, "value": int(m.group(1))})
                    break
            if intent.get("filters") and intent["filters"][-1].get("field") == field_path:
                break

    # Boolean/numeric field filters: "with FIELD N"
    # E.g., "VPCs with is_default 0", "users with access_keys_count 0"
    numeric_fields = ["is_default", "main", "enabled", "encrypted", "public", "private",
                      "access_keys_count", "attachment_count"]
    for field in numeric_fields:
        # Pattern: "with FIELD N" or "FIELD N" where N is 0/1/true/false or any number
        field_m = re.search(rf'\b(?:with\s+)?{field}\s+(\d+|true|false)\b', q, re.IGNORECASE)
        if field_m:
            value_str = field_m.group(1).lower()
            # Convert to appropriate type
            if value_str in ("true", "false"):
                value = 1 if value_str == "true" else 0
            else:
                value = int(value_str)
            intent["filters"].append({"field": f"$.{field}", "op": "eq", "value": value})
            break  # Only match one field

    # String field filters: "with FIELD VALUE"
    # E.g., "RDS with mysql engine", "Lambda with python runtime"
    string_fields = ["engine", "runtime"]
    for field in string_fields:
        field_m = re.search(rf'\b(?:with\s+)?(\w+)\s+{field}\b', q)
        if field_m:
            value = field_m.group(1)
            # Skip if negation context: "not using python runtime"
            if re.search(rf'\b(?:not|without)\s+(?:using\s+)?{re.escape(value)}\s+{field}\b', q):
                continue
            # Skip ordering/grouping keywords and digit-only values
            if value not in ("by", "sorted", "ordered", "and", "or", "the", "their", "show", "with") and not value.isdigit():
                # Skip if filter already exists for this field (avoid duplicates)
                field_path = f"$.{field}"
                if not any(f.get("field") == field_path for f in intent.get("filters", [])):
                    intent["filters"].append({"field": field_path, "op": "eq", "value": value})
                break


def _extract_state_filters(q: str, qw: set, intent: dict, question: str) -> None:
    """Extract state/status filters."""
    # Uppercase keywords from original question (preserve case)
    state_m = re.search(r'\b(ALARM|OK|INSUFFICIENT_DATA)\b', question)
    if state_m:
        intent["filters"].append({"field": "$.state_value", "op": "eq", "value": state_m.group(1)})
    status_m = re.search(
        r'\b(CREATE_COMPLETE|CREATE_FAILED|UPDATE_COMPLETE|ROLLBACK_COMPLETE|'
        r'DELETE_COMPLETE|ISSUED|PENDING_VALIDATION|EXPIRED|ACTIVE|INACTIVE|'
        r'FAILED|RUNNING|SUCCEEDED|ENABLED|DISABLED)\b', question
    )
    if status_m:
        status_val = status_m.group(1)
        # Check for negation: "that are not FAILED"
        is_negated = re.search(rf'\b(?:that\s+are\s+not|not)\s+{status_val}', question, re.IGNORECASE) is not None
        op = "ne" if is_negated else "eq"
        # DynamoDB streams use $.stream_status instead of $.status
        field = "$.stream_status" if intent.get("service") == "dynamodb" and intent.get("type") == "stream" else "$.status"
        intent["filters"].append({"field": field, "op": op, "value": status_val})
    ec2_state_m = re.search(r'\b(running|stopped|terminated|pending|stopping)\b', q)
    if ec2_state_m and not status_m:
        state_val = ec2_state_m.group(1)
        # Check for negation: "not in X state" / "not X"
        is_negated = re.search(rf'\bnot\s+(?:in\s+)?{state_val}', q) is not None
        op = "ne" if is_negated else "eq"
        intent["filters"].append({"field": "$.state", "op": op, "value": state_val})

    # Last build status filter (CodeBuild)
    last_build_m = re.search(r'\blast\s+build\s+(FAILED|SUCCEEDED|STOPPED|IN_PROGRESS)', question)
    if last_build_m:
        intent["filters"].append({"field": "$.last_build_status", "op": "eq", "value": last_build_m.group(1)})

    # Instance type filter (EC2)
    # Matches: "instance type t3.micro" OR "of type t3.micro" (when service is EC2)
    instance_type_m = re.search(r'\b(?:instance\s+)?type\s+([a-z0-9]+\.[a-z0-9]+)', q)
    if instance_type_m and (intent.get("service") == "ec2" or "instance" in q):
        # Check for negation: "not of type X"
        is_negated = re.search(r'\bnot\s+(?:of\s+)?type\s+' + re.escape(instance_type_m.group(1)), q) is not None
        op = "ne" if is_negated else "eq"
        intent["filters"].append({"field": "$.instance_type", "op": op, "value": instance_type_m.group(1)})

    # Instance type categories (compute/memory optimized, graviton)
    if "compute optimized" in q or "compute-optimized" in q:
        intent["filters"].append({"field": "$.instance_type", "op": "like", "value": "c%"})
    elif "memory optimized" in q or "memory-optimized" in q:
        intent["filters"].append({"field": "$.instance_type", "op": "like", "value": "r%"})
    elif "graviton" in q:
        intent["filters"].append({"field": "$.instance_type", "op": "like", "value": "%g.%"})

    # Billing mode filter (DynamoDB)
    # Matches: "billing mode PROVISIONED" OR "with PROVISIONED billing"
    billing_m = re.search(r'\b(?:billing\s+mode\s+([A-Z_]+)|([A-Z_]+)\s+billing)', question)
    if billing_m:
        value = billing_m.group(1) or billing_m.group(2)
        intent["filters"].append({"field": "$.billing_mode", "op": "eq", "value": value})

    # Launch type filter (ECS)
    launch_type_m = re.search(r'\b(FARGATE|EC2)\s+launch\s+type', question)
    if launch_type_m:
        intent["filters"].append({"field": "$.launch_type", "op": "eq", "value": launch_type_m.group(1)})

    # Security groups allowing 0.0.0.0/0
    if "allowing access from 0.0.0.0/0" in q or "allow 0.0.0.0/0" in q:
        intent["filters"].append({"field": "$.ingress_rules", "op": "like", "value": "%0.0.0.0/0%"})

    # Numeric comparisons for sizes and counts
    # "larger than X GB" or "greater than X GB"
    size_m = re.search(r'(?:larger|greater)\s+than\s+(\d+)\s*(?:GB|gb)', q, re.IGNORECASE)
    if size_m:
        intent["filters"].append({"field": "$.size", "op": "gt", "value": int(size_m.group(1))})

    # "number of nodes greater than X"
    nodes_m = re.search(r'number\s+of\s+nodes\s+(?:greater|more)\s+than\s+(\d+)', q)
    if nodes_m:
        intent["filters"].append({"field": "$.number_of_nodes", "op": "gt", "value": int(nodes_m.group(1))})

    # === GENERIC DETAIL FIELD FILTERS ===

    # Lambda: code_size "greater than X"
    code_size_m = re.search(r'code\s+size\s+(?:greater|larger)\s+than\s+(\d+)', q)
    if code_size_m:
        intent["filters"].append({"field": "$.code_size", "op": "gt", "value": int(code_size_m.group(1))})

    # Lambda: ephemeral_storage "greater than X"
    ephemeral_m = re.search(r'ephemeral\s+storage\s+(?:greater|larger)\s+than\s+(\d+)', q)
    if ephemeral_m:
        intent["filters"].append({"field": "$.ephemeral_storage_size", "op": "gt", "value": int(ephemeral_m.group(1))})

    # Lambda: handler "containing X"
    handler_m = re.search(r'handler\s+containing\s+(\w+)', q)
    if handler_m:
        intent["filters"].append({"field": "$.handler", "op": "like", "value": f"%{handler_m.group(1)}%"})

    # Lambda: package_type Image|Zip
    pkg_type_m = re.search(r'package\s+type\s+(Image|Zip)', question, re.IGNORECASE)
    if pkg_type_m:
        intent["filters"].append({"field": "$.package_type", "op": "eq", "value": pkg_type_m.group(1).capitalize()})

    # Lambda: architecture arm64|x86_64
    if "arm64" in q or "ARM64" in question:
        intent["filters"].append({"field": "$.architectures", "op": "like", "value": "%arm64%"})
    elif "x86" in q or "x86_64" in q:
        intent["filters"].append({"field": "$.architectures", "op": "like", "value": "%x86_64%"})

    # IAM: path "/service-role/" or "/aws-service-role/"
    path_m = re.search(r'path\s+(\/[\/\w-]+\/?)', q)
    if path_m:
        intent["filters"].append({"field": "$.path", "op": "like", "value": f"%{path_m.group(1)}%"})
    # IAM: custom path (not "/" and not "/aws-*")
    elif "custom path" in q:
        intent["filters"].append({"field": "$.path", "op": "ne", "value": "/"})
        intent["filters"].append({"field": "$.path", "op": "not_like", "value": "/aws-%"})

    # IAM: max_session_duration "greater than X"
    max_session_m = re.search(r'max\s+session\s+duration\s+(?:greater|more)\s+than\s+(\d+)', q)
    if max_session_m:
        intent["filters"].append({"field": "$.max_session_duration", "op": "gt", "value": int(max_session_m.group(1))})

    # IAM: MFA enabled/disabled (check negative first to avoid matching "without mfa enabled")
    if "without mfa" in q or "mfa disabled" in q:
        intent["filters"].append({"field": "$.mfa_enabled", "op": "is_null_or_false"})
    elif "mfa enabled" in q or "with mfa" in q:
        intent["filters"].append({"field": "$.mfa_enabled", "op": "eq", "value": 1})

    # IAM: access keys (skip if explicit field value specified)
    if ("access keys" in q or "access_keys" in q) and not re.search(r'\baccess_keys_count\s+\d+\b', q):
        if "without access keys" in q or "without access_keys" in q:
            intent["filters"].append({"field": "$.access_keys_count", "op": "eq", "value": 0})
        else:
            intent["filters"].append({"field": "$.access_keys_count", "op": "gt", "value": 0})

    # S3: created_date "after YYYY"
    created_m = re.search(r'created\s+after\s+(\d{4})', q)
    if created_m:
        intent["filters"].append({"field": "$.creation_date", "op": "gt", "value": f"{created_m.group(1)}-01-01"})

    # DynamoDB: billing mode
    if "PAY_PER_REQUEST" in q or "pay_per_request" in q:
        intent["filters"].append({"field": "$.billing_mode", "op": "eq", "value": "PAY_PER_REQUEST"})
    elif "PROVISIONED" in q and "billing" in q:
        intent["filters"].append({"field": "$.billing_mode", "op": "eq", "value": "PROVISIONED"})

    # S3: versioning Enabled|Suspended|Disabled
    versioning_m = re.search(r'versioning\s+(Enabled|Suspended|Disabled)', question, re.IGNORECASE)
    if versioning_m:
        intent["filters"].append({"field": "$.versioning", "op": "eq", "value": versioning_m.group(1).capitalize()})

    # DynamoDB: stream enabled/disabled
    if "stream enabled" in q or "with stream" in q:
        intent["filters"].append({"field": "$.stream_enabled", "op": "eq", "value": 1})
    elif "without stream" in q or "stream disabled" in q:
        intent["filters"].append({"field": "$.stream_enabled", "op": "is_null_or_false"})

    # EBS: volume_type gp2|gp3|io1|io2|st1|sc1
    vol_type_m = re.search(r'volume\s+type\s+(gp2|gp3|io1|io2|st1|sc1|standard)', q)
    if vol_type_m:
        intent["filters"].append({"field": "$.volume_type", "op": "eq", "value": vol_type_m.group(1)})

    # EBS: encryption enabled (but not "encryption configured")
    if ("encryption enabled" in q or "with encryption enabled" in q) and "encryption configured" not in q:
        intent["filters"].append({"field": "$.encrypted", "op": "eq", "value": 1})

    # VPC: CIDR "10.0.0.0/16" or "containing 172.31"
    cidr_exact_m = re.search(r'CIDR\s+(\d+\.\d+\.\d+\.\d+/\d+)', q, re.IGNORECASE)
    cidr_contains_m = re.search(r'CIDR\s+containing\s+(\d+\.\d+)', q, re.IGNORECASE)
    if cidr_exact_m:
        intent["filters"].append({"field": "$.cidr_block", "op": "eq", "value": cidr_exact_m.group(1)})
    elif cidr_contains_m:
        intent["filters"].append({"field": "$.cidr_block", "op": "like", "value": f"%{cidr_contains_m.group(1)}%"})

    # Subnets: map_public_ip on launch
    if "map public ip on launch" in q or "auto-assign public ip" in q or "auto assign public ip" in q:
        # Check for negation: "without auto-assign public IP" means =0
        has_negation = any(neg in q for neg in ("without", "no ", "not "))
        value = 0 if has_negation else 1
        intent["filters"].append({"field": "$.map_public_ip_on_launch", "op": "eq", "value": value})

    # Subnets: available_ip_count
    avail_ip_m = re.search(r'available\s+ip\s+count\s+(?:greater|more)\s+than\s+(\d+)', q)
    if avail_ip_m:
        intent["filters"].append({"field": "$.available_ip_address_count", "op": "gt", "value": int(avail_ip_m.group(1))})

    # CloudWatch: namespace (case-insensitive match, normalize to AWS/Service format)
    namespace_m = re.search(r'namespace\s+aws/([\w]+)', q, re.IGNORECASE)
    if namespace_m:
        # Normalize to AWS/Service format with capitalized service name (AWS/Lambda, not AWS/LAMBDA)
        service_name = namespace_m.group(1).capitalize()
        namespace_value = f"AWS/{service_name}"
        intent["filters"].append({"field": "$.namespace", "op": "eq", "value": namespace_value})

    # Logs: retention (without policy = NULL)
    if "without retention policy" in q or "without retention" in q:
        intent["filters"].append({"field": "$.retention_days", "op": "is_null"})
    elif "with retention" in q or "retention configured" in q:
        intent["filters"].append({"field": "$.retention_days", "op": "is_not_null"})

    # Logs: stored_bytes
    stored_bytes_m = re.search(r'stored\s+bytes\s+(?:greater|more)\s+than\s+(\d+)', q)
    if stored_bytes_m:
        intent["filters"].append({"field": "$.stored_bytes", "op": "gt", "value": int(stored_bytes_m.group(1))})

    # EventBridge: schedule_expression (check negative first)
    if "without schedule" in q:
        intent["filters"].append({"field": "$.schedule_expression", "op": "is_null"})
    elif "schedule expression" in q or "with schedule" in q:
        intent["filters"].append({"field": "$.schedule_expression", "op": "is_not_null"})

    # S3: encryption configured
    if "encryption configured" in q or "with encryption configured" in q:
        intent["filters"].append({"field": "$.encryption", "op": "is_not_null"})

    # S3: versioning (without specific state)
    if "s3" in qw or "bucket" in qw:
        if "with versioning" in q and "versioning enabled" not in q and "versioning suspended" not in q:
            intent["filters"].append({"field": "$.versioning", "op": "is_not_null"})

    # Security groups: no ingress rules / no rules
    if ("security" in qw and "group" in qw) and ("no ingress" in q or "without ingress" in q):
        intent["filters"].append({"field": "$.ingress_rules_count", "op": "eq", "value": 0})

    # ACM: not in use (check for NULL or empty array '[]')
    if "acm" in qw and "not in use" in q:
        intent["filters"].append({"field": "$.in_use_by", "op": "is_empty"})

    # ECS: active_services_count > X
    if "ecs" in qw and "cluster" in qw:
        active_m = re.search(r'active\s+services\s+(?:greater|more)\s+than\s+(\d+)', q)
        if active_m:
            intent["filters"].append({"field": "$.active_services_count", "op": "gt", "value": int(active_m.group(1))})

    # Route53: public/private hosted zones
    if "route53" in qw or "hosted zone" in q:
        if "public" in q and "hosted zone" in q:
            intent["filters"].append({"field": "$.private_zone", "op": "is_null_or_false"})
        elif "private" in q and "hosted zone" in q:
            intent["filters"].append({"field": "$.private_zone", "op": "eq", "value": 1})

    # SQS: visibility_timeout
    if "sqs" in qw or "queue" in qw:
        visibility_m = re.search(r'visibility\s+timeout\s+(?:greater|more)\s+than\s+(\d+)', q)
        if visibility_m:
            intent["filters"].append({"field": "$.visibility_timeout", "op": "gt", "value": int(visibility_m.group(1))})

    # DynamoDB: gsi_count greater than X
    if "gsi_count" in q or "gsi count" in q:
        gsi_m = re.search(r'gsi[_\s]count\s+(?:greater|more)\s+than\s+(\d+)', q)
        if gsi_m:
            intent["filters"].append({"field": "$.gsi_count", "op": "gt", "value": int(gsi_m.group(1))})

    # IAM: path / (exact match)
    if ("iam" in qw or "role" in qw or "policy" in qw) and "path /" in q:
        intent["filters"].append({"field": "$.path", "op": "eq", "value": "/"})

    # IAM: attachment_count greater than X
    if "attachment_count" in q or "attachment count" in q:
        attach_m = re.search(r'attachment[_\s]count\s+(?:greater|more)\s+than\s+(\d+)', q)
        if attach_m:
            intent["filters"].append({"field": "$.attachment_count", "op": "gt", "value": int(attach_m.group(1))})

    # CloudTrail: is_logging, is_multi_region, is_organization_trail, log_file_validation_enabled
    if "cloudtrail" in qw or "trail" in qw:
        # Check negation FIRST to avoid matching "logging" in "not logging"
        if "not logging" in q or "that are not logging" in q:
            intent["filters"].append({"field": "$.is_logging", "op": "is_null_or_false"})
        elif "logging" in q or "that are logging" in q:
            intent["filters"].append({"field": "$.is_logging", "op": "eq", "value": 1})
        if "multi-region" in q or "multi region" in q:
            intent["filters"].append({"field": "$.is_multi_region_trail", "op": "eq", "value": 1})
        if "organization trail" in q:
            intent["filters"].append({"field": "$.is_organization_trail", "op": "eq", "value": 1})
        if "log file validation" in q:
            intent["filters"].append({"field": "$.log_file_validation_enabled", "op": "eq", "value": 1})


def _extract_tag_filters(q: str, qw: set, intent: dict, question: str) -> None:
    """Extract tag filters: tagged with X, tag=value, tag count, etc."""
    not_tagged_m = re.search(r'\bnot\s+tagged\s+with\s+(\w+)', q)
    not_env_m = re.search(r'\bnot\s+tagged\s+with\s+Environment\b', question)
    if not_tagged_m:
        intent["filters"].append({"field": f"tags.{not_tagged_m.group(1).capitalize()}", "op": "is_null"})
    else:
        # Check for OR: "tagged with X or Y"
        tagged_or_m = re.search(r'\btagged\s+with\s+(\w+)\s+or\s+(\w+)', q)
        if tagged_or_m:
            tag1 = tagged_or_m.group(1).capitalize()
            tag2 = tagged_or_m.group(2).capitalize()
            intent["filters"].append({"field": f"tags.{tag1}", "op": "is_not_null"})
            intent["filters"].append({"field": f"tags.{tag2}", "op": "is_not_null", "logic": "or"})
        else:
            # Check for tag=value pattern first (use original question to preserve case)
            tagged_val_m = re.search(r'\btagged\s+with\s+(\w+)=(\w+)', question, re.IGNORECASE)
            if tagged_val_m:
                tag_name = tagged_val_m.group(1)  # Preserve original case
                tag_value = tagged_val_m.group(2)
                intent["filters"].append({"field": f"tags.{tag_name}", "op": "eq", "value": tag_value})
            else:
                # Check for tag exists pattern
                tagged_m = re.search(r'\btagged\s+with\s+(\w+)', q)
                if tagged_m:
                    intent["filters"].append({"field": f"tags.{tagged_m.group(1).capitalize()}", "op": "is_not_null"})
            if not_env_m and not tagged_val_m:
                intent["filters"].append({"field": "tags.Environment", "op": "is_null"})

    # "which resources have a Name tag" - add Name tag to SELECT (but not for "without")
    if "name tag" in q and "without" not in q:
        intent["filters"].append({"field": "tags.Name", "op": "is_not_null"})
        intent["select_fields"].insert(0, "tags.Name")
        intent["service"] = None
        intent["type"] = None

    # "without a X tag" - specific tag field check (before generic "without tags")
    without_tag_m = re.search(r'\bwithout\s+(?:a\s+)?(\w+)\s+tag\b', q)
    if without_tag_m and "any" not in q and "tags" != without_tag_m.group(1).lower():
        tag_name = without_tag_m.group(1).capitalize()
        if not any(f.get("field") == f"tags.{tag_name}" for f in intent.get("filters", [])):
            intent["filters"].append({"field": f"tags.{tag_name}", "op": "is_null"})

    # "resources without any tags" / "without tags" - generic empty tags check
    if "without" in q and "tag" in qw and not any(f.get("field", "").startswith("tags") for f in intent.get("filters", [])):
        intent["filters"].append({"field": "tags", "op": "is_empty"})

    # "N or more tags" pattern - check tag count
    tags_count_m = re.search(r'with\s+(\d+)\s+or\s+more\s+tags', q)
    if tags_count_m:
        min_count = int(tags_count_m.group(1))
        # Store as custom filter for SQL builder to handle
        intent.setdefault("_custom_filters", []).append({
            "type": "tag_count_gte",
            "value": min_count
        })

    # "in production" / "in staging" → Environment tag filter
    env_context_m = re.search(r'\bin\s+(production|staging|development|dev|prod|test)', q)
    if env_context_m and not any(f.get("field") == "tags.Environment" for f in intent.get("filters", [])):
        env_value = env_context_m.group(1).capitalize()
        intent["filters"].append({"field": "tags.Environment", "op": "eq", "value": env_value})

    # VPC id filter
    vpc_id_m = re.search(r'\b(vpc-[0-9a-f]+)\b', q)
    if vpc_id_m:
        intent["filters"].append({"field": "$.vpc_id", "op": "eq", "value": vpc_id_m.group(1)})
        # If searching for resources "in vpc-XXX", fix type if it was wrongly set to "vpc"
        if intent.get("type") == "vpc" and "subnet" in qw:
            intent["service"] = "vpc"
            intent["type"] = "subnet"


def _extract_select_fields(q: str, qw: set, intent: dict) -> None:
    """Extract additional SELECT fields: CIDR, attached-policies, and show X."""
    if "cidr" in qw:
        intent["select_fields"].append("$.cidr_block")
    if "attached polic" in q and ("their" in qw or "and" in qw):
        if "$.attached_policies" not in intent["select_fields"]:
            intent["select_fields"].append("$.attached_policies")

    # Generic "show X" / "show their X and Y" pattern
    # Captures multiple fields separated by "and"
    # E.g., "show me their name and runtime" → ["name", "runtime"]
    # E.g., "and show memory" → ["memory"]
    show_match = re.search(
        r'\b(?:and\s+)?show\s+(?:me\s+)?(?:their|its|the)?\s*'
        r'([a-z_]+(?:\s+and\s+[a-z_]+)*)\s*$', q)
    if show_match:
        raw_fields = re.split(r'\s+and\s+', show_match.group(1))
        # Map common field names to JSON paths (service-aware for "type")
        field_map = {
            "memory": "$.memory_size",
            "runtime": "$.runtime",
            "runtimes": "$.runtime",
            "timeout": "$.timeout",
            "timeouts": "$.timeout",
            "state": "$.state",
            "status": "$.status",
            "engine": "$.engine",
            "engines": "$.engine",
            "version": "$.version",
            "versions": "$.version",
            "size": "$.size",
            "sizes": "$.size",
            "instance_type": "$.instance_type",
            "name": "name",
            "names": "name",
            "region": "region",
            "regions": "region",
            "arn": "arn",
            "arns": "arn",
        }
        for field_name in raw_fields:
            field_name = field_name.strip()
            # Skip filler words
            if field_name in ("them", "all", "it", "list"):
                continue
            # Context-aware "type" mapping
            if field_name in ("type", "types"):
                if intent.get("service") == "ec2" and intent.get("type") == "instance":
                    field = "$.instance_type"
                elif intent.get("service") == "lambda":
                    field = "$.package_type"
                else:
                    field = "type"
            else:
                field = field_map.get(field_name, field_name)
            if field not in intent["select_fields"]:
                intent["select_fields"].append(field)


def _extract_ordering(q: str, qw: set, intent: dict) -> None:
    """Extract ORDER BY clauses."""
    # Check multi-field sort FIRST (more specific pattern)
    sort_multi = re.search(r'\bsorted?\s+by\s+([a-z_]+)\s+and\s+([a-z_]+)', q)
    if sort_multi:
        _fmap2 = {"account": "account_id", "region": "region", "name": "name", "memory": "$.memory_size"}
        for fn in (sort_multi.group(1), sort_multi.group(2)):
            intent["order_by"].append({"field": _fmap2.get(fn, fn), "direction": "asc"})
    else:
        # Single-field sort
        sort_m = re.search(r'\bsorted?\s+by\s+([a-z_]+)(?:\s+(asc(?:ending)?|desc(?:ending)?))?\b', q)
        if sort_m:
            fn = sort_m.group(1)
            direction = "desc" if sort_m.group(2) and "desc" in sort_m.group(2) else "asc"
            _fmap = {"memory": "$.memory_size", "timeout": "$.timeout", "name": "name",
                     "region": "region", "account": "account_id", "modified": "$.last_modified",
                     "recent": "$.last_modified"}
            intent["order_by"].append({"field": _fmap.get(fn, fn), "direction": direction})
    if "most recent" in q:
        intent["order_by"].append({"field": "$.last_modified", "direction": "desc"})


def _extract_grouping(q: str, qw: set, intent: dict) -> None:
    """Extract GROUP BY clauses and handle group_by conflicts."""
    # Check for "A vs B" or "A versus B" comparison pattern first
    # E.g., "Lambda functions in us-east-1 vs eu-west-1" → GROUP BY region + filter to those regions
    if " vs " in q or " versus " in q:
        # Check what's being compared
        vs_match = re.search(r'(us-[a-z]+-\d+|eu-[a-z]+-\d+|ap-[a-z]+-\d+)\s+(?:vs|versus)\s+(us-[a-z]+-\d+|eu-[a-z]+-\d+|ap-[a-z]+-\d+)', q)
        if vs_match:
            # Region comparison - add both regions to filter and GROUP BY
            region1, region2 = vs_match.group(1), vs_match.group(2)
            # Remove existing region filters first
            intent["filters"] = [f for f in intent.get("filters", []) if f.get("field") != "region"]
            # Add IN filter (represented as OR logic)
            intent["filters"].append({"field": "region", "op": "eq", "value": region1})
            intent["filters"].append({"field": "region", "op": "eq", "value": region2, "logic": "or"})
            # Add GROUP BY region
            if "region" not in intent.get("group_by", []):
                intent["group_by"].append("region")

    # Multi-field GROUP BY: "per X and Y combination"
    # E.g., "count Lambda functions per runtime and memory combination"
    combo_m = re.search(r'per\s+(\w+)\s+and\s+(\w+)\s+combination', q)
    if combo_m:
        field1, field2 = combo_m.group(1), combo_m.group(2)
        # Map field names to JSON paths
        field_map = {
            "runtime": "$.runtime", "memory": "$.memory_size", "state": "$.state",
            "status": "$.status", "engine": "$.engine", "region": "region",
            "account": "account_id", "type": "type", "service": "service",
            "architecture": "$.architecture", "billing": "$.billing_mode",
        }
        if field1 in field_map and field2 in field_map:
            if field_map[field1] not in intent["group_by"]:
                intent["group_by"].append(field_map[field1])
            if field_map[field2] not in intent["group_by"]:
                intent["group_by"].append(field_map[field2])
            # Mark as combination query for short aliases
            intent["_combination_query"] = True

    # CRITICAL: Skip if "sorted"/"top"/"first" appears OR if order_by/limit already populated
    # ("sorted by X" / "top N by X" means ORDER BY, not GROUP BY)
    has_sort_keyword = ("sorted" in q or "sort by" in q)
    has_limit_keyword = ("top " in q or "first " in q or re.search(r'\blimit\s+\d+', q))
    has_order_by = bool(intent.get("order_by"))
    has_limit = bool(intent.get("limit"))
    if not has_sort_keyword and not has_limit_keyword and not has_order_by and not has_limit:
        for phrase, field in (
            ("per region", "region"),
            ("by region", "region"),
            ("per account", "account_id"),
            ("by account", "account_id"),
            ("per service", "service"),
            ("by service", "service"),
            ("per type", "type"),  # Will be overridden below for EC2
            ("by type", "type"),
            ("per runtime", "$.runtime"),
            ("per instance type", "$.instance_type"),
            ("per instance_type", "$.instance_type"),
            ("per state", "$.state"),
            ("per status", "$.status"),
            ("per engine", "$.engine"),
            ("per billing mode", "$.billing_mode"),
            ("per cluster", "$.cluster"),
            ("per environment tag", "tags.Environment"),
            ("per owner tag", "tags.Owner"),
            ("per team tag", "tags.Team"),
            ("per project tag", "tags.Project"),
            ("per costcenter tag", "tags.CostCenter"),
            ("by architecture", "$.architecture"),
            ("per architecture", "$.architecture"),
            ("by service", "service"),
            ("per package type", "$.package_type"),
            ("per path", "$.path"),
            ("per versioning status", "$.versioning"),
            ("per versioning", "$.versioning"),
            ("per volume type", "$.volume_type"),
            ("per availability zone", "$.availability_zone"),
            ("per az", "$.availability_zone"),
            ("per namespace", "$.namespace"),
            ("per retention period", "$.retention_days"),
            ("per retention", "$.retention_days"),
        ):
            if phrase in q and field not in intent["group_by"]:
                intent["group_by"].append(field)

        # Context-aware "per type" disambiguation for EC2
        # "EC2 instances per type" means instance_type, not resource type
        if "per type" in q and "type" in intent.get("group_by", []):
            if intent.get("service") == "ec2" and intent.get("type") == "instance":
                # Replace "type" with "$.instance_type"
                intent["group_by"] = [f if f != "type" else "$.instance_type" for f in intent["group_by"]]

    # Count implies no spurious limit
    if intent["action"] == "count" or intent["group_by"]:
        intent["action"] = "count" if intent["group_by"] else intent["action"]

    # group_by conflict: remove eq filters on group_by fields
    # BUT preserve OR filter groups (used for "X vs Y" comparisons)
    if intent["group_by"]:
        intent["action"] = "count"
        gb = set(intent["group_by"])

        # Check for OR groups on each GROUP BY field
        # A field has an OR group if ANY filter on that field has logic="or"
        or_group_fields = set()
        for f in intent["filters"]:
            if f.get("op") == "eq" and f.get("logic") == "or" and f.get("field") in gb:
                or_group_fields.add(f.get("field"))

        # Remove eq filters only if NOT part of an OR group
        # If a field has an OR group, keep ALL eq filters for that field
        intent["filters"] = [
            f for f in intent["filters"]
            if not (f.get("op") == "eq" and f.get("field") in gb and f.get("field") not in or_group_fields)
        ]

        if "service" in gb:
            intent["service"] = None
            intent["type"] = None
        # When grouping by "type", clear the implicit type scope
        if "type" in gb:
            intent["type"] = None
        # When grouping by tag fields, filter out NULL to avoid counting NULL as a group
        for gb_field in gb:
            if gb_field.startswith("tags."):
                # Add filter to exclude resources without this tag
                if not any(f.get("field") == gb_field and f.get("op") == "is_not_null" for f in intent.get("filters", [])):
                    intent.setdefault("filters", []).append({"field": gb_field, "op": "is_not_null"})


def _extract_limit(q: str, qw: set, intent: dict) -> None:
    """Extract LIMIT clauses."""
    limit_m = re.search(r'\b(?:top|first|last)\s+(\d+)\b', q)
    if limit_m:
        intent["limit"] = int(limit_m.group(1))
        # "top N by X" → add order by X DESC (allow optional words between N and "by")
        top_by = re.search(r'\btop\s+\d+\s+.*?\bby\s+([a-z_]+)\b', q)
        if top_by and not intent.get("order_by"):
            fn = top_by.group(1)
            _fmap = {"memory": "$.memory_size", "timeout": "$.timeout", "name": "name"}
            intent["order_by"].append({"field": _fmap.get(fn, fn), "direction": "desc"})
    most_m = re.search(r'\b(\d+)\s+most\s+recent\b', q)
    if most_m:
        intent["limit"] = int(most_m.group(1))

    # Final safeguard: sorted queries should be LIST, not COUNT
    # If order_by is populated from "sorted by X" pattern, force action to "list"
    if intent.get("order_by") and "sorted" in q and not intent.get("group_by"):
        intent["action"] = "list"


def _builtin_parse(question: str) -> dict:
    """
    Built-in NL→intent parser. No LLM required.
    Uses _AWSMAP_TYPES as data + regex patterns. Generic, not AWS-specific.

    Orchestrates 14 specialized extractor functions for clean separation of concerns.
    """
    q = question.lower().strip()
    qw = _q_words(question)

    intent: dict = {
        "action": "list",
        "service": None,
        "type": None,
        "filters": [],
        "select_fields": [],
        "group_by": [],
        "order_by": [],
        "limit": None,
    }

    # Call specialized extractors in sequence
    _detect_action(q, qw, intent)
    _detect_service_type(q, qw, intent)
    _detect_multi_service_patterns(q, qw, intent)  # Must run after service detection
    _extract_relationship_patterns(q, qw, intent)
    _extract_region_filters(q, qw, intent)
    _extract_semantic_filters(q, qw, intent)
    _extract_name_filters(q, qw, intent)
    _extract_using_patterns(q, qw, intent)         # Generic "using X" for engines
    _extract_numeric_filters(q, qw, intent)
    _extract_generic_numeric_field_filters(q, qw, intent)  # Generic numeric fields
    _extract_keyword_value_patterns(q, qw, intent, question)  # Keyword-value patterns
    _extract_relative_time_filters(q, qw, intent)   # Relative time queries
    _extract_state_filters(q, qw, intent, question)
    _extract_tag_filters(q, qw, intent, question)
    _extract_select_fields(q, qw, intent)
    _extract_ordering(q, qw, intent)
    _extract_grouping(q, qw, intent)
    _extract_limit(q, qw, intent)

    return intent


# ---------------------------------------------------------------------------
# 12. generate_sql — public API
# ---------------------------------------------------------------------------

last_debug: list[str] = []


def _fix_partial_value_match(sql, conn, *, enable_fuzzy_fallback=True):
    """
    If exact match returns 0 rows, optionally retry with LIKE for string equality filters.

    This is a convenience feature that relaxes exact matches to substring matches
    when no results are found. It changes query semantics, so it's controlled by
    the enable_fuzzy_fallback flag.

    Args:
        sql: The SQL query to execute
        conn: Database connection
        enable_fuzzy_fallback: If True, converts = to LIKE when 0 rows found (default: True)

    Returns:
        Original SQL or modified SQL with LIKE operators

    Examples:
        - Query: "show me bucket named test" returns 0 rows
        - Without fuzzy: returns empty result
        - With fuzzy: converts name='test' to name LIKE '%test%', finds "test-bucket"
    """
    if not enable_fuzzy_fallback:
        return sql

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        if len(rows) > 0:
            return sql
    except Exception:
        return sql

    # Try converting exact matches on string fields to LIKE
    # Pattern: field='value' -> field LIKE '%value%'
    pattern = re.compile(r"((?:name|json_extract\([^)]+\)))='([^']+)'")
    matches = list(pattern.finditer(sql))
    if not matches:
        return sql

    new_sql = sql
    for m in reversed(matches):
        field_expr = m.group(1)
        value = m.group(2)
        # Skip if value already has wildcards or is a known exact value
        if "%" in value or value in ("global",):
            continue
        # Skip region, service, type comparisons
        if field_expr in ("service", "type", "region", "account_id"):
            continue
        # Skip tag exact matches (Environment=production should not become LIKE)
        if "tags" in field_expr:
            continue
        # Sanitize value: escape SQLite LIKE special chars and single quotes
        safe_value = value.replace("'", "''").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_clause = f"{field_expr} LIKE '%{safe_value}%' ESCAPE '\\'"
        new_sql = new_sql[:m.start()] + like_clause + new_sql[m.end():]

    if new_sql != sql:
        try:
            cursor = conn.execute(new_sql)
            rows = cursor.fetchall()
            if len(rows) > 0:
                return new_sql
        except Exception:
            pass

    return sql


def generate_sql(question, conn=None, account_id=None):
    """Convert a natural language question to SQL.

    Args:
        question: The natural language question
        conn: Optional SQLite connection for schema context and validation
        account_id: Optional account ID to scope queries

    Returns:
        SQL query string
    """
    debug = os.environ.get("NLQ_DEBUG", "").strip() == "1"
    global last_debug
    last_debug = []

    # Parse question using built-in parser
    intent = _builtin_parse(question)

    # Validate and normalize
    _validate_intent(intent, conn, account_id, question)

    # Build SQL
    sql = build_sql(intent, account_id)

    if debug:
        last_debug.extend([
            f"[NLQ_DEBUG] question  : {question!r}",
            f"[NLQ_DEBUG] intent    : {json.dumps(intent, default=str)}",
            f"[NLQ_DEBUG] sql       : {sql}",
        ])

    # Try fixing partial value matches (fuzzy fallback = to LIKE)
    if conn:
        sql = _fix_partial_value_match(sql, conn, enable_fuzzy_fallback=True)
        if debug:
            last_debug.append(f"FINAL: {sql}")

    return sql
