# Roadmap

We currently cover **150 AWS services**. Below are the **86 services** we still need to add: **64 new collectors** and **22 extensions** to existing collectors.

This list was built by comparing all **417 services available in boto3** against what cmipsmap already covers, then filtering out deprecated/sunset services and data-plane-only APIs that don't have inventoriable resources.

To contribute: pick a service, write a collector in `src/cmips_inventory/collectors/`, and open a PR.

## New collectors (64)

- **aiops** - AI Operations
- **appfabric** - App bundles, ingestions
- **appintegrations** - Event/data integrations
- **application-insights** - CloudWatch Application Insights
- **application-signals** - CloudWatch Application Signals
- **appstream** - AppStream 2.0 fleets, stacks, images
- **autoscaling-plans** - Auto Scaling plans
- **b2bi** - B2B Data Interchange profiles, transformers
- **chatbot** - Slack/Teams channel configs
- **codeconnections** - Source provider connections
- **controltower** - Landing zones, enabled controls
- **databrew** - Glue DataBrew datasets, projects, recipes, jobs
- **dataexchange** - Data sets, revisions
- **deadline** - Deadline Cloud farms, queues, fleets
- **drs** - Elastic Disaster Recovery
- **entityresolution** - Matching workflows, schema mappings
- **evs** - Elastic VMware Service environments
- **gameliftstreams** - GameLift Streams stream groups
- **greengrassv2** - Core devices, components, deployments
- **groundstation** - Ground Station configs, mission profiles
- **healthlake** - HealthLake FHIR datastores
- **internetmonitor** - Internet monitors
- **iot-managed-integrations** - IoT Managed Integrations
- **iotfleetwise** - IoT FleetWise campaigns, fleets, vehicles
- **iottwinmaker** - IoT TwinMaker workspaces, scenes, entities
- **iotwireless** - IoT Wireless devices, gateways, profiles
- **kinesisanalyticsv2** - Managed Apache Flink applications
- **kinesisvideo** - Kinesis Video streams
- **launch-wizard** - Deployments
- **license-manager** - License configurations, grants
- **license-manager-user-subscriptions** - User-based subscriptions
- **mailmanager** - SES Mail Manager policies, rule sets
- **managedblockchain** - Managed Blockchain networks, nodes
- **medical-imaging** - HealthImaging datastores, image sets
- **mgn** - Application Migration Service
- **mpa** - Multi-party approval policies
- **mwaa-serverless** - MWAA Serverless environments
- **networkflowmonitor** - Network flow monitors
- **networkmonitor** - CloudWatch Network Monitor probes
- **oam** - Observability Access Manager links and sinks
- **odb** - Oracle Database on AWS
- **omics** - HealthOmics workflows, runs, stores
- **payment-cryptography** - Payment keys, aliases
- **pca-connector-ad** - PCA Connector for Active Directory
- **pca-connector-scep** - PCA Connector for SCEP
- **pcs** - Parallel Computing Service clusters
- **qbusiness** - Q Business applications, indices
- **rbin** - Recycle Bin retention rules
- **repostspace** - re:Post Private spaces
- **rolesanywhere** - IAM Roles Anywhere trust anchors, profiles
- **route53-recovery-control-config** - ARC clusters, control panels, routing controls
- **route53-recovery-readiness** - Readiness checks, recovery groups
- **rum** - CloudWatch Real User Monitoring
- **security-ir** - Incident response cases
- **servicecatalog-appregistry** - Applications, attribute groups
- **signer** - Signing profiles
- **ssm-contacts** - Contacts and escalation plans
- **ssm-quicksetup** - Quick Setup configurations
- **ssm-sap** - SAP applications
- **supplychain** - Supply Chain instances
- **tnb** - Telco Network Builder packages, networks
- **verifiedpermissions** - Policy stores, policies
- **wellarchitected** - Workloads, lenses, reviews
- **wickr** - Wickr networks
- **workmail** - Organizations, users, groups

## Extensions to existing collectors (22)

Extend `bedrock.py`:
- **bedrock-data-automation** - Data automation projects

Extend `cleanrooms.py`:
- **cleanroomsml** - Clean Rooms ML models

Extend `connect.py`:
- **connectcampaignsv2** - Connect outbound campaigns
- **connectcases** - Connect Cases domains, templates
- **customer-profiles** - Connect Customer Profiles domains
- **qconnect** - Q Connect assistants and knowledge bases

Extend `docdb.py`:
- **docdb-elastic** - DocumentDB Elastic Clusters

Extend `emr.py`:
- **emr-containers** - EMR on EKS virtual clusters

Extend `ivs.py`:
- **ivs-realtime** - IVS Real-Time stages, compositions
- **ivschat** - IVS Chat rooms, logging configs

Extend `mediapackage.py`:
- **mediapackage-vod** - MediaPackage VOD packaging groups, assets
- **mediapackagev2** - MediaPackage V2 channel groups, channels

Extend `neptune.py`:
- **neptune-graph** - Neptune Analytics graphs

Extend `opensearch.py`:
- **osis** - OpenSearch Ingestion pipelines

Extend `route53.py`:
- **route53profiles** - Route 53 Profiles

Extend `route53resolver.py`:
- **route53globalresolver** - Global Resolver rules

Extend `s3.py`:
- **s3control** - Access points, Storage Lens
- **s3outposts** - S3 on Outposts endpoints

Extend `workspaces.py`:
- **workspaces-instances** - WorkSpaces Instances
- **workspaces-thin-client** - Thin Client environments, devices
- **workspaces-web** - Web portals, browser settings

## Note: **frauddetector** already in cmipsmap

**frauddetector** was put in maintenance mode by AWS on Nov 7, 2025. It still works but no longer accepts new customers. We may remove it in a future release.
