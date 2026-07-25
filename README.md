<p align="center">
  <img src="assets/logo.png" alt="cmipsmap" width="160" style="height: auto;">
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-brightgreen.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"></a>
  <a href="https://aws.amazon.com/"><img src="https://img.shields.io/badge/AWS-150%2B_Services-orange.svg" alt="AWS Services"></a>
</p>

# cmipsmap

A fast, comprehensive tool for mapping and inventorying the CMIPS AWS estate across 150+ services and all regions.

**Author:** Kiran Rajanna

<p align="center">
  <img src="assets/demo.gif" alt="cmipsmap demo: scan, SQL query, security queries, and natural-language ask" width="100%">
</p>

## Features

- **150+ AWS Services**: Covers compute, storage, database, networking, security, and more
- **Multi-Region**: Parallel scanning across all enabled regions
- **Local Database**: Every scan auto-stored in SQLite - query your inventory offline
- **SQL Query Engine**: Run SQL against your inventory history (`cmipsmap query "SELECT ..."`)
- **Pre-Built Query Library**: 30 ready-to-use security and compliance queries (`cmipsmap query -n admin-users`)
- **Natural Language Queries**: Ask questions in plain English - zero dependencies, works out of the box (`cmipsmap ask show me all EC2 without Owner tag`)
- **Examples Library**: 1381 ready-to-run questions organized by service (`cmipsmap examples lambda`)
- **Multi-Account**: Scan multiple accounts, query across all of them
- **Tag Filtering**: Filter by tags - multiple values for same tag match ANY (Owner=John OR Jane), different tags match ALL (Owner=John AND Environment=Production)
- **Beautiful HTML Reports**: Interactive reports with search, filters, dark mode, and export
- **Multiple Outputs**: JSON, CSV, and HTML formats
- **Fast**: Parallel execution with 40 workers (~2 minutes for typical accounts)
- **Drift Detection**: Compare snapshots over time - detect added, removed, and modified resources (`cmipsmap diff`)
- **Waste Detection**: Find idle or wasteful resources from collected data, no extra API calls (`cmipsmap waste`)
- **Tag Compliance**: Audit tagging coverage and score against required tags (`cmipsmap tags`)
- **Scan-Scoped Queries**: Query any point in your scan history, not just the current state (`cmipsmap query --scan`, `cmipsmap ask --scan`)
- **Console Login Support**: Works with `aws login` credential provider

## Installation

### From source

```bash
git clone https://github.com/kiranrajanna/cmipsmap.git
cd cmipsmap
pip install .
```

**Requirements:** Python 3.9+, AWS credentials configured

### Docker

Build locally:

```bash
git clone https://github.com/kiranrajanna/cmipsmap.git
cd cmipsmap
docker build -t cmipsmap .
```

### Development Installation

```bash
git clone https://github.com/kiranrajanna/cmipsmap.git
cd cmipsmap
pip install -e .
```

## Docker Usage

```bash
# Using AWS credentials file
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/output:/app/output \
  -v ~/.cmipsmap:/root/.cmipsmap \
  cmipsmap -p myprofile -o /app/output/inventory.html

# Using environment variables
docker run --rm \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -v $(pwd)/output:/app/output \
  -v ~/.cmipsmap:/root/.cmipsmap \
  cmipsmap -o /app/output/inventory.html

# Query stored inventory
docker run --rm \
  -v ~/.cmipsmap:/root/.cmipsmap \
  cmipsmap query "SELECT service, COUNT(*) as count FROM resources GROUP BY service ORDER BY count DESC"

# List available services
docker run --rm cmipsmap --list-services
```

## Usage

```bash
# Full account inventory (all services, all regions, HTML output)
cmipsmap -p myprofile

# Specific services (comma-separated or multiple -s flags)
cmipsmap -p myprofile -s ec2,s3,rds,lambda,iam

# Specific regions
cmipsmap -p myprofile -r us-east-1,eu-west-1

# Filter by tags (OR logic for same key)
cmipsmap -p myprofile -t Owner=John -t Owner=Jane -t Environment=Production

# JSON output
cmipsmap -p myprofile -f json -o inventory.json

# List available collectors
cmipsmap --list-services

# Show timing per service (useful for debugging)
cmipsmap -p myprofile --timings

# Exclude default AWS resources (default VPCs, security groups, etc.)
cmipsmap -p myprofile --exclude-defaults

# Skip local database storage
cmipsmap -p myprofile --no-db
```

## Multi-Account

Scan multiple AWS accounts. Each scan is stored in the same local database - query across all of them.

```bash
# Scan different accounts (different profiles)
cmipsmap -p production
cmipsmap -p staging
cmipsmap -p dev-account

# Query across all accounts
cmipsmap query -n resources-by-account
cmipsmap ask how many resources per account

# Scope to one account
cmipsmap query -n admin-users -a production
cmipsmap ask -a staging show me all Lambda functions
```

## Query Your Inventory

Every scan is automatically stored in a local SQLite database (`~/.cmipsmap/inventory.db`). Query it offline with raw SQL or natural language.

