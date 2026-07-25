"""
Secrets Manager resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_secretsmanager_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Secrets Manager resources: secrets.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sm = session.client('secretsmanager', region_name=region)

    try:
        paginator = sm.get_paginator('list_secrets')
        for page in paginator.paginate():
            for secret in page.get('SecretList', []):
                secret_name = secret['Name']
                secret_arn = secret['ARN']

                # Get tags from the response
                tags = {}
                for tag in secret.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                resources.append({
                    'service': 'secretsmanager',
                    'type': 'secret',
                    'id': secret_name,
                    'arn': secret_arn,
                    'name': secret_name,
                    'region': region,
                    'details': {
                        'description': secret.get('Description'),
                        'kms_key_id': secret.get('KmsKeyId'),
                        'rotation_enabled': secret.get('RotationEnabled'),
                        'rotation_lambda_arn': secret.get('RotationLambdaARN'),
                        'rotation_rules': secret.get('RotationRules'),
                        'last_rotated_date': str(secret.get('LastRotatedDate', '')) if secret.get('LastRotatedDate') else None,
                        'last_changed_date': str(secret.get('LastChangedDate', '')) if secret.get('LastChangedDate') else None,
                        'last_accessed_date': str(secret.get('LastAccessedDate', '')) if secret.get('LastAccessedDate') else None,
                        'deleted_date': str(secret.get('DeletedDate', '')) if secret.get('DeletedDate') else None,
                        'primary_region': secret.get('PrimaryRegion'),
                        'owning_service': secret.get('OwningService'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
