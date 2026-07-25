# Supported AWS Services

This document lists all 150 AWS services supported by cmipsmap, along with the specific resource types collected for each service.

**Legend:**
- *(global)* - Service is collected once globally, not per-region

---

## Compute (13 services)

### ec2
Amazon Elastic Compute Cloud
- `instance` - EC2 instances
- `volume` - EBS volumes
- `snapshot` - EBS snapshots
- `ami` - Amazon Machine Images (owned)
- `security-group` - Security groups
- `key-pair` - Key pairs
- `elastic-ip` - Elastic IP addresses
- `network-interface` - Network interfaces
- `placement-group` - Placement groups

### lambda
AWS Lambda
- `function` - Lambda functions
- `layer` - Lambda layers
- `event-source-mapping` - Event source mappings

### ecs
Amazon Elastic Container Service
- `cluster` - ECS clusters
- `service` - ECS services
- `task-definition` - Task definitions
- `capacity-provider` - Capacity providers

### eks
Amazon Elastic Kubernetes Service
- `cluster` - EKS clusters
- `nodegroup` - Node groups
- `fargate-profile` - Fargate profiles
- `addon` - EKS add-ons

### ecr
Amazon Elastic Container Registry
- `repository` - ECR repositories

### ecr-public
Amazon ECR Public
- `repository` - Public repositories

### lightsail
Amazon Lightsail
- `instance` - Lightsail instances
- `database` - Managed databases
- `bucket` - Object storage buckets
- `disk` - Block storage disks
- `load-balancer` - Load balancers
- `container-service` - Container services
- `distribution` - CDN distributions
- `certificate` - SSL/TLS certificates
- `domain` - DNS domains
- `static-ip` - Static IPs
- `key-pair` - SSH key pairs

### autoscaling
Amazon EC2 Auto Scaling
- `auto-scaling-group` - Auto Scaling groups
- `launch-configuration` - Launch configurations
- `scaling-policy` - Scaling policies
- `scheduled-action` - Scheduled actions

### application-autoscaling
AWS Application Auto Scaling
- `scalable-target` - Scalable targets
- `scaling-policy` - Scaling policies

### elasticbeanstalk
AWS Elastic Beanstalk
- `application` - Applications
- `application-version` - Application versions
- `environment` - Environments

### batch
AWS Batch
- `compute-environment` - Compute environments
- `job-queue` - Job queues
- `job-definition` - Job definitions
- `scheduling-policy` - Scheduling policies

### apprunner
AWS App Runner
- `service` - App Runner services
- `connection` - Source connections
- `auto-scaling-configuration` - Auto scaling configurations
- `vpc-connector` - VPC connectors
- `observability-configuration` - Observability configurations
- `vpc-ingress-connection` - VPC ingress connections

### imagebuilder
EC2 Image Builder
- `pipeline` - Image pipelines
- `image-recipe` - Image recipes
- `container-recipe` - Container recipes
- `infrastructure-configuration` - Infrastructure configurations
- `distribution-configuration` - Distribution configurations
- `component` - Components
- `workflow` - Workflows
- `lifecycle-policy` - Lifecycle policies

---

## Storage (7 services)

### s3 *(global)*
Amazon Simple Storage Service
- `bucket` - S3 buckets
- `table-bucket` - S3 Tables table buckets
- `namespace` - S3 Tables namespaces
- `table` - S3 Tables tables

### efs
Amazon Elastic File System
- `file-system` - EFS file systems
- `access-point` - Access points
- `replication-configuration` - Replication configurations

### fsx
Amazon FSx
- `file-system-lustre` - FSx for Lustre
- `file-system-windows` - FSx for Windows File Server
- `file-system-ontap` - FSx for NetApp ONTAP
- `file-system-openzfs` - FSx for OpenZFS
- `volume-ontap` - ONTAP volumes
- `volume-openzfs` - OpenZFS volumes
- `backup` - FSx backups

### backup
AWS Backup
- `vault` - Backup vaults
- `plan` - Backup plans
- `framework` - Audit frameworks
- `report-plan` - Report plans
- `restore-testing-plan` - Restore testing plans