### SQL Queries

```bash
# Count resources per service
cmipsmap query "SELECT service, COUNT(*) as count FROM resources GROUP BY service ORDER BY count DESC"

# Find all EC2 instances in a specific region
cmipsmap query "SELECT id, name, region FROM resources WHERE service='ec2' AND type='instance'"

# View scan history
cmipsmap query "SELECT * FROM scans ORDER BY timestamp DESC"

# JSON or CSV output
cmipsmap query "SELECT * FROM resources WHERE service='s3'" -f json
cmipsmap query "SELECT service, id, name FROM resources" -f csv

# Query tags (filter to resources that have the tag)
cmipsmap query "SELECT id, name, json_extract(tags, '$.Owner') as owner FROM resources WHERE service='ec2' AND json_extract(tags, '$.Owner') IS NOT NULL"
```

**More SQL examples:** See `examples/queries/*.sql` for ready-to-use query templates you can customize.

### Pre-Built Query Library

cmipsmap ships with 30 pre-built queries for common security, compliance, and operational tasks. No SQL knowledge required.

```bash
# List all available queries
cmipsmap query --list

# Run a named query
cmipsmap query -n admin-users
cmipsmap query -n users-without-mfa
cmipsmap query -n open-security-groups
cmipsmap query -n untagged-resources

# Pass parameters (find resources with Owner tag)
cmipsmap query -n resources-by-tag -P tag=Owner

# Multiple parameters (find EC2 missing Environment tag)
cmipsmap query -n missing-tag -P tag=Environment -P service=ec2

# Scope to a specific account
cmipsmap query -n admin-users -a production

# Show query SQL without running it
cmipsmap query --show admin-users

# Run SQL from a file
cmipsmap query -F my-query.sql
```

**Parameter format:** Use `-P parameter=value` where `parameter` is the query parameter name (e.g., `tag`, `service`) and `value` is what you're searching for. Example: `-P tag=Owner` means "filter by the Owner tag" (NOT `-P Owner=SomeValue`).

**Available queries:**

| Query | Description | Example |
|-------|-------------|---------|
| **IAM / Security** | | |
| `admin-users` | IAM users with admin permissions (direct + via group) | `cmipsmap query -n admin-users` |
| `admin-roles` | IAM roles with admin permissions | `cmipsmap query -n admin-roles` |
| `users-without-mfa` | IAM users without MFA enabled | `cmipsmap query -n users-without-mfa` |
| `iam-inactive-users` | IAM users with no login and no access keys | `cmipsmap query -n iam-inactive-users` |
| `old-access-keys` | IAM users with access keys | `cmipsmap query -n old-access-keys` |
| `cross-account-roles` | IAM roles with trust policies allowing external accounts | `cmipsmap query -n cross-account-roles` |
| `open-security-groups` | Security groups with 0.0.0.0/0 ingress rules | `cmipsmap query -n open-security-groups` |
| `secrets-no-rotation` | Secrets Manager secrets without auto-rotation | `cmipsmap query -n secrets-no-rotation` |
| **S3** | | |
| `public-s3-buckets` | S3 buckets with public access enabled | `cmipsmap query -n public-s3-buckets` |
| `encryption-status` | S3 buckets and their encryption configuration | `cmipsmap query -n encryption-status` |
| `s3-no-versioning` | S3 buckets without versioning | `cmipsmap query -n s3-no-versioning` |
| `s3-no-logging` | S3 buckets without access logging | `cmipsmap query -n s3-no-logging` |
| **EC2 / EBS** | | |
| `stopped-instances` | EC2 instances in stopped state | `cmipsmap query -n stopped-instances` |
| `unused-volumes` | EBS volumes not attached to any instance | `cmipsmap query -n unused-volumes` |
| `ebs-unencrypted` | EBS volumes without encryption | `cmipsmap query -n ebs-unencrypted` |
| `unused-eips` | Elastic IPs not associated with any instance | `cmipsmap query -n unused-eips` |
| `default-vpcs` | Default VPCs across all regions | `cmipsmap query -n default-vpcs` |
| **RDS** | | |
| `rds-public` | RDS instances with public access enabled | `cmipsmap query -n rds-public` |
| `rds-unencrypted` | RDS instances without encryption | `cmipsmap query -n rds-unencrypted` |
| `rds-no-multi-az` | RDS instances without Multi-AZ | `cmipsmap query -n rds-no-multi-az` |
| `rds-engines` | RDS instances grouped by engine | `cmipsmap query -n rds-engines` |
| **Lambda** | | |
| `lambda-runtimes` | Lambda functions grouped by runtime | `cmipsmap query -n lambda-runtimes` |
| `lambda-high-memory` | Lambda functions with memory > 512 MB | `cmipsmap query -n lambda-high-memory` |
| **Tags** | | |
| `untagged-resources` | Resources with no tags | `cmipsmap query -n untagged-resources` |
| `missing-tag` | Resources missing a specific tag | `cmipsmap query -n missing-tag -P tag=Owner` |
| `resources-by-tag` | Resources that have a specific tag | `cmipsmap query -n resources-by-tag -P tag=Owner` |
| **Inventory** | | |
| `resources-by-service` | Resource count per service | `cmipsmap query -n resources-by-service` |
| `resources-by-region` | Resource count per region | `cmipsmap query -n resources-by-region` |
| `resources-by-account` | Resource count per account | `cmipsmap query -n resources-by-account` |
| `resources-per-account-service` | Resource count per account per service | `cmipsmap query -n resources-per-account-service` |

