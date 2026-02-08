"""
Core resource collection functionality with parallel execution.
"""

import time
import importlib
import threading
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable

from aws_inventory.auth import get_account_id, get_enabled_regions


# Global services grouped by control plane region
# See: https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/global-services.html
US_EAST_1_GLOBAL_SERVICES = ['iam', 'organizations', 'route53', 'route53domains', 'cloudfront', 'shield', 'budgets', 'ce', 'health']
US_WEST_2_GLOBAL_SERVICES = ['networkmanager', 'globalaccelerator']

# All global services (for backward compatibility)
GLOBAL_SERVICES = US_EAST_1_GLOBAL_SERVICES + US_WEST_2_GLOBAL_SERVICES

# S3 is treated as regional - buckets have specific regions

# Service name to module name mapping (for special cases)
SERVICE_MODULE_MAP = {
    'lambda': 'lambda_',
    'ecr-public': 'ecr_public',
    'network-firewall': 'network_firewall',
    'vpc-lattice': 'vpc_lattice',
    'acm-pca': 'acm_pca',
    'compute-optimizer': 'computeoptimizer',
    'service-quotas': 'servicequotas',
    'resource-groups': 'resourcegroups',
    'resource-explorer-2': 'resourceexplorer',
    'eventbridge-scheduler': 'scheduler',
    'eventbridge-pipes': 'pipes',
    'redshift-serverless': 'redshiftserverless',
    'opensearch-serverless': 'opensearchserverless',
    'emr-serverless': 'emrserverless',
    'application-autoscaling': 'applicationautoscaling',
    'timestream-influxdb': 'timestream_influxdb',
}

# Thread-safe tracking for progress
_lock = threading.Lock()
_service_progress = {}
_service_timings = {}


def validate_services(services: List[str]) -> None:
    """
    Validate that all requested service names have collectors.

    Args:
        services: List of service names to validate

    Raises:
        ValueError: If any service name is unknown
    """
    from difflib import get_close_matches
    available = set(get_available_services())
    unknown = [s for s in services if s.lower() not in available]
    if unknown:
        msgs = []
        for s in unknown:
            matches = get_close_matches(s.lower(), sorted(available), n=3, cutoff=0.5)
            msg = f"Unknown service '{s}'"
            if matches:
                msg += f". Did you mean: {', '.join(matches)}?"
            msgs.append(msg)
        raise ValueError(
            '\n'.join(msgs) + '\n\nUse --list-services to see all available collectors.'
        )


def get_collector_function(service_name: str) -> Optional[Callable]:
    """
    Dynamically import and return the collector function for a service.

    Args:
        service_name: Name of the AWS service

    Returns:
        Collector function or None if not found
    """
    module_name = SERVICE_MODULE_MAP.get(service_name, service_name)
    function_name = f"collect_{module_name}_resources"

    try:
        module = importlib.import_module(f'aws_inventory.collectors.{module_name}')
        return getattr(module, function_name)
    except (ImportError, AttributeError):
        return None