### datasync
AWS DataSync
- `agent` - DataSync agents
- `location` - Source/destination locations
- `task` - Transfer tasks

### dlm
Amazon Data Lifecycle Manager
- `lifecycle-policy` - Lifecycle policies

### storagegateway
AWS Storage Gateway
- `gateway` - Storage gateways
- `file-share` - File shares
- `volume` - Storage volumes
- `tape` - Virtual tapes

---

## Database (14 services)

### rds
Amazon Relational Database Service
- `db-instance` - RDS instances
- `db-cluster` - Aurora clusters
- `db-snapshot` - Manual DB snapshots
- `db-cluster-snapshot` - Manual cluster snapshots
- `db-subnet-group` - Subnet groups
- `db-parameter-group` - Parameter groups (custom only)
- `option-group` - Option groups (custom only)
- `db-proxy` - RDS Proxy

### dynamodb
Amazon DynamoDB
- `table` - DynamoDB tables
- `global-table` - Global tables
- `backup` - On-demand backups
- `stream` - DynamoDB Streams

### elasticache
Amazon ElastiCache
- `cluster` - Cache clusters
- `replication-group` - Replication groups
- `serverless-cache` - Serverless caches
- `user-group` - User groups

### memorydb
Amazon MemoryDB for Redis
- `cluster` - MemoryDB clusters
- `user` - Users
- `acl` - Access control lists

### docdb
Amazon DocumentDB
- `cluster` - DocumentDB clusters
- `instance` - Cluster instances

### neptune
Amazon Neptune
- `cluster` - Neptune clusters
- `instance` - Cluster instances

### redshift
Amazon Redshift
- `cluster` - Redshift clusters
- `subnet-group` - Subnet groups
- `parameter-group` - Parameter groups
- `serverless-namespace` - Serverless namespaces
- `serverless-workgroup` - Serverless workgroups

### redshift-serverless
Amazon Redshift Serverless
- `namespace` - Namespaces
- `workgroup` - Workgroups
- `snapshot` - Snapshots

### keyspaces
Amazon Keyspaces (for Apache Cassandra)
- `keyspace` - Keyspaces
- `table` - Tables

### opensearch
Amazon OpenSearch Service
- `domain` - OpenSearch domains
- `serverless-collection` - Serverless collections

### opensearch-serverless
Amazon OpenSearch Serverless
- `collection` - Collections
- `security-policy` - Security policies
- `access-policy` - Access policies
- `vpc-endpoint` - VPC endpoints

### dax
Amazon DynamoDB Accelerator
- `cluster` - DAX clusters
- `parameter-group` - Parameter groups
- `subnet-group` - Subnet groups

### dsql
Amazon Aurora DSQL
- `cluster` - DSQL clusters

### timestream-influxdb
Amazon Timestream for InfluxDB
- `db_instance` - DB instances
- `db_parameter_group` - DB parameter groups

---

## Networking (16 services)

### vpc
Amazon Virtual Private Cloud
- `vpc` - VPCs
- `subnet` - Subnets
- `route-table` - Route tables
- `internet-gateway` - Internet gateways
- `nat-gateway` - NAT gateways
- `network-acl` - Network ACLs
- `vpc-endpoint` - VPC endpoints
- `vpc-peering` - Peering connections
- `transit-gateway` - Transit gateways
- `transit-gateway-attachment` - Transit gateway attachments
- `dhcp-options` - DHCP option sets

### elbv2
Elastic Load Balancing v2
- `load-balancer` - Application/Network/Gateway Load Balancers
- `target-group` - Target groups
- `listener` - Listeners

### elb
Elastic Load Balancing (Classic)
- `classic-load-balancer` - Classic Load Balancers

### route53 *(global)*
Amazon Route 53
- `hosted-zone` - Hosted zones
- `health-check` - Health checks
- `query-logging-config` - Query logging configurations

### route53resolver
Amazon Route 53 Resolver
- `resolver-endpoint` - Resolver endpoints
- `resolver-rule` - Resolver rules
- `query-log-config` - Query log configurations
- `firewall-rule-group` - DNS Firewall rule groups
- `firewall-domain-list` - DNS Firewall domain lists

### route53domains *(global)*
Amazon Route 53 Domains
- `domain` - Registered domains