You can also add your own queries by placing `.sql` files in `~/.cmipsmap/queries/`. Use the same header format as the built-in queries (`-- name:`, `-- description:`, `-- params:`).

### Natural Language Queries

Ask questions about your inventory in plain English using `cmipsmap ask`. **No setup required** - works out of the box with a built-in zero-dependency parser.

```bash
cmipsmap ask how many resources per region
cmipsmap ask show me all EC2 instances without Owner tag
cmipsmap ask which S3 buckets are in eu-west-1
cmipsmap ask what services have the most resources
```

cmipsmap translates your question to SQL using a **built-in parser** (zero dependencies), shows you the generated query, and displays the results.

### Examples Library

Browse and run 1381 pre-built questions organized by AWS service using `cmipsmap examples`.

```bash
# List all services with question counts
cmipsmap examples

# Browse questions for a service
cmipsmap examples lambda

# Run a specific question by number
cmipsmap examples lambda 5

# Search across all questions
cmipsmap examples --search "public"
cmipsmap examples --search "encryption"
```

#### Multi-Account Queries

When multiple accounts have been scanned, `cmipsmap ask` queries all of them by default. Use `-a` to scope to a single account:

```bash
# Query across all accounts
cmipsmap ask show me all IAM users

# Scope to one account
cmipsmap ask -a production show me Lambda functions
```

## Drift Detection

Compare snapshots of your AWS inventory over time to detect what changed - resources added, removed, or modified.

```bash
# What did the most recent scan change? (no arguments: previous scan vs current)
cmipsmap diff

# What changed in the last 7 days?
cmipsmap diff --from 7d

# Compare two specific dates
cmipsmap diff --from 2026-01-15 --to 2026-02-09

# Scope to specific services
cmipsmap diff --from 30d -s ec2,s3

# Scope to a specific account (by profile name, alias, or account ID)
cmipsmap diff --from 7d -a production -r us-east-1

# Show only added or removed resources
cmipsmap diff --from 7d --type added
cmipsmap diff --from 7d --type removed

# Summary only (no resource details)
cmipsmap diff --from 7d --summary

# Ignore tag-only changes
cmipsmap diff --from 30d --ignore-tags

# JSON output
cmipsmap diff --from 7d -f json -o drift-report.json

# HTML report (interactive, with filters and dark mode)
cmipsmap diff --from 7d -f html -o drift-report.html
```

**How it works:** cmipsmap reconstructs point-in-time snapshots from your scan history. For each `(account, service)`, it finds the latest scan at or before the given date, then compares the two snapshots field by field. This correctly handles partial scans - if you scanned EC2 on Monday and S3 on Tuesday, each service uses its own latest scan.

With no `--from`, `cmipsmap diff` compares the state before the most recent scan against the current state, so you can see exactly what your latest scan changed. `--to` without `--from` defaults `--from` to the scan immediately before `--to`.

**Relative dates:** `7d`, `30d`, `90d`, `yesterday`, `today`, or exact dates like `2026-01-15`.

**Change types:**
- **Added** - resource exists in the newer snapshot but not the older one
- **Removed** - resource exists in the older snapshot but not the newer one
- **Modified** - resource exists in both but details, tags, or name changed (with field-level diffs)

## Waste Detection

Find idle or potentially wasteful resources from the data cmipsmap already collected. No new AWS API calls - the rules run over your latest stored snapshot.

```bash
# Run all rules against the current snapshot
cmipsmap waste

# Counts per rule only
cmipsmap waste --summary

# Scope to one account (by profile name, alias, or account ID)
cmipsmap waste -a production

# Run only specific rules
cmipsmap waste -t unattached-ebs -t available-eni

# Change the age threshold for snapshots and AMIs (default 90 days)
cmipsmap waste --min-age-days 180

# Include default AWS resources (excluded by default)
cmipsmap waste --include-defaults

# HTML report (interactive, with filters and dark mode)
cmipsmap waste -f html -o waste.html
```

**Rules:**

| Rule key | What it flags |
|----------|---------------|
| `unattached-ebs` | EBS volumes in the `available` state |
| `unassociated-eip` | Elastic IPs not attached to an instance or network interface |
| `available-eni` | Network interfaces in the `available` (detached) state |
| `idle-target-group` | Target groups with no registered targets |
| `empty-classic-elb` | Classic load balancers with no instances |
| `old-snapshot` | EBS snapshots older than `--min-age-days` (default 90) |
| `old-ami` | AMIs older than `--min-age-days` (default 90) |
| `stopped-instance` | EC2 instances in the `stopped` state |

