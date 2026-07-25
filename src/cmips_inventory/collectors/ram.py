"""
Resource Access Manager resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_ram_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect RAM resources: resource shares.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ram = session.client('ram', region_name=region)

    # Resource Shares (owned by this account)
    try:
        paginator = ram.get_paginator('get_resource_shares')
        for page in paginator.paginate(resourceOwner='SELF'):
            for share in page.get('resourceShares', []):
                share_arn = share['resourceShareArn']
                share_name = share.get('name', share_arn.split('/')[-1])

                # Tags are included in the response
                tags = {}
                for tag in share.get('tags', []):
                    tags[tag.get('key', '')] = tag.get('value', '')

                # Get shared resources count
                shared_resources = []
                try:
                    res_paginator = ram.get_paginator('list_resources')
                    for res_page in res_paginator.paginate(resourceOwner='SELF', resourceShareArns=[share_arn]):
                        shared_resources.extend(res_page.get('resources', []))
                except Exception:
                    pass

                # Get principals count
                principals = []
                try:
                    prin_paginator = ram.get_paginator('list_principals')
                    for prin_page in prin_paginator.paginate(resourceOwner='SELF', resourceShareArns=[share_arn]):
                        principals.extend(prin_page.get('principals', []))
                except Exception:
                    pass

                resources.append({
                    'service': 'ram',
                    'type': 'resource-share',
                    'id': share_arn.split('/')[-1],
                    'arn': share_arn,
                    'name': share_name,
                    'region': region,
                    'details': {
                        'status': share.get('status'),
                        'status_message': share.get('statusMessage'),
                        'allow_external_principals': share.get('allowExternalPrincipals'),
                        'creation_time': str(share.get('creationTime', '')),
                        'last_updated_time': str(share.get('lastUpdatedTime', '')),
                        'feature_set': share.get('featureSet'),
                        'shared_resources_count': len(shared_resources),
                        'principals_count': len(principals),
                        'resource_types': list(set(r.get('type') for r in shared_resources if r.get('type'))),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Resource Shares (shared with this account)
    try:
        paginator = ram.get_paginator('get_resource_shares')
        for page in paginator.paginate(resourceOwner='OTHER-ACCOUNTS'):
            for share in page.get('resourceShares', []):
                share_arn = share['resourceShareArn']
                share_name = share.get('name', share_arn.split('/')[-1])

                # Tags are included in the response
                tags = {}
                for tag in share.get('tags', []):
                    tags[tag.get('key', '')] = tag.get('value', '')

                resources.append({
                    'service': 'ram',
                    'type': 'resource-share-invitation',
                    'id': share_arn.split('/')[-1],
                    'arn': share_arn,
                    'name': share_name,
                    'region': region,
                    'details': {
                        'status': share.get('status'),
                        'owner_account_id': share.get('owningAccountId'),
                        'allow_external_principals': share.get('allowExternalPrincipals'),
                        'creation_time': str(share.get('creationTime', '')),
                        'last_updated_time': str(share.get('lastUpdatedTime', '')),
                        'feature_set': share.get('featureSet'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
