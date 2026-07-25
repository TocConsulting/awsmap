"""
Inspector2 resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_inspector2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Inspector2 resources: coverage statistics, filters.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    inspector2 = session.client('inspector2', region_name=region)

    # Get Inspector2 status
    try:
        status_response = inspector2.batch_get_account_status(
            accountIds=[account_id]
        )

        for account_status in status_response.get('accounts', []):
            if account_status.get('state', {}).get('status') == 'ENABLED':
                resources.append({
                    'service': 'inspector2',
                    'type': 'account-status',
                    'id': account_id,
                    'arn': f"arn:aws:inspector2:{region}:{account_id}:account",
                    'name': f"inspector2-{account_id}",
                    'region': region,
                    'details': {
                        'status': account_status.get('state', {}).get('status'),
                        'resource_status': account_status.get('resourceState'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Filters
    try:
        paginator = inspector2.get_paginator('list_filters')
        for page in paginator.paginate():
            for filter_item in page.get('filters', []):
                filter_arn = filter_item['arn']
                filter_name = filter_item['name']

                # Get tags
                tags = filter_item.get('tags', {})

                resources.append({
                    'service': 'inspector2',
                    'type': 'filter',
                    'id': filter_name,
                    'arn': filter_arn,
                    'name': filter_name,
                    'region': region,
                    'details': {
                        'description': filter_item.get('description'),
                        'action': filter_item.get('action'),
                        'owner_id': filter_item.get('ownerId'),
                        'reason': filter_item.get('reason'),
                        'created_at': str(filter_item.get('createdAt', '')),
                        'updated_at': str(filter_item.get('updatedAt', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
