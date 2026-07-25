"""
AWS Resource Explorer resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_resourceexplorer_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Resource Explorer resources: indexes and views.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    explorer = session.client('resource-explorer-2', region_name=region)

    # Indexes
    try:
        paginator = explorer.get_paginator('list_indexes')
        for page in paginator.paginate():
            for index in page.get('Indexes', []):
                index_arn = index['Arn']
                index_region = index.get('Region', region)
                index_type = index.get('Type', 'LOCAL')

                # Only collect indexes for the current region to avoid duplicates
                if index_region != region:
                    continue

                details = {
                    'type': index_type,
                }

                resources.append({
                    'service': 'resource-explorer-2',
                    'type': 'index',
                    'id': index_arn.split('/')[-1] if '/' in index_arn else index_arn,
                    'arn': index_arn,
                    'name': f"{index_type.lower()}-index",
                    'region': index_region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Views
    try:
        paginator = explorer.get_paginator('list_views')
        for page in paginator.paginate():
            for view_arn in page.get('Views', []):
                # Extract view name from ARN
                view_name = view_arn.split('/view/')[-1].split('/')[0] if '/view/' in view_arn else view_arn

                resources.append({
                    'service': 'resource-explorer-2',
                    'type': 'view',
                    'id': view_name,
                    'arn': view_arn,
                    'name': view_name,
                    'region': region,
                    'details': {},
                    'tags': {}
                })
    except Exception:
        pass

    return resources