cmipsmap reports counts and the resources to act on. It does not estimate dollar costs. Output is `table` (default), `json`, or `html`; `is_default` resources are excluded unless you pass `--include-defaults`.

## Tag Compliance

Audit tagging coverage across your inventory and score it against a set of required tags. Operates on already-collected data.

```bash
# Coverage of "has at least one tag"
cmipsmap tags

# Compliance against required tags
cmipsmap tags -R Owner,Environment,CostCenter

# Scope to an account and service, list only non-compliant resources
cmipsmap tags -a production -s ec2 --noncompliant-only

# List only resources with zero tags
cmipsmap tags --untagged-only

# Score only, no resource listing
cmipsmap tags -R Owner --summary

# HTML report
cmipsmap tags -R Owner,Environment -f html -o tag-compliance.html
```

The report shows an overall compliance score, per-required-tag coverage (so you can see which tag is the gap), a per-service breakdown, and the list of non-compliant resources with their missing tags.

- Required tags come from `-R/--required` (comma-separated or repeatable) or the `required_tags` config key. With neither set, compliance falls back to "has at least one tag".
- A blank tag value (for example `Owner=`) counts as missing.
- `is_default` resources are excluded by default; pass `--include-defaults` to keep them.
- Set a default required set once: `cmipsmap config set required_tags Owner,Environment,CostCenter`.
- Output is `table` (default), `json`, or `html`.

## Querying a Specific Scan

By default `query` and `ask` run against the current snapshot (`is_current`). Use `--scan` to target any scan in your history.

```bash
# List stored scans
cmipsmap query --list-scans

# Run a named query against the previous scan
cmipsmap query --scan previous -n admin-users

# Raw SQL against the latest scan (use the {scan_filter} placeholder)
cmipsmap query --scan latest "SELECT service, COUNT(*) FROM resources WHERE {scan_filter} GROUP BY service"

# Natural language against the first (oldest) scan
cmipsmap ask --scan first show me ec2 instances
```

Selectors: `latest`, `previous`, `first`, or an explicit `<scan_id>` (see `--list-scans`). Named queries, files, and `ask` apply the scope automatically. For raw inline SQL, include the `{scan_filter}` placeholder where the scope should go; using `--scan` on raw SQL without the placeholder reports an error instead of running an unscoped query.

## Demo Database

Generate a realistic synthetic database to try cmipsmap without needing an AWS account. Covers all 150+ services, multiple accounts, and multiple scans with drift.

```bash
# Generate with defaults (3 accounts, 3 scans, ~12,000 resources)
cmipsmap demo

# Custom options
cmipsmap demo --accounts 2 --scans 5 --db ./demo.db

# Overwrite existing
cmipsmap demo --force
```

After generating, use `--db` to point any command at the demo database:

```bash
cmipsmap query --db ~/.cmipsmap/demo.db -n admin-users
cmipsmap ask --db ~/.cmipsmap/demo.db show me all EC2 instances
cmipsmap diff --db ~/.cmipsmap/demo.db --from 30d
cmipsmap examples lambda 5 --db ~/.cmipsmap/demo.db
```

Or set it as the default database:

```bash
cmipsmap config set db ~/.cmipsmap/demo.db
```

### Demo Options (`cmipsmap demo`)

| Option | Description |
|--------|-------------|
| `--db` | Database path (default: `~/.cmipsmap/demo.db`) |
| `--accounts` | Number of accounts to generate (1-5, default: 3) |
| `--scans` | Number of scans per account for drift (1-5, default: 3) |
| `--seed` | Random seed for reproducibility (default: 42) |
| `--force` | Overwrite existing demo database |

## CLI Options

### Scan Options

| Option | Description |
|--------|-------------|
| `-p, --profile` | AWS profile name |
| `-r, --region` | Region(s) to scan (comma-separated or multiple flags) |
| `-s, --services` | Service(s) to scan (comma-separated or multiple flags) |
| `-t, --tag` | Filter by tag Key=Value (multiple allowed) |
| `-f, --format` | Output format: `html` (default), `json`, `csv` |
| `-o, --output` | Output file path |
| `-w, --workers` | Parallel workers (default: 40) |
| `-q, --quiet` | Suppress progress output |
| `--timings` | Show timing summary per service |
| `--include-global` | Include global services when filtering by non-global regions |
| `--exclude-defaults` | Exclude default AWS resources (default VPCs, security groups, etc.) |
| `--no-db` | Skip local database storage |
| `--list-services` | List available service collectors |

### Query Options (`cmipsmap query`)

| Option | Description |
|--------|-------------|
| `-n, --name` | Run a pre-built named query |
| `-F, --file` | Run SQL from a file |
| `-l, --list` | List available pre-built queries |
| `-S, --show` | Show SQL of a named query without running it |
| `-P, --param` | Parameter for named query (`key=value`, multiple allowed) |
| `-a, --account` | Scope to an account (account ID, account alias, or AWS profile) |
| `--scan` | Scope to a scan: `latest`, `previous`, `first`, or a `<scan_id>` (raw SQL needs the `{scan_filter}` placeholder) |
| `--list-scans` | List stored scans and exit |
| `--db` | Database path (default: `~/.cmipsmap/inventory.db`) |
| `-f, --format` | Output format: `table` (default), `json`, `csv` |