### cloudfront *(global)*
Amazon CloudFront
- `distribution` - CDN distributions
- `function` - CloudFront Functions
- `origin-access-identity` - Origin access identities (legacy)
- `origin-access-control` - Origin access controls
- `cache-policy` - Cache policies

### globalaccelerator *(global)*
AWS Global Accelerator
- `accelerator` - Accelerators
- `listener` - Listeners
- `endpoint-group` - Endpoint groups
- `custom-routing-accelerator` - Custom routing accelerators
- `byoip-cidr` - BYOIP CIDRs
- `cross-account-attachment` - Cross-account attachments

### apigateway
Amazon API Gateway (REST)
- `rest-api` - REST APIs
- `stage` - Stages
- `api-key` - API keys
- `usage-plan` - Usage plans
- `vpc-link` - VPC links

### apigatewayv2
Amazon API Gateway (HTTP/WebSocket)
- `http-api` - HTTP APIs
- `websocket-api` - WebSocket APIs
- `stage` - Stages
- `domain-name` - Custom domain names
- `vpc-link` - VPC links

### appsync
AWS AppSync
- `graphql-api` - GraphQL APIs
- `data-source` - Data sources
- `function` - Functions
- `api-key` - API keys
- `domain-name` - Custom domain names

### directconnect
AWS Direct Connect
- `connection` - Connections
- `gateway` - Direct Connect gateways
- `virtual-interface-private` - Private virtual interfaces
- `virtual-interface-public` - Public virtual interfaces
- `virtual-interface-transit` - Transit virtual interfaces
- `lag` - Link aggregation groups

### network-firewall
AWS Network Firewall
- `firewall` - Firewalls
- `firewall-policy` - Firewall policies
- `rule-group` - Rule groups
- `tls-inspection-configuration` - TLS inspection configurations

### servicediscovery
AWS Cloud Map
- `namespace` - Namespaces
- `service` - Services
- `instance` - Service instances

### vpc-lattice
Amazon VPC Lattice
- `service-network` - Service networks
- `service` - Services
- `target-group` - Target groups
- `listener` - Listeners
- `rule` - Listener rules
- `service-network-vpc-association` - VPC associations
- `service-network-service-association` - Service associations
- `access-log-subscription` - Access log subscriptions

### networkmanager *(global)*
AWS Network Manager
- `global-network` - Global networks
- `site` - Sites
- `device` - Devices
- `link` - Links
- `connection` - Connections

---

## Security (20 services)

### iam *(global)*
AWS Identity and Access Management
- `user` - IAM users
- `group` - IAM groups
- `role` - IAM roles
- `policy` - Customer managed policies
- `instance-profile` - Instance profiles
- `saml-provider` - SAML providers
- `oidc-provider` - OIDC providers

### sso
AWS IAM Identity Center
- `instance` - Identity Center instances
- `permission-set` - Permission sets
- `user` - Users
- `group` - Groups

### kms
AWS Key Management Service
- `key` - Customer managed keys
- `alias` - Key aliases

### secretsmanager
AWS Secrets Manager
- `secret` - Secrets

### acm
AWS Certificate Manager
- `certificate` - SSL/TLS certificates

### acm-pca
AWS Private Certificate Authority
- `certificate-authority` - Private CAs
- `permission` - CA permissions

### wafv2
AWS WAF v2
- `web-acl-regional` - Regional Web ACLs
- `web-acl-cloudfront` - CloudFront Web ACLs
- `ip-set-regional` - Regional IP sets
- `ip-set-cloudfront` - CloudFront IP sets
- `rule-group-regional` - Regional rule groups
- `rule-group-cloudfront` - CloudFront rule groups
- `regex-pattern-set-regional` - Regional regex pattern sets
- `regex-pattern-set-cloudfront` - CloudFront regex pattern sets

### guardduty
Amazon GuardDuty
- `detector` - Detectors
- `filter` - Filters
- `ip-set` - Trusted IP lists
- `threat-intel-set` - Threat intelligence sets

### inspector2
Amazon Inspector
- `account-status` - Account status
- `filter` - Suppression rules