def get_available_services() -> List[str]:
    """
    Get list of available service collectors.

    Returns:
        List of service names that have collectors
    """
    services = [
        # Compute
        'ec2', 'lambda', 'ecs', 'eks', 'ecr', 'ecr-public', 'lightsail', 'autoscaling', 'application-autoscaling', 'elasticbeanstalk', 'batch', 'apprunner',
        # Storage
        's3', 'efs', 'fsx', 'backup', 'datasync', 'dlm', 'storagegateway',
        # Database
        'rds', 'dynamodb', 'elasticache', 'memorydb', 'docdb', 'neptune', 'redshift',
        'keyspaces', 'opensearch', 'opensearch-serverless', 'dax', 'redshift-serverless',
        'dsql', 'timestream-influxdb',
        # Networking
        'vpc', 'elbv2', 'elb', 'route53', 'cloudfront', 'globalaccelerator', 'apigateway', 'apigatewayv2', 'appsync', 'directconnect', 'network-firewall',
        # Security
        'iam', 'sso', 'kms', 'secretsmanager', 'acm', 'wafv2', 'guardduty', 'inspector2',
        'securityhub', 'ds', 'cognito', 'accessanalyzer', 'macie2', 'detective', 'shield', 'fms', 'acm-pca', 'cloudhsmv2',
        # Management
        'cloudwatch', 'logs', 'cloudtrail', 'ssm', 'config', 'sns', 'sqs', 'events',
        'xray', 'grafana', 'amp', 'ce', 'budgets', 'compute-optimizer', 'service-quotas', 'resource-groups', 'health',
        # Serverless
        'stepfunctions', 'kinesis', 'firehose', 'kafka', 'eventbridge-scheduler', 'eventbridge-pipes', 'schemas',
        # DevTools
        'cloudformation', 'codeartifact', 'codebuild', 'codepipeline', 'codedeploy',
        # Analytics
        'athena', 'glue', 'mwaa', 'quicksight', 'lakeformation', 'emr', 'emr-serverless', 'cleanrooms',
        # AI/ML
        'sagemaker', 'bedrock', 'frauddetector',
        # Data Governance
        'datazone',
        # Image Building
        'imagebuilder',
        # End User
        'workspaces', 'amplify',
        # IoT
        'iot',
        # Messaging
        'mq',
        # Migration & Transfer
        'transfer',
        # Management
        'organizations',
        # Other
        'ram',
        # Service Discovery
        'servicediscovery',
        # Route 53 Resolver
        'route53resolver',
        # Route 53 Domains
        'route53domains',
        # VPC Lattice
        'vpc-lattice',
        # Network Manager
        'networkmanager',
        # Database Migration
        'dms',
        # Email
        'sesv2',
        # Integration
        'appflow',
        # Media
        'mediaconvert',
        'mediaconnect',
        'mediapackage',
        'medialive',
        'mediastore',
        'mediatailor',
        # Conversational AI
        'lexv2',
        # Contact Center
        'connect',
        # AI/ML - Vision
        'rekognition',
        # AI/ML - Document
        'textract',
        # AI/ML - Speech
        'transcribe',
        # AI/ML - Language
        'translate',
        # AI/ML - NLP
        'comprehend',
        # AI/ML - Text to Speech
        'polly',
        # AI/ML - Recommendations
        'personalize',
        # AI/ML - Search
        'kendra',
        # Interactive Video
        'ivs',
        # Game Development
        'gamelift',
        # IoT
        'iotsitewise',
        # Hybrid
        'outposts',
        # Serverless
        'serverlessrepo',
        # Monitoring
        'synthetics',
        # Chaos Engineering
        'fis',
        # Service Management
        'servicecatalog',
        # Location
        'location',
        # Configuration
        'appconfig',
        # Resource Discovery
        'resource-explorer-2',
        # Compliance
        'auditmanager',
        # Resilience
        'resiliencehub',
        # Security Data Lake
        'securitylake',
        # Testing
        'devicefarm',
    ]

    # Return only services that have collectors implemented
    available = []
    for service in services:
        if get_collector_function(service):
            available.append(service)

    return sorted(available)


def collect_s3_with_region_filter(
    session,
    account_id: str,
    filter_regions: Optional[List[str]] = None
) -> tuple:
    """
    Collect S3 buckets with optional region filtering.

    S3 buckets are global but each bucket has a specific region.
    When filter_regions is provided, only buckets in those regions are returned.

    Args:
        session: boto3.Session to use
        account_id: AWS account ID
        filter_regions: Optional list of regions to filter by

    Returns:
        Tuple of (resources list, elapsed time)
    """
    from aws_inventory.collectors.s3 import collect_s3_resources

    start = time.time()
    try:
        resources = collect_s3_resources(session, None, account_id)

        # Filter by region if specified
        if filter_regions:
            resources = [r for r in resources if r.get('region') in filter_regions]

        elapsed = time.time() - start
        return resources, elapsed
    except Exception:
        elapsed = time.time() - start
        return [], elapsed


def collect_service_resources(
    session,
    service_name: str,
    region: Optional[str],
    account_id: str
) -> tuple:
    """
    Collect resources for a single service in a single region.

    Args:
        session: boto3.Session to use
        service_name: Name of the AWS service
        region: AWS region (None for global services)
        account_id: AWS account ID

    Returns:
        Tuple of (resources list, elapsed time)
    """
    collector_func = get_collector_function(service_name)
    if not collector_func:
        return [], 0.0

    start = time.time()
    try:
        resources = collector_func(session, region, account_id)
        elapsed = time.time() - start
        return resources, elapsed
    except Exception:
        elapsed = time.time() - start
        return [], elapsed