### Ask Options (`cmipsmap ask`)

| Option | Description |
|--------|-------------|
| `-a, --account` | Scope to an account (account ID, account alias, or AWS profile) |
| `--scan` | Scope to a scan: `latest`, `previous`, `first`, or a `<scan_id>` |
| `--db` | Database path (default: `~/.cmipsmap/inventory.db`) |

### Diff Options (`cmipsmap diff`)

| Option | Description |
|--------|-------------|
| `--from` | Start date for comparison. Supports: `YYYY-MM-DD`, `7d`, `30d`, `yesterday`, `today`. If omitted, compares the previous scan against the current state |
| `--to` | End date (default: current state). Same date formats as `--from` |
| `-a, --account` | Scope to an account (account ID, alias, or profile) |
| `-s, --service` | Service(s) to compare (comma-separated or multiple flags) |
| `-r, --region` | Region(s) to compare (comma-separated or multiple flags) |
| `--type` | Show only one change type: `all` (default), `added`, `removed`, or `modified` |
| `--summary` | Show summary counts only, no resource details |
| `--ignore-tags` | Ignore tag-only changes |
| `-f, --format` | Output format: `table` (default), `json`, `html` |
| `-o, --output` | Output file path |
| `--db` | Database path (default: `~/.cmipsmap/inventory.db`) |

### Waste Options (`cmipsmap waste`)

| Option | Description |
|--------|-------------|
| `-a, --account` | Scope to an account (account ID, alias, or profile) |
| `-t, --type` | Run only specific rule key(s) (comma-separated or multiple flags) |
| `--min-age-days` | Age threshold for `old-snapshot` and `old-ami` (default: 90) |
| `--include-defaults` | Include default AWS resources (excluded by default) |
| `--summary` | Show counts per rule only, no resource listing |
| `-f, --format` | Output format: `table` (default), `json`, `html` |
| `-o, --output` | Output file path |
| `--db` | Database path (default: `~/.cmipsmap/inventory.db`) |

### Tags Options (`cmipsmap tags`)

| Option | Description |
|--------|-------------|
| `-R, --required` | Required tag key(s) (comma-separated or repeatable). Falls back to the `required_tags` config key |
| `-a, --account` | Scope to an account (account ID, alias, or profile) |
| `-s, --service` | Scope to service(s) (comma-separated or multiple flags) |
| `--untagged-only` | List only resources with zero tags |
| `--noncompliant-only` | List only resources missing a required tag |
| `--include-defaults` | Include default AWS resources (excluded by default) |
| `--summary` | Show scores only, no resource listing |
| `-f, --format` | Output format: `table` (default), `json`, `html` |
| `-o, --output` | Output file path |
| `--db` | Database path (default: `~/.cmipsmap/inventory.db`) |

### Examples Options (`cmipsmap examples`)

| Argument / Option | Description |
|-------------------|-------------|
| `<service>` | Show questions for a specific service |
| `<service> <number>` | Run question #N against the database |
| `-s, --search` | Search all questions by keyword |
| `--db` | Database path (default: `~/.cmipsmap/inventory.db`) |

### Config Commands (`cmipsmap config`)

Set persistent defaults so you don't have to repeat CLI flags. CLI flags always override config values.

Only the keys listed below are accepted - unknown keys and invalid values are rejected. If the config file is manually edited and contains invalid entries, `cmipsmap config list` detects them, warns you, and auto-cleans the file.

| Command | Description |
|---------|-------------|
| `cmipsmap config set key value` | Set a configuration value (validated) |
| `cmipsmap config get key` | Get a configuration value |
| `cmipsmap config list` | List all values (detects and cleans invalid entries) |
| `cmipsmap config delete key` | Delete a configuration value |

**Available config keys (only these are accepted):**

| Key | Applies to | Description | Example |
|-----|-----------|-------------|---------|
| `profile` | `cmipsmap` (scan) | Default AWS profile | `cmipsmap config set profile production` |
| `regions` | `cmipsmap` (scan) | Default regions (comma-separated) | `cmipsmap config set regions us-east-1,eu-west-1` |
| `services` | `cmipsmap` (scan) | Default services (comma-separated) | `cmipsmap config set services ec2,s3,lambda` |
| `format` | `cmipsmap` (scan) | Default output format (`html`, `json`, `csv`) | `cmipsmap config set format json` |
| `workers` | `cmipsmap` (scan) | Default parallel workers | `cmipsmap config set workers 20` |
| `exclude_defaults` | `cmipsmap` (scan) | Exclude default AWS resources (`true`/`false`) | `cmipsmap config set exclude_defaults true` |
| `db` | `query`, `ask` | Default database path | `cmipsmap config set db /path/to/inventory.db` |
| `query_format` | `query` | Default query output format (`table`, `json`, `csv`) | `cmipsmap config set query_format csv` |
| `required_tags` | `tags` | Default required tag keys (comma-separated) | `cmipsmap config set required_tags Owner,Environment,CostCenter` |

