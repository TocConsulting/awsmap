"""
CloudWatch Logs resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_logs_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CloudWatch Logs resources: log groups, metric filters, subscription filters.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    logs = session.client('logs', region_name=region)

    # Log Groups (tags and filters disabled for performance - saves ~35s per region)
    try:
        paginator = logs.get_paginator('describe_log_groups')
        for page in paginator.paginate():
            for lg in page.get('logGroups', []):
                lg_name = lg['logGroupName']
                lg_arn = lg.get('arn', f"arn:aws:logs:{region}:{account_id}:log-group:{lg_name}")

                resources.append({
                    'service': 'logs',
                    'type': 'log-group',
                    'id': lg_name,
                    'arn': lg_arn,
                    'name': lg_name,
                    'region': region,
                    'details': {
                        'stored_bytes': lg.get('storedBytes'),
                        'retention_in_days': lg.get('retentionInDays'),
                        'metric_filter_count': lg.get('metricFilterCount'),
                        'kms_key_id': lg.get('kmsKeyId'),
                        'data_protection_status': lg.get('dataProtectionStatus'),
                        'creation_time': lg.get('creationTime'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Log Destinations
    try:
        paginator = logs.get_paginator('describe_destinations')
        for page in paginator.paginate():
            for dest in page.get('destinations', []):
                dest_name = dest['destinationName']

                resources.append({
                    'service': 'logs',
                    'type': 'destination',
                    'id': dest_name,
                    'arn': dest.get('arn', f"arn:aws:logs:{region}:{account_id}:destination:{dest_name}"),
                    'name': dest_name,
                    'region': region,
                    'details': {
                        'target_arn': dest.get('targetArn'),
                        'role_arn': dest.get('roleArn'),
                        'creation_time': dest.get('creationTime'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
