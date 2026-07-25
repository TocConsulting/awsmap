"""
Amazon EventBridge Schema Registry resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_schemas_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EventBridge Schema Registry resources: registries, schemas, discoverers.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    schemas = session.client('schemas', region_name=region)

    # Registries (skip AWS-owned registries)
    try:
        paginator = schemas.get_paginator('list_registries')
        for page in paginator.paginate():
            for registry in page.get('Registries', []):
                registry_arn = registry.get('RegistryArn', '')
                registry_name = registry.get('RegistryName', registry_arn.split('/')[-1])

                # Skip AWS-owned registries
                if registry_name.startswith('aws.'):
                    continue

                details = {}

                # Get tags
                tags = {}
                try:
                    tag_response = schemas.list_tags_for_resource(ResourceArn=registry_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'schemas',
                    'type': 'registry',
                    'id': registry_name,
                    'arn': registry_arn,
                    'name': registry_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Discoverers
    try:
        paginator = schemas.get_paginator('list_discoverers')
        for page in paginator.paginate():
            for discoverer in page.get('Discoverers', []):
                discoverer_id = discoverer.get('DiscovererId', '')
                discoverer_arn = discoverer.get('DiscovererArn', '')

                details = {
                    'source_arn': discoverer.get('SourceArn'),
                    'state': discoverer.get('State'),
                    'cross_account': discoverer.get('CrossAccount'),
                }

                # Get tags
                tags = {}
                try:
                    tag_response = schemas.list_tags_for_resource(ResourceArn=discoverer_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'schemas',
                    'type': 'discoverer',
                    'id': discoverer_id,
                    'arn': discoverer_arn,
                    'name': discoverer_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