### securityhub
AWS Security Hub
- `hub` - Security Hub enablement
- `enabled-standard` - Enabled standards
- `insight` - Custom insights
- `automation-rule` - Automation rules

### ds
AWS Directory Service
- `directory` - Directories

### cognito
Amazon Cognito
- `user-pool` - User pools
- `user-pool-client` - App clients
- `identity-pool` - Identity pools

### accessanalyzer
AWS IAM Access Analyzer
- `analyzer` - Analyzers
- `archive-rule` - Archive rules

### macie2
Amazon Macie
- `classification-job` - Classification jobs
- `custom-data-identifier` - Custom data identifiers
- `findings-filter` - Findings filters
- `allow-list` - Allow lists
- `member` - Member accounts

### detective
Amazon Detective
- `graph` - Behavior graphs
- `member` - Member accounts
- `investigation` - Investigations

### shield *(global)*
AWS Shield Advanced
- `subscription` - Shield Advanced subscription
- `protection` - Protected resources
- `protection-group` - Protection groups

### fms
AWS Firewall Manager
- `policy` - Security policies
- `apps-list` - Application lists
- `protocols-list` - Protocol lists
- `resource-set` - Resource sets

### cloudhsmv2
AWS CloudHSM
- `cluster` - HSM clusters
- `backup` - Cluster backups

### auditmanager
AWS Audit Manager
- `assessment` - Assessments
- `framework` - Custom frameworks

### securitylake
Amazon Security Lake
- `data-lake` - Data lake configuration
- `subscriber` - Subscribers

---

## Management & Monitoring (22 services)

### cloudwatch
Amazon CloudWatch
- `metric-alarm` - Metric alarms
- `composite-alarm` - Composite alarms
- `dashboard` - Dashboards
- `metric-stream` - Metric streams

### logs
Amazon CloudWatch Logs
- `log-group` - Log groups
- `destination` - Destinations

### cloudtrail
AWS CloudTrail
- `trail` - Trails
- `event-data-store` - Event data stores

### ssm
AWS Systems Manager
- `parameter` - Parameter Store parameters
- `document` - SSM documents (custom only)
- `maintenance-window` - Maintenance windows
- `patch-baseline` - Patch baselines (custom only)
- `association` - State Manager associations

### config
AWS Config
- `configuration-recorder` - Configuration recorders
- `delivery-channel` - Delivery channels
- `config-rule` - Config rules
- `conformance-pack` - Conformance packs
- `configuration-aggregator` - Aggregators

### sns
Amazon Simple Notification Service
- `topic` - SNS topics
- `subscription` - Subscriptions

### sqs
Amazon Simple Queue Service
- `queue` - SQS queues

### events
Amazon EventBridge
- `event-bus` - Event buses
- `rule` - Rules
- `archive` - Archives
- `api-destination` - API destinations
- `connection` - Connections

### xray
AWS X-Ray
- `group` - X-Ray groups
- `sampling-rule` - Sampling rules

### grafana
Amazon Managed Grafana
- `workspace` - Grafana workspaces

### amp
Amazon Managed Service for Prometheus
- `workspace` - Prometheus workspaces
- `rule-groups-namespace` - Rule groups
- `alert-manager` - Alert manager configurations

### ce *(global)*
AWS Cost Explorer
- `cost-category` - Cost categories
- `anomaly-monitor` - Anomaly monitors
- `anomaly-subscription` - Anomaly subscriptions
- `savings-plan` - Savings Plans

### budgets *(global)*
AWS Budgets
- `budget` - Budgets
- `budget-action` - Budget actions

### compute-optimizer
AWS Compute Optimizer
- `ec2-recommendation` - EC2 recommendations
- `asg-recommendation` - Auto Scaling recommendations
- `ebs-recommendation` - EBS recommendations
- `lambda-recommendation` - Lambda recommendations

### service-quotas
Service Quotas
- `quota-request` - Quota increase requests

### resource-groups
AWS Resource Groups
- `group` - Resource groups

### health *(global)*
AWS Health
- `event` - Health events

### synthetics
Amazon CloudWatch Synthetics
- `canary` - Canaries
- `group` - Canary groups

