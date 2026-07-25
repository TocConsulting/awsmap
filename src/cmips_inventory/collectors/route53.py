"""
Route53 resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_route53_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Route53 resources: hosted zones, health checks.

    Args:
        session: boto3.Session to use
        region: Not used for Route53 (global service)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    route53 = session.client('route53')

    # Hosted Zones
    try:
        paginator = route53.get_paginator('list_hosted_zones')
        for page in paginator.paginate():
            for zone in page.get('HostedZones', []):
                zone_id = zone['Id'].split('/')[-1]

                # Get tags
                tags = {}
                try:
                    tag_response = route53.list_tags_for_resource(
                        ResourceType='hostedzone',
                        ResourceId=zone_id
                    )
                    for tag in tag_response.get('ResourceTagSet', {}).get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                # Get record count
                record_count = zone.get('ResourceRecordSetCount', 0)

                resources.append({
                    'service': 'route53',
                    'type': 'hosted-zone',
                    'id': zone_id,
                    'arn': f"arn:aws:route53:::hostedzone/{zone_id}",
                    'name': zone['Name'].rstrip('.'),
                    'region': 'global',
                    'details': {
                        'zone_name': zone['Name'],
                        'private_zone': zone.get('Config', {}).get('PrivateZone', False),
                        'record_count': record_count,
                        'comment': zone.get('Config', {}).get('Comment'),
                        'caller_reference': zone.get('CallerReference'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Health Checks
    try:
        paginator = route53.get_paginator('list_health_checks')
        for page in paginator.paginate():
            for hc in page.get('HealthChecks', []):
                hc_id = hc['Id']

                # Get tags
                tags = {}
                try:
                    tag_response = route53.list_tags_for_resource(
                        ResourceType='healthcheck',
                        ResourceId=hc_id
                    )
                    for tag in tag_response.get('ResourceTagSet', {}).get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                config = hc.get('HealthCheckConfig', {})
                name = tags.get('Name', config.get('FullyQualifiedDomainName') or config.get('IPAddress') or hc_id)

                resources.append({
                    'service': 'route53',
                    'type': 'health-check',
                    'id': hc_id,
                    'arn': f"arn:aws:route53:::healthcheck/{hc_id}",
                    'name': name,
                    'region': 'global',
                    'details': {
                        'type': config.get('Type'),
                        'ip_address': config.get('IPAddress'),
                        'fqdn': config.get('FullyQualifiedDomainName'),
                        'port': config.get('Port'),
                        'resource_path': config.get('ResourcePath'),
                        'request_interval': config.get('RequestInterval'),
                        'failure_threshold': config.get('FailureThreshold'),
                        'measure_latency': config.get('MeasureLatency'),
                        'inverted': config.get('Inverted'),
                        'disabled': config.get('Disabled'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Query Logging Configs
    try:
        response = route53.list_query_logging_configs()
        for qlc in response.get('QueryLoggingConfigs', []):
            qlc_id = qlc['Id']
            zone_id = qlc['HostedZoneId']

            resources.append({
                'service': 'route53',
                'type': 'query-logging-config',
                'id': qlc_id,
                'arn': f"arn:aws:route53:::queryloggingconfig/{qlc_id}",
                'name': f"qlc-{zone_id}",
                'region': 'global',
                'details': {
                    'hosted_zone_id': zone_id,
                    'cloudwatch_logs_log_group_arn': qlc.get('CloudWatchLogsLogGroupArn'),
                },
                'tags': {}
            })
    except Exception:
        pass

    return resources
