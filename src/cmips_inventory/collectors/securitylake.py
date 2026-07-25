"""
AWS Security Lake resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_securitylake_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Security Lake resources: data lakes and subscribers.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    securitylake = session.client('securitylake', region_name=region)

    # Data Lakes
    try:
        response = securitylake.list_data_lakes()
        for lake in response.get('dataLakes', []):
            lake_arn = lake.get('dataLakeArn', '')
            lake_region = lake.get('region', region)

            # Only collect for current region to avoid duplicates
            if lake_region != region:
                continue

            lifecycle = lake.get('lifecycleConfiguration', {})
            details = {
                'status': lake.get('createStatus'),
                's3_bucket_arn': lake.get('s3BucketArn'),
                'encryption_key': lake.get('encryptionConfiguration', {}).get('kmsKeyId'),
                'retention_days': lifecycle.get('expiration', {}).get('days') if lifecycle else None,
            }

            resources.append({
                'service': 'securitylake',
                'type': 'data-lake',
                'id': lake_region,
                'arn': lake_arn,
                'name': f"security-lake-{lake_region}",
                'region': lake_region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Subscribers
    try:
        paginator = securitylake.get_paginator('list_subscribers')
        for page in paginator.paginate():
            for subscriber in page.get('subscribers', []):
                subscriber_id = subscriber.get('subscriberId', '')
                subscriber_arn = subscriber.get('subscriberArn', f"arn:aws:securitylake:{region}:{account_id}:subscriber/{subscriber_id}")
                subscriber_name = subscriber.get('subscriberName', subscriber_id)

                identity = subscriber.get('subscriberIdentity', {})
                details = {
                    'description': subscriber.get('subscriberDescription'),
                    'status': subscriber.get('subscriberStatus'),
                    'external_id': identity.get('externalId'),
                    'principal': identity.get('principal'),
                    'access_types': subscriber.get('accessTypes', []),
                }

                resources.append({
                    'service': 'securitylake',
                    'type': 'subscriber',
                    'id': subscriber_id,
                    'arn': subscriber_arn,
                    'name': subscriber_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