### appconfig
AWS AppConfig
- `application` - Applications
- `environment` - Environments
- `configuration-profile` - Configuration profiles
- `deployment-strategy` - Deployment strategies

### organizations *(global)*
AWS Organizations
- `organization` - Organization
- `root` - Root
- `organizational-unit` - Organizational units
- `account` - Member accounts
- `policy` - SCPs and other policies
- `delegated-administrator` - Delegated administrators

### servicecatalog
AWS Service Catalog
- `portfolio` - Portfolios
- `product` - Products

### resiliencehub
AWS Resilience Hub
- `app` - Applications
- `resiliency-policy` - Resiliency policies

---

## Serverless (8 services)

### stepfunctions
AWS Step Functions
- `state-machine` - State machines
- `activity` - Activities

### kinesis
Amazon Kinesis Data Streams
- `stream` - Data streams
- `stream-consumer` - Enhanced fan-out consumers

### firehose
Amazon Kinesis Data Firehose
- `delivery-stream` - Delivery streams

### kafka
Amazon Managed Streaming for Apache Kafka
- `cluster` - MSK clusters
- `serverless-cluster` - Serverless clusters
- `configuration` - Cluster configurations
- `connector` - MSK Connect connectors

### serverlessrepo
AWS Serverless Application Repository
- `application` - Published applications

### eventbridge-scheduler
Amazon EventBridge Scheduler
- `schedule-group` - Schedule groups
- `schedule` - Schedules

### eventbridge-pipes
Amazon EventBridge Pipes
- `pipe` - Pipes

### schemas
Amazon EventBridge Schema Registry
- `registry` - Registries
- `discoverer` - Schema discoverers

---

## Developer Tools (6 services)

### cloudformation
AWS CloudFormation
- `stack` - Stacks
- `stack-set` - Stack sets

### codeartifact
AWS CodeArtifact
- `domain` - Domains
- `repository` - Repositories
- `package-group` - Package groups

### codebuild
AWS CodeBuild
- `project` - Build projects
- `report-group` - Report groups

### codepipeline
AWS CodePipeline
- `pipeline` - Pipelines

### codedeploy
AWS CodeDeploy
- `application` - Applications
- `deployment-group` - Deployment groups
- `deployment-config` - Deployment configurations

### devicefarm
AWS Device Farm
- `project` - Projects
- `test-grid-project` - Desktop browser testing projects
- `vpce-configuration` - VPC endpoint configurations

---

## Analytics (9 services)

### athena
Amazon Athena
- `workgroup` - Workgroups
- `data-catalog` - Data catalogs (custom only)
- `named-query` - Named queries

### glue
AWS Glue
- `database` - Data Catalog databases
- `table` - Data Catalog tables
- `job` - ETL jobs
- `crawler` - Crawlers
- `connection` - Connections
- `registry` - Schema registries

### mwaa
Amazon Managed Workflows for Apache Airflow
- `environment` - MWAA environments

### lakeformation
AWS Lake Formation
- `registered-resource` - Registered resources
- `lf-tag` - LF-Tags
- `data-cells-filter` - Data cell filters

### emr
Amazon EMR
- `cluster` - EMR clusters (active)
- `studio` - EMR Studios
- `serverless-application` - EMR Serverless applications

### emr-serverless
Amazon EMR Serverless
- `application` - Applications

### cleanrooms
AWS Clean Rooms
- `collaboration` - Collaborations
- `membership` - Memberships
- `configured-table` - Configured tables

### quicksight
Amazon QuickSight
- `dashboard` - Dashboards
- `data-set` - Data sets
- `data-source` - Data sources
- `analysis` - Analyses

### datazone
Amazon DataZone
- `domain` - Domains
- `project` - Projects
- `environment` - Environments

---

## AI/ML (12 services)

### sagemaker
Amazon SageMaker
- `notebook-instance` - Notebook instances
- `endpoint` - Inference endpoints
- `model` - Models
- `domain` - SageMaker Studio domains
- `training-job` - Training jobs (active)
- `feature-group` - Feature groups

