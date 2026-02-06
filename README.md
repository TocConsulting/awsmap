<p align="center">
  <img src="assets/logo.png" alt="AWS Inventory Tool" style="max-width: 100%; height: auto;">
</p>

<p align="center">
  <a href="https://pypi.org/project/awsmap/"><img src="https://img.shields.io/pypi/v/awsmap.svg" alt="PyPI version"></a>
  <a href="https://pepy.tech/project/awsmap"><img src="https://static.pepy.tech/badge/awsmap" alt="Downloads"></a>
  <a href="https://hub.docker.com/r/tarekcheikh/awsmap"><img src="https://img.shields.io/docker/v/tarekcheikh/awsmap?label=docker" alt="Docker"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-brightgreen.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="https://aws.amazon.com/"><img src="https://img.shields.io/badge/AWS-140%2B_Services-orange.svg" alt="AWS Services"></a>
</p>

# awsmap

A fast, comprehensive tool for mapping and inventorying AWS resources across 140+ services and all regions.

## Features

- **140+ AWS Services**: Covers compute, storage, database, networking, security, and more
- **Multi-Region**: Parallel scanning across all enabled regions
- **Tag Filtering**: Filter resources by tags with OR logic for same key, AND logic across keys
- **Beautiful HTML Reports**: Interactive reports with search, filters, dark mode, and export
- **Multiple Outputs**: JSON, CSV, and HTML formats
- **Fast**: Parallel execution with 40 workers (~2 minutes for typical accounts)
- **Console Login Support**: Works with `aws login` credential provider

## Installation

### PyPI

```bash
pip install awsmap
```

**Requirements:** Python 3.8+, AWS credentials configured

### Docker

```bash
docker pull tarekcheikh/awsmap
```

Or build locally:

```bash
git clone https://github.com/TocConsulting/awsmap.git
cd awsmap
docker build -t awsmap .
```

### Development Installation

```bash
git clone https://github.com/TocConsulting/awsmap.git
cd awsmap
pip install -e .
```

## Docker Usage

```bash
# Using AWS credentials file
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/output:/app/output \
  awsmap -p myprofile -o /app/output/inventory.html

# Using environment variables
docker run --rm \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -v $(pwd)/output:/app/output \
  awsmap -o /app/output/inventory.html

# List available services
docker run --rm awsmap --list-services
```

## Usage

```bash
# Full account inventory (all services, all regions, HTML output)
awsmap -p myprofile

# Specific services (comma-separated or multiple -s flags)
awsmap -p myprofile -s ec2,s3,rds,lambda,iam

# Specific regions
awsmap -p myprofile -r us-east-1,eu-west-1

# Filter by tags (OR logic for same key)
awsmap -p myprofile -t Owner=John -t Owner=Jane -t Environment=Production

# JSON output
awsmap -p myprofile -f json -o inventory.json

# List available collectors
awsmap --list-services

# Show timing per service (useful for debugging)
awsmap -p myprofile --timings
```

## CLI Options

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
| `--list-services` | List available service collectors |

## Supported Services

| Category | Services |
|----------|----------|
| **Compute** | ec2, lambda, ecs, eks, ecr, ecr-public, lightsail, autoscaling, application-autoscaling, elasticbeanstalk, batch, apprunner, imagebuilder |
| **Storage** | s3, efs, fsx, backup, datasync, dlm, storagegateway |
| **Database** | rds, dynamodb, elasticache, memorydb, docdb, neptune, redshift, redshift-serverless, keyspaces, opensearch, opensearch-serverless, dax |
| **Networking** | vpc, elbv2, elb, route53, route53resolver, route53domains, cloudfront, globalaccelerator, apigateway, apigatewayv2, appsync, directconnect, network-firewall, servicediscovery, vpc-lattice, networkmanager |
| **Security** | iam, sso, kms, secretsmanager, acm, acm-pca, wafv2, guardduty, inspector2, securityhub, ds, cognito, accessanalyzer, macie2, detective, shield, fms, cloudhsmv2, auditmanager, securitylake |
| **Management & Monitoring** | cloudwatch, logs, cloudtrail, ssm, config, sns, sqs, events, xray, grafana, amp, ce, budgets, compute-optimizer, service-quotas, resource-groups, health, synthetics, appconfig, organizations, servicecatalog, resiliencehub |
| **Serverless** | stepfunctions, kinesis, firehose, kafka, serverlessrepo, eventbridge-scheduler, eventbridge-pipes, schemas |
| **Developer Tools** | cloudformation, codeartifact, codebuild, codepipeline, codedeploy, devicefarm |
| **Analytics** | athena, glue, mwaa, lakeformation, emr, emr-serverless, cleanrooms |
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
      "details": {...},
      "tags": {"Owner": "John", "Environment": "Production"}
    }
  ]
}
```

### CSV
Flat format with columns: service, type, id, name, region, arn, tags

## Tag Filtering

```bash
# Single tag
awsmap -t Environment=Production

