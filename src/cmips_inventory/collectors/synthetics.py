"""
AWS CloudWatch Synthetics resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_synthetics_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS CloudWatch Synthetics resources: canaries and groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    synthetics = session.client('synthetics', region_name=region)

    # Canaries
    try:
        paginator = synthetics.get_paginator('describe_canaries')
        for page in paginator.paginate():
            for canary in page.get('Canaries', []):
                canary_id = canary.get('Id', '')
                canary_name = canary['Name']
                canary_arn = f"arn:aws:synthetics:{region}:{account_id}:canary:{canary_name}"

                status = canary.get('Status', {})
                schedule = canary.get('Schedule', {})
                run_config = canary.get('RunConfig', {})

                details = {
                    'status': status.get('State'),
                    'status_reason': status.get('StateReason'),
                    'schedule_expression': schedule.get('Expression'),
                    'runtime_version': canary.get('RuntimeVersion'),
                    'timeout_in_seconds': run_config.get('TimeoutInSeconds'),
                    'memory_in_mb': run_config.get('MemoryInMB'),
                    'artifact_s3_location': canary.get('ArtifactS3Location'),
                    'execution_role_arn': canary.get('ExecutionRoleArn'),
                }

                tags = canary.get('Tags', {})

                resources.append({
                    'service': 'synthetics',
                    'type': 'canary',
                    'id': canary_name,
                    'arn': canary_arn,
                    'name': canary_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Groups
    try:
        paginator = synthetics.get_paginator('list_groups')
        for page in paginator.paginate():
            for group in page.get('Groups', []):
                group_id = group.get('Id', '')
                group_name = group.get('Name', group_id)
                group_arn = group.get('Arn', f"arn:aws:synthetics:{region}:{account_id}:group:{group_name}")

                details = {}

                resources.append({
                    'service': 'synthetics',
                    'type': 'group',
                    'id': group_id,
                    'arn': group_arn,
                    'name': group_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