```bash
# Set your usual profile and regions
cmipsmap config set profile production
cmipsmap config set regions us-east-1,eu-west-1

# Now just run:
cmipsmap
# Equivalent to: cmipsmap -p production -r us-east-1,eu-west-1

# CLI flags still override config:
cmipsmap -p staging    # Uses staging profile, but regions from config
```

## Shell Completion

cmipsmap supports tab completion for bash, zsh, and fish. Complete subcommands, service names, regions, AWS profiles, query names, account names, and config keys.

```bash
# Bash
eval "$(cmipsmap completion bash)"     # add to ~/.bashrc

# Zsh
eval "$(cmipsmap completion zsh)"      # add to ~/.zshrc

# Fish
cmipsmap completion fish > ~/.config/fish/completions/cmipsmap.fish
```

**What gets completed:**

| Context | Completions |
|---------|-------------|
| `cmipsmap <TAB>` | Subcommands: ask, config, completion, demo, diff, examples, query |
| `cmipsmap -s <TAB>` | Service names (ec2, s3, lambda, ...) |
| `cmipsmap -r <TAB>` | AWS region names |
| `cmipsmap -p <TAB>` | AWS profile names from ~/.aws/credentials and ~/.aws/config |
| `cmipsmap query -n <TAB>` | Pre-built query names |
| `cmipsmap query -a <TAB>` | Account aliases, profiles, and IDs from the database |
| `cmipsmap config set <TAB>` | Valid configuration keys |
| `cmipsmap examples <TAB>` | Service names from the examples library |

> **Important: Bash version requirement.** Shell completion requires **Bash 4.4 or newer**. macOS ships with Bash 3.2 (from 2007, frozen due to GPLv3 licensing) which is **not supported**. To fix this on macOS:
>
> ```bash
> # Install modern Bash via Homebrew
> brew install bash
>
> # Add it to allowed shells
> sudo sh -c 'echo /opt/homebrew/bin/bash >> /etc/shells'
>
> # Set it as your default shell
> chsh -s /opt/homebrew/bin/bash
> ```
>
> Alternatively, macOS users can use **zsh** (the default shell since macOS Catalina) which works out of the box.

## Supported Services

| Category | Services |
|----------|----------|
| **Compute** | ec2, lambda, ecs, eks, ecr, ecr-public, lightsail, autoscaling, application-autoscaling, elasticbeanstalk, batch, apprunner, imagebuilder |
| **Storage** | s3, efs, fsx, backup, datasync, dlm, storagegateway |
| **Database** | rds, dynamodb, elasticache, memorydb, docdb, neptune, redshift, redshift-serverless, keyspaces, opensearch, opensearch-serverless, dax, dsql, timestream-influxdb |
| **Networking** | vpc, elbv2, elb, route53, route53resolver, route53domains, cloudfront, globalaccelerator, apigateway, apigatewayv2, appsync, directconnect, network-firewall, servicediscovery, vpc-lattice, networkmanager |
| **Security** | iam, sso, kms, secretsmanager, acm, acm-pca, wafv2, guardduty, inspector2, securityhub, ds, cognito, accessanalyzer, macie2, detective, shield, fms, cloudhsmv2, auditmanager, securitylake |
| **Management & Monitoring** | cloudwatch, logs, cloudtrail, ssm, config, sns, sqs, events, xray, grafana, amp, ce, budgets, compute-optimizer, service-quotas, resource-groups, health, synthetics, appconfig, organizations, servicecatalog, resiliencehub |
| **Serverless** | stepfunctions, kinesis, firehose, kafka, serverlessrepo, eventbridge-scheduler, eventbridge-pipes, schemas |
| **Developer Tools** | cloudformation, codeartifact, codebuild, codepipeline, codedeploy, devicefarm |
| **Analytics** | athena, glue, mwaa, lakeformation, emr, emr-serverless, cleanrooms, quicksight, datazone |
| **AI/ML** | sagemaker, bedrock, lexv2, rekognition, textract, transcribe, translate, comprehend, polly, personalize, kendra, frauddetector |
| **Media** | mediaconvert, mediaconnect, mediapackage, medialive, mediastore, mediatailor, ivs |
| **Migration & Transfer** | transfer, dms |
| **End User Computing** | workspaces, amplify, connect |
| **IoT** | iot, iotsitewise |
| **Other** | ram, resource-explorer-2, mq, sesv2, appflow, gamelift, outposts, fis, location |

For detailed resource types per service, see [SERVICES.md](SERVICES.md).

## Output Formats

### HTML (Default)
Interactive report with:
- Dashboard with resource counts and charts
- Global search across all resources
- Filter by service and region
- Collapsible service sections
- Click to copy ARN/ID
- Clickable tag badges (shows all tags)
- Dark/light mode toggle
- Export filtered view to CSV
- Print-friendly

