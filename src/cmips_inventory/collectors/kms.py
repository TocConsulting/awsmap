"""
KMS resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_kms_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect KMS resources: customer managed keys, aliases.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    kms = session.client('kms', region_name=region)

    # KMS Keys (customer managed only)
    try:
        paginator = kms.get_paginator('list_keys')
        for page in paginator.paginate():
            for key in page.get('Keys', []):
                key_id = key['KeyId']

                try:
                    # Get key details
                    key_response = kms.describe_key(KeyId=key_id)
                    key_metadata = key_response.get('KeyMetadata', {})

                    # Skip AWS managed keys
                    key_manager = key_metadata.get('KeyManager')
                    if key_manager != 'CUSTOMER':
                        continue

                    # Get tags
                    tags = {}
                    try:
                        tag_response = kms.list_resource_tags(KeyId=key_id)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('TagKey', '')] = tag.get('TagValue', '')
                    except Exception:
                        pass

                    # Get aliases for this key
                    aliases = []
                    try:
                        alias_response = kms.list_aliases(KeyId=key_id)
                        aliases = [a.get('AliasName') for a in alias_response.get('Aliases', [])]
                    except Exception:
                        pass

                    key_name = tags.get('Name') or (aliases[0] if aliases else key_id)

                    resources.append({
                        'service': 'kms',
                        'type': 'key',
                        'id': key_id,
                        'arn': key_metadata['Arn'],
                        'name': key_name,
                        'region': region,
                        'details': {
                            'key_state': key_metadata.get('KeyState'),
                            'key_usage': key_metadata.get('KeyUsage'),
                            'key_spec': key_metadata.get('KeySpec'),
                            'origin': key_metadata.get('Origin'),
                            'creation_date': str(key_metadata.get('CreationDate', '')),
                            'description': key_metadata.get('Description'),
                            'enabled': key_metadata.get('Enabled'),
                            'multi_region': key_metadata.get('MultiRegion'),
                            'aliases': aliases,
                            'deletion_date': str(key_metadata.get('DeletionDate', '')) if key_metadata.get('DeletionDate') else None,
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # KMS Aliases (that point to customer managed keys)
    try:
        paginator = kms.get_paginator('list_aliases')
        for page in paginator.paginate():
            for alias in page.get('Aliases', []):
                alias_name = alias.get('AliasName', '')

                # Skip AWS managed aliases
                if alias_name.startswith('alias/aws/'):
                    continue

                # Skip aliases without target keys
                target_key_id = alias.get('TargetKeyId')
                if not target_key_id:
                    continue

                resources.append({
                    'service': 'kms',
                    'type': 'alias',
                    'id': alias_name,
                    'arn': alias.get('AliasArn'),
                    'name': alias_name.replace('alias/', ''),
                    'region': region,
                    'details': {
                        'target_key_id': target_key_id,
                        'creation_date': str(alias.get('CreationDate', '')),
                        'last_updated_date': str(alias.get('LastUpdatedDate', '')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