### bedrock
Amazon Bedrock
- `custom-model` - Custom models
- `customization-job` - Model customization jobs (active)
- `provisioned-throughput` - Provisioned throughput
- `guardrail` - Guardrails
- `agent` - Bedrock Agents
- `knowledge-base` - Knowledge bases
- `data-source` - Knowledge base data sources

### lexv2
Amazon Lex V2
- `bot` - Bots
- `bot-alias` - Bot aliases

### rekognition
Amazon Rekognition
- `collection` - Face collections
- `project` - Custom Labels projects
- `stream-processor` - Stream processors

### textract
Amazon Textract
- `adapter` - Custom adapters

### transcribe
Amazon Transcribe
- `vocabulary` - Custom vocabularies
- `vocabulary-filter` - Vocabulary filters
- `language-model` - Custom language models
- `call-analytics-category` - Call Analytics categories

### translate
Amazon Translate
- `terminology` - Custom terminologies
- `parallel-data` - Parallel data

### comprehend
Amazon Comprehend
- `document-classifier` - Document classifiers
- `entity-recognizer` - Entity recognizers
- `endpoint` - Endpoints
- `flywheel` - Flywheels

### polly
Amazon Polly
- `lexicon` - Pronunciation lexicons

### personalize
Amazon Personalize
- `dataset-group` - Dataset groups
- `dataset` - Datasets
- `solution` - Solutions
- `campaign` - Campaigns

### kendra
Amazon Kendra
- `index` - Indexes
- `data-source` - Data sources

### frauddetector
Amazon Fraud Detector
- `detector` - Detectors
- `event-type` - Event types
- `model` - Models

---

## Media (7 services)

### mediaconvert
AWS Elemental MediaConvert
- `queue` - Queues
- `preset` - Presets
- `job-template` - Job templates

### mediaconnect
AWS Elemental MediaConnect
- `flow` - Flows
- `bridge` - Bridges
- `gateway` - Gateways

### mediapackage
AWS Elemental MediaPackage
- `channel` - Channels
- `origin-endpoint` - Origin endpoints

### medialive
AWS Elemental MediaLive
- `channel` - Channels
- `input` - Inputs
- `input-security-group` - Input security groups

### mediastore
AWS Elemental MediaStore
- `container` - Containers

### mediatailor
AWS Elemental MediaTailor
- `playback-configuration` - Playback configurations
- `channel` - Channels
- `source-location` - Source locations

### ivs
Amazon Interactive Video Service
- `channel` - Channels
- `recording-configuration` - Recording configurations
- `playback-key-pair` - Playback key pairs

---

## Migration & Transfer (2 services)

### transfer
AWS Transfer Family
- `server` - SFTP/FTPS/FTP servers
- `user` - Server users
- `workflow` - Workflows
- `connector` - SFTP connectors
- `certificate` - Certificates
- `profile` - AS2 profiles
- `agreement` - AS2 agreements
- `host-key` - SSH host keys
- `web-app` - Web apps

### dms
AWS Database Migration Service
- `replication-instance` - Replication instances
- `endpoint` - Source/target endpoints
- `replication-task` - Migration tasks
- `replication-subnet-group` - Subnet groups
- `certificate` - Certificates

---

## End User Computing (3 services)

### workspaces
Amazon WorkSpaces
- `workspace` - WorkSpaces
- `directory` - WorkSpaces directories

### amplify
AWS Amplify
- `app` - Amplify apps
- `branch` - Branches
- `domain` - Custom domains

### connect
Amazon Connect
- `instance` - Connect instances
- `contact-flow` - Contact flows
- `queue` - Queues
- `routing-profile` - Routing profiles

---

## IoT (2 services)

### iot
AWS IoT Core
- `thing` - Things
- `thing-type` - Thing types
- `thing-group` - Thing groups
- `policy` - IoT policies
- `certificate` - Device certificates

### iotsitewise
AWS IoT SiteWise
- `asset` - Assets
- `asset-model` - Asset models
- `gateway` - Gateways
- `portal` - Portals

---

## Other (9 services)

### ram
AWS Resource Access Manager
- `resource-share` - Resource shares
- `resource-share-invitation` - Pending invitations

### resource-explorer-2
AWS Resource Explorer
- `index` - Indexes
- `view` - Views

### mq
Amazon MQ
- `broker` - Message brokers
- `configuration` - Broker configurations