### JSON
```json
{
  "metadata": {
    "account_id": "123456789012",
    "timestamp": "2024-12-24 15:30:00 UTC",
    "resource_count": 1590
  },
  "resources": [
    {
      "service": "ec2",
      "type": "instance",
      "id": "i-1234567890abcdef0",
      "arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
      "name": "my-instance",
      "region": "us-east-1",
      "is_default": false,
      "details": {...},
      "tags": {"Owner": "John", "Environment": "Production"}
    }
  ]
}
```

### CSV
Flat format with columns: service, type, id, name, region, arn, is_default, tags

## Tag Filtering

```bash
# Single tag
cmipsmap -t Environment=Production

# Multiple values for same key (OR logic)
cmipsmap -t Owner=John -t Owner=Jane
# Returns resources where Owner is "John" OR "Jane"

# Multiple keys (AND logic)
cmipsmap -t Owner=John -t Environment=Production
# Returns resources where Owner is "John" AND Environment is "Production"

# Combined
cmipsmap -t Owner=John -t Owner=Jane -t Environment=Production
# Returns resources where (Owner is "John" OR "Jane") AND Environment is "Production"
```

## Global vs Regional Services

AWS has two types of services:
- **Regional services** (EC2, RDS, Lambda, etc.) - Resources exist in specific regions
- **Global services** (IAM, Route53, CloudFront, etc.) - Resources are account-wide, not region-specific

### How cmipsmap handles global services

When you filter by region, cmipsmap intelligently includes global services based on their **control plane location**:

| Command | Behavior |
|---------|----------|
| `cmipsmap` (no region) | All services (regional + global) |
| `cmipsmap -r us-east-1` | Regional in us-east-1 + global services with us-east-1 control plane |
| `cmipsmap -r us-west-2` | Regional in us-west-2 + global services with us-west-2 control plane |
| `cmipsmap -r eu-west-1` | Regional in eu-west-1 only (no global services) |
| `cmipsmap -r eu-west-1 --include-global` | Regional in eu-west-1 + all global services |

### Global services by control plane

Based on [AWS Global Services documentation](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/global-services.html):

| Control Plane | Global Services |
|---------------|-----------------|
| **us-east-1** | IAM, Organizations, Route53, Route53 Domains, CloudFront, Shield, Budgets, Cost Explorer, Health |
| **us-west-2** | Network Manager, Global Accelerator |

### S3 buckets

S3 bucket names are globally unique, but **each bucket has a specific region**. cmipsmap treats S3 as a regional service:

```bash
# Only S3 buckets in eu-west-1
cmipsmap -r eu-west-1 -s s3

# All S3 buckets
cmipsmap -s s3
```

## Performance

Scans **150+ services** across all regions in parallel.

| Account Size | Resources | Estimated Time |
|--------------|-----------|----------------|
| Small | <500 | ~1.5 minutes |
| Medium | 500-5,000 | ~2 minutes |
| Large | 5,000-20,000 | ~3-5 minutes |
| Enterprise | 20,000+ | ~5-10 minutes |

**Tuning Options:**
```bash
# Increase parallelism for faster scans
cmipsmap -p myprofile -w 50

# Reduce parallelism for rate-limited accounts
cmipsmap -p myprofile -w 20

# Scan specific services only (much faster)
cmipsmap -p myprofile -s ec2,s3,lambda,iam

# Scan specific regions only
cmipsmap -p myprofile -r us-east-1,eu-west-1
```

**Why is the scan fast?**
- Parallel execution with configurable workers (default: 40)
- Region-aware collectors skip unsupported regions automatically
- Global services (IAM, Route53, etc.) collected once, not per-region
- Smart region filtering excludes global services when not relevant
- Optimized API calls (batch operations where available)

## IAM Permissions

Only scanning (`cmipsmap`) calls AWS, and it needs read-only access to the services you want to inventory. The analysis commands (`query`, `ask`, `diff`, `waste`, `tags`) run entirely against your local database and require no AWS permissions.

Beyond the per-service read actions, a scan calls `sts:GetCallerIdentity`, `account:ListRegions` (to discover enabled regions; falls back to a built-in region list if denied), and `iam:ListAccountAliases` (for the account alias).

### Recommended: ReadOnlyAccess plus a small supplement

Attach the AWS managed [`ReadOnlyAccess`](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ReadOnlyAccess.html) policy. It is maintained by AWS and covers the large majority of cmipsmap's read calls.

`ReadOnlyAccess` does not cover everything, though: it lags on some newer services (Amazon Location, MediaTailor, Timestream for InfluxDB, Textract adapters) and deliberately omits a few read actions (for example `glue:GetConnections`). cmipsmap calls 26 read actions that `ReadOnlyAccess` does not grant. They were computed by diffing cmipsmap's exact API calls against the live `ReadOnlyAccess` document, so the list is the precise difference, not a guess.