# Multiple values for same key (OR logic)
awsmap -t Owner=John -t Owner=Jane
# Returns resources where Owner is "John" OR "Jane"

# Multiple keys (AND logic)
awsmap -t Owner=John -t Environment=Production
# Returns resources where Owner is "John" AND Environment is "Production"

# Combined
awsmap -t Owner=John -t Owner=Jane -t Environment=Production
# Returns resources where (Owner is "John" OR "Jane") AND Environment is "Production"
```

## Global vs Regional Services

AWS has two types of services:
- **Regional services** (EC2, RDS, Lambda, etc.) - Resources exist in specific regions
- **Global services** (IAM, Route53, CloudFront, etc.) - Resources are account-wide, not region-specific

### How awsmap handles global services

When you filter by region, awsmap intelligently includes global services based on their **control plane location**:

| Command | Behavior |
|---------|----------|
| `awsmap` (no region) | All services (regional + global) |
| `awsmap -r us-east-1` | Regional in us-east-1 + global services with us-east-1 control plane |
| `awsmap -r us-west-2` | Regional in us-west-2 + global services with us-west-2 control plane |
| `awsmap -r eu-west-1` | Regional in eu-west-1 only (no global services) |
| `awsmap -r eu-west-1 --include-global` | Regional in eu-west-1 + all global services |

### Global services by control plane

Based on [AWS Global Services documentation](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/global-services.html):

| Control Plane | Global Services |
|---------------|-----------------|
| **us-east-1** | IAM, Organizations, Route53, Route53 Domains, CloudFront, Shield, Budgets, Cost Explorer, Health |
| **us-west-2** | Network Manager, Global Accelerator |

### S3 buckets

S3 bucket names are globally unique, but **each bucket has a specific region**. awsmap treats S3 as a regional service:

```bash
# Only S3 buckets in eu-west-1
awsmap -r eu-west-1 -s s3

# All S3 buckets
awsmap -s s3
```

## Performance

Scans **140+ services** across all regions in parallel.

| Account Size | Resources | Estimated Time |
|--------------|-----------|----------------|
| Small | <500 | ~1.5 minutes |
| Medium | 500-5,000 | ~2 minutes |
| Large | 5,000-20,000 | ~3-5 minutes |
| Enterprise | 20,000+ | ~5-10 minutes |

**Tuning Options:**
```bash
# Increase parallelism for faster scans
awsmap -p myprofile -w 50

# Reduce parallelism for rate-limited accounts
awsmap -p myprofile -w 20

# Scan specific services only (much faster)
awsmap -p myprofile -s ec2,s3,lambda,iam

# Scan specific regions only
awsmap -p myprofile -r us-east-1,eu-west-1
```

**Why is the scan fast?**
- Parallel execution with configurable workers (default: 40)
- Region-aware collectors skip unsupported regions automatically
- Global services (IAM, Route53, etc.) collected once, not per-region
- Smart region filtering excludes global services when not relevant
- Optimized API calls (batch operations where available)

## IAM Permissions

awsmap requires read-only access to the AWS services you want to inventory.

**Recommended:** Attach the AWS managed [`ReadOnlyAccess`](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ReadOnlyAccess.html) policy to your IAM user or role. This policy is maintained by AWS and provides read access across all services.

```bash
# Attach to a role
aws iam attach-role-policy \
  --role-name YourRoleName \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Attach to a user
aws iam attach-user-policy \
  --user-name YourUserName \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
```

For more restrictive access, you can create a custom policy with explicit read actions for specific services (e.g., `ec2:Describe*`, `s3:List*`, `s3:Get*`). See the [IAM Actions Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html) for service-specific actions.

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

See [SERVICES.md](SERVICES.md#filtered-resources) for the complete list of filtered resources.

## Support

- **Documentation**: Check this README and [SERVICES.md](SERVICES.md)
- **Issues**: Report bugs via [GitHub Issues](https://github.com/TocConsulting/awsmap/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/TocConsulting/awsmap/discussions)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