def collect_all(
    session,
    services: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
    max_workers: int = 20,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    show_timings: bool = False,
    include_global: bool = False
) -> Dict[str, Any]:
    """
    Collect resources from all specified services and regions.

    Args:
        session: boto3.Session to use
        services: List of service names to collect (None for all)
        regions: List of regions to collect from (None for all enabled)
        max_workers: Maximum parallel workers
        progress_callback: Optional callback(service_name, status) for progress updates
        show_timings: If True, print service timing summary at the end
        include_global: If True, include global services even when filtering by non-global regions

    Returns:
        Dict with metadata and resources list
    """
    global _service_progress, _service_timings
    _service_progress = {}
    _service_timings = {}

    start_time = time.time()

    # Get account info
    account_id = get_account_id(session)

    # Determine services to collect
    if services:
        service_list = [s.lower() for s in services]
        validate_services(service_list)
    else:
        service_list = get_available_services()

    service_list = sorted(service_list)

    # Determine regions
    if regions:
        region_list = regions
        # Validate requested regions
        enabled = get_enabled_regions(session)
        unknown_regions = [r for r in region_list if r not in enabled]
        if unknown_regions:
            from difflib import get_close_matches
            msgs = []
            for r in unknown_regions:
                matches = get_close_matches(r, enabled, n=3, cutoff=0.5)
                msg = f"Unknown or disabled region '{r}'"
                if matches:
                    msg += f". Did you mean: {', '.join(matches)}?"
                msgs.append(msg)
            raise ValueError('\n'.join(msgs))
    else:
        region_list = get_enabled_regions(session)

    # Determine which global services to include based on region filter
    # - No region filter: include all global services
    # - include_global flag: include all global services
    # - us-east-1 in regions: include us-east-1 control plane services (IAM, Route53, etc.)
    # - us-west-2 in regions: include us-west-2 control plane services (NetworkManager, GlobalAccelerator)
    active_global_services = set()
    if not regions or include_global:
        # No region filter or --include-global: include all global services
        active_global_services = set(GLOBAL_SERVICES)
    else:
        # Include global services based on their control plane region
        if 'us-east-1' in region_list:
            active_global_services.update(US_EAST_1_GLOBAL_SERVICES)
        if 'us-west-2' in region_list:
            active_global_services.update(US_WEST_2_GLOBAL_SERVICES)

    # Initialize progress tracking
    for service in service_list:
        if service in active_global_services:
            _service_progress[service] = {'total': 1, 'completed': 0, 'resources': 0}
        elif service == 's3':
            # S3 is treated as regional - will filter by bucket region
            _service_progress[service] = {'total': 1, 'completed': 0, 'resources': 0}
        else:
            _service_progress[service] = {'total': len(region_list), 'completed': 0, 'resources': 0}

    all_resources = []
    futures_map = {}

    def on_complete(service: str, resources: List[Dict[str, Any]], elapsed: float):
        """Track completion, resources, and timing."""
        with _lock:
            _service_progress[service]['completed'] += 1
            _service_progress[service]['resources'] += len(resources)

            if service not in _service_timings:
                _service_timings[service] = 0.0
            _service_timings[service] += elapsed

            progress = _service_progress[service]
            if progress['completed'] >= progress['total']:
                if progress_callback:
                    progress_callback(service, f"Done: {progress['resources']} resources")

    # Submit all collection tasks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for service in service_list:
            if service in active_global_services:
                # Global service - single call, no region
                if progress_callback:
                    progress_callback(service, "Collecting...")
                future = executor.submit(
                    collect_service_resources,
                    session, service, None, account_id
                )
                futures_map[future] = (service, None)
            elif service == 's3':
                # S3 - collect all buckets, filter by region later
                if progress_callback:
                    progress_callback(service, "Collecting...")
                future = executor.submit(
                    collect_s3_with_region_filter,
                    session, account_id, region_list if regions else None
                )
                futures_map[future] = (service, None)
            elif service not in GLOBAL_SERVICES:
                # Regional service - one call per region
                if progress_callback:
                    progress_callback(service, "Collecting...")
                for region in region_list:
                    future = executor.submit(
                        collect_service_resources,
                        session, service, region, account_id
                    )
                    futures_map[future] = (service, region)
            # else: skip global services not in active_global_services

        # Process completed futures
        for future in concurrent.futures.as_completed(futures_map):
            service, region = futures_map[future]
            try:
                resources, elapsed = future.result()
                all_resources.extend(resources)
                on_complete(service, resources, elapsed)
            except Exception:
                on_complete(service, [], 0.0)

    elapsed_time = time.time() - start_time

    # Print timing summary if requested
    if show_timings:
        print("\n" + "="*60)
        print("SERVICE TIMING SUMMARY (sorted by total time)")
        print("="*60)
        sorted_timings = sorted(_service_timings.items(), key=lambda x: x[1], reverse=True)
        for service, total_time in sorted_timings:
            resources = _service_progress.get(service, {}).get('resources', 0)
            print(f"{service:30} {total_time:8.2f}s  ({resources} resources)")
        print("="*60)
        print(f"{'TOTAL':30} {elapsed_time:8.2f}s  ({len(all_resources)} resources)")
        print("="*60 + "\n")

    # Build result
    return {
        'metadata': {
            'account_id': account_id,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            'scan_duration_seconds': round(elapsed_time, 2),
            'services_scanned': len(service_list),
            'regions_scanned': len(region_list),
            'resource_count': len(all_resources)
        },
        'resources': all_resources
    }


def tags_to_dict(tags: Optional[List[Dict[str, str]]]) -> Dict[str, str]:
    """
    Convert AWS tags list to dictionary.

    Args:
        tags: List of {'Key': k, 'Value': v} dicts

    Returns:
        Dict of {key: value}
    """
    if not tags:
        return {}
    return {tag.get('Key', ''): tag.get('Value', '') for tag in tags if isinstance(tag, dict)}


def get_tag_value(tags: Optional[List[Dict[str, str]]], key: str) -> Optional[str]:
    """
    Get a specific tag value from tags list.

    Args:
        tags: List of {'Key': k, 'Value': v} dicts
        key: Tag key to find

    Returns:
        Tag value or None
    """
    if not tags:
        return None
    for tag in tags:
        if isinstance(tag, dict) and tag.get('Key') == key:
            return tag.get('Value')
    return None