Attach this supplemental policy alongside `ReadOnlyAccess`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "cmipsmapSupplementalReadOnly",
      "Effect": "Allow",
      "Action": [
        "airflow:GetEnvironment",
        "bedrock:ListTagsForResource",
        "codeartifact:ListPackageGroups",
        "fms:GetResourceSet",
        "fms:ListResourceSets",
        "geo:ListGeofenceCollections",
        "geo:ListMaps",
        "geo:ListPlaceIndexes",
        "geo:ListRouteCalculators",
        "geo:ListTrackers",
        "glue:GetConnections",
        "mediatailor:ListChannels",
        "mediatailor:ListPlaybackConfigurations",
        "mediatailor:ListSourceLocations",
        "quicksight:ListAnalyses",
        "quicksight:ListDashboards",
        "quicksight:ListDataSets",
        "quicksight:ListDataSources",
        "quicksight:ListTagsForResource",
        "rekognition:DescribeCollection",
        "textract:GetAdapter",
        "textract:ListAdapters",
        "timestream-influxdb:GetDbInstance",
        "timestream-influxdb:ListDbInstances",
        "timestream-influxdb:ListDbParameterGroups",
        "timestream-influxdb:ListTagsForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

Attach both to a role (or use `attach-user-policy` for a user):

```bash
# 1. Attach the AWS managed ReadOnlyAccess policy
aws iam attach-role-policy \
  --role-name YourRoleName \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# 2. Create the supplemental policy from the JSON above and attach it
aws iam create-policy \
  --policy-name cmipsmap-supplemental-readonly \
  --policy-document file://cmipsmap-supplemental-readonly.json

aws iam attach-role-policy \
  --role-name YourRoleName \
  --policy-arn arn:aws:iam::<account-id>:policy/cmipsmap-supplemental-readonly
```

Every collector call is wrapped so a denied permission never stops a scan: the affected resources are simply skipped. The supplement only removes those blind spots so the inventory is complete. All 26 actions are read-only.

### Alternative: no managed policy

If you cannot use `ReadOnlyAccess`, grant read actions (`Describe*`, `List*`, `Get*`, plus `BatchGet*`/`Search*` where applicable) for the services cmipsmap scans, together with the supplemental actions above. The full standalone list covers about 150 service prefixes; see the [IAM Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html) for per-service read actions.

## What's NOT Collected

This tool only collects **user-owned resources**, excluding:
- AWS-managed policies (only customer-managed)
- AWS-managed KMS keys (only customer-managed)
- Default parameter groups and option groups
- AWS service-linked roles
- Reserved instance offerings (pricing catalog)
- Foundation models (Bedrock catalog)
- Automated backups (only manual snapshots)
- AWS system keyspaces (Keyspaces: `system_*`)
- AWS default queues/groups (MediaConvert, X-Ray)
- AWS managed domain lists (Route53 Resolver: `AWSManagedDomains*`)
- Default data lake settings (Lake Formation)

**Default VPC resources** (default VPCs, subnets, security groups, route tables, internet gateways, NACLs, DHCP options) are collected by default and marked with a "DEFAULT" badge in HTML reports. Use `--exclude-defaults` to filter them out.

See [SERVICES.md](SERVICES.md#filtered-resources) for the complete list of filtered resources.

## Why a Built-In NLQ Parser Instead of AI/LLM?

We evaluated three approaches for natural language queries:

| Approach | Accuracy | Cost | Latency | Offline |
|----------|----------|------|---------|---------|
| **Ollama (local LLMs)** | ~80% | Free | Slow (seconds) | Yes |
| **OpenAI / Anthropic APIs** | ~95% | Pay per query | Network dependent | No |
| **Built-in parser (cmipsmap)** | **100%** | **Free** | **Instant** | **Yes** |

- **Ollama** models are free and run locally, but when tested against real AWS inventory queries, accuracy was around 80% - one in five queries would generate wrong SQL or fail silently. Not acceptable for a CLI tool where users trust the output.
- **OpenAI / Anthropic APIs** produce better results, but require API keys, cost money per query, and depend on network connectivity. Not ideal for an infrastructure tool that should just work.
- **Built-in parser** is a zero-dependency, deterministic NL-to-SQL engine. It's tested against **1500 realistic test questions with a 100% pass rate** (separate from the 1381 examples library). It covers listing, counting, aggregation, region filters, negation, tags, multi-service queries, synonyms, typo tolerance, relative time, numeric fields, keyword-value patterns, and 150+ AWS services. No API keys, no network, no cost, instant results.

The 1500 test questions (used during development to validate the parser) are designed to cover the vast majority of real-world use cases. The parser also includes typo tolerance, synonym support, and fuzzy matching to handle natural variations in how people phrase questions.

> **Found a bug or an inaccurate query?** Please [open an issue](https://github.com/kiranrajanna/cmipsmap/issues) and report it! Every report helps improve the parser for everyone. **If you have ideas for a better approach than the built-in NLQ, we're always open to suggestions.**

## Support

- **Documentation**: Check this README and [SERVICES.md](SERVICES.md)
- **Issues**: Report bugs via [GitHub Issues](https://github.com/kiranrajanna/cmipsmap/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/kiranrajanna/cmipsmap/discussions)

## Author

**Kiran Rajanna**

## Credits

cmipsmap is derived from [awsmap](https://github.com/TocConsulting/awsmap) by Toc Consulting, rebranded and adapted for CMIPS.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

