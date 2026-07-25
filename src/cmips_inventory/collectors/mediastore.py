"""
AWS Elemental MediaStore resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


# MediaStore supported regions (from https://docs.aws.amazon.com/general/latest/gr/mediastore.html)
MEDIASTORE_REGIONS = {
    'us-east-1', 'us-west-2',
    'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-2',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-north-1',
}


def collect_mediastore_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Elemental MediaStore resources: containers.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in MEDIASTORE_REGIONS:
        return []

    resources = []
    mediastore = session.client('mediastore', region_name=region)

    # Containers
    try:
        paginator = mediastore.get_paginator('list_containers')
        for page in paginator.paginate():
            for container in page.get('Containers', []):
                container_arn = container.get('ARN', '')
                container_name = container.get('Name', container_arn.split('/')[-1])

                details = {
                    'status': container.get('Status'),
                    'endpoint': container.get('Endpoint'),
                    'access_logging_enabled': container.get('AccessLoggingEnabled'),
                }

                resources.append({
                    'service': 'mediastore',
                    'type': 'container',
                    'id': container_name,
                    'arn': container_arn,
                    'name': container_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