### sesv2
Amazon Simple Email Service v2
- `email-identity` - Email identities
- `configuration-set` - Configuration sets
- `contact-list` - Contact lists
- `dedicated-ip-pool` - Dedicated IP pools
- `email-template` - Email templates

### appflow
Amazon AppFlow
- `flow` - Flows
- `connector-profile` - Connector profiles

### gamelift
Amazon GameLift
- `fleet` - Fleets
- `build` - Builds
- `script` - Scripts
- `alias` - Aliases
- `game-session-queue` - Game session queues
- `matchmaking-configuration` - Matchmaking configurations
- `matchmaking-rule-set` - Matchmaking rule sets

### outposts
AWS Outposts
- `outpost` - Outposts
- `site` - Sites

### fis
AWS Fault Injection Simulator
- `experiment-template` - Experiment templates
- `experiment` - Experiments

### location
Amazon Location Service
- `map` - Maps
- `place-index` - Place indexes
- `route-calculator` - Route calculators
- `geofence-collection` - Geofence collections
- `tracker` - Trackers

---

## Summary

| Category | Services | Resource Types |
|----------|----------|----------------|
| Compute | 13 | 50+ |
| Storage | 7 | 25+ |
| Database | 14 | 45+ |
| Networking | 16 | 60+ |
| Security | 20 | 50+ |
| Management & Monitoring | 22 | 50+ |
| Serverless | 8 | 15+ |
| Developer Tools | 6 | 15+ |
| Analytics | 9 | 30+ |
| AI/ML | 12 | 40+ |
| Media | 7 | 20+ |
| Migration & Transfer | 2 | 15+ |
| End User Computing | 3 | 10+ |
| IoT | 2 | 10+ |
| Other | 9 | 25+ |
| **Total** | **150** | **415+** |

---

## Filtered Resources

The following AWS default/managed resources are automatically excluded from inventory results to avoid noise:

| Service | Excluded Resources | Reason |
|---------|-------------------|--------|
| **keyspaces** | `system`, `system_schema`, `system_schema_mcs`, `system_multiregion_info` keyspaces | AWS system keyspaces (not user-created) |
| **lakeformation** | `data-lake-settings` | Default settings that exist in every AWS account/region |
| **mediaconvert** | `Default` queue | AWS default queue that exists in every region |
| **route53resolver** | `AWSManagedDomains*` firewall domain lists | AWS-managed threat intelligence lists |
| **timestream-influxdb** | `InfluxDBV3Core`, `InfluxDBV3Enterprise`, `InfluxDBV3Enterprise1Node` parameter groups | AWS default parameter groups (not user-created) |
| **xray** | `Default` group | AWS default group that exists in every region |

These resources are created and managed by AWS automatically and are not considered user-owned infrastructure.

---

## Global Services

Some AWS services are **global** (account-wide) rather than regional. When filtering by region, cmipsmap intelligently handles these based on their control plane location.

### Control Plane: us-east-1

These services have their control plane in us-east-1 and are included when scanning us-east-1 or with `--include-global`:

| Service | Description |
|---------|-------------|
| **iam** | Identity and Access Management (users, roles, policies) |
| **organizations** | AWS Organizations (accounts, OUs, SCPs) |
| **route53** | Route 53 DNS (hosted zones, records) |
| **route53domains** | Route 53 Domains (registered domains) |
| **cloudfront** | CloudFront CDN (distributions) |
| **shield** | AWS Shield (protections) |
| **budgets** | AWS Budgets |
| **ce** | Cost Explorer |
| **health** | AWS Health Dashboard |

### Control Plane: us-west-2

These services have their control plane in us-west-2 and are included when scanning us-west-2 or with `--include-global`:

| Service | Description |
|---------|-------------|
| **networkmanager** | Network Manager (global networks, transit gateways) |
| **globalaccelerator** | Global Accelerator (accelerators, endpoints) |

### S3 (Regional)

S3 bucket names are globally unique, but each bucket has a **specific region**. cmipsmap treats S3 as a regional service and filters buckets by their actual region when using `-r`.

Reference: [AWS Global Services Documentation](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/global-services.html)
