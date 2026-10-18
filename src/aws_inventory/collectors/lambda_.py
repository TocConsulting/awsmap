"""
Lambda resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

from aws_inventory.parallel import bounded_map

_TAG_WORKERS = 4


def collect_lambda__resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Lambda resources: functions, layers, event source mappings.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    lambda_client = session.client('lambda', region_name=region)

    # Collect functions
    functions = []
    try:
        paginator = lambda_client.get_paginator('list_functions')
        for page in paginator.paginate():
            functions.extend(page.get('Functions', []))
    except Exception:
        pass

    # Fetch tags with the same client (and therefore the same credentials) that
    # listed the functions. The previous asyncio path rebuilt a session from the
    # profile name, which silently used the wrong account for assumed-role and
    # environment credentials.
    def _tags(func_arn: str) -> Dict[str, str]:
        try:
            return lambda_client.list_tags(Resource=func_arn).get('Tags', {}) or {}
        except Exception:
            return {}

    arns = [f['FunctionArn'] for f in functions]
    tags_map = dict(zip(arns, bounded_map(_tags, arns, _TAG_WORKERS)))

    # Build function resources
    for func in functions:
        func_name = func['FunctionName']
        func_arn = func['FunctionArn']

        resources.append({
            'service': 'lambda',
            'type': 'function',
            'id': func_name,
            'arn': func_arn,
            'name': func_name,
            'region': region,
            'details': {
                'runtime': func.get('Runtime'),
                'handler': func.get('Handler'),
                'code_size': func.get('CodeSize'),
                'memory_size': func.get('MemorySize'),
                'timeout': func.get('Timeout'),
                'last_modified': func.get('LastModified'),
                'description': func.get('Description'),
                'role': func.get('Role'),
                'vpc_id': func.get('VpcConfig', {}).get('VpcId'),
                'architectures': func.get('Architectures', []),
                'package_type': func.get('PackageType'),
                'ephemeral_storage': func.get('EphemeralStorage', {}).get('Size'),
            },
            'tags': tags_map.get(func_arn, {})
        })

    # Lambda Layers
    try:
        paginator = lambda_client.get_paginator('list_layers')
        for page in paginator.paginate():
            for layer in page.get('Layers', []):
                layer_name = layer['LayerName']
                layer_arn = layer['LayerArn']
                latest_version = layer.get('LatestMatchingVersion', {})

                resources.append({
                    'service': 'lambda',
                    'type': 'layer',
                    'id': layer_name,
                    'arn': layer_arn,
                    'name': layer_name,
                    'region': region,
                    'details': {
                        'latest_version': latest_version.get('Version'),
                        'latest_version_arn': latest_version.get('LayerVersionArn'),
                        'description': latest_version.get('Description'),
                        'created_date': latest_version.get('CreatedDate'),
                        'compatible_runtimes': latest_version.get('CompatibleRuntimes', []),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Event Source Mappings
    try:
        paginator = lambda_client.get_paginator('list_event_source_mappings')
        for page in paginator.paginate():
            for esm in page.get('EventSourceMappings', []):
                esm_uuid = esm['UUID']
                func_arn = esm.get('FunctionArn', '')
                func_name = func_arn.split(':')[-1] if func_arn else 'unknown'

                resources.append({
                    'service': 'lambda',
                    'type': 'event-source-mapping',
                    'id': esm_uuid,
                    'arn': f"arn:aws:lambda:{region}:{account_id}:event-source-mapping:{esm_uuid}",
                    'name': f"{func_name}-{esm_uuid[:8]}",
                    'region': region,
                    'details': {
                        'function_arn': func_arn,
                        'event_source_arn': esm.get('EventSourceArn'),
                        'state': esm.get('State'),
                        'batch_size': esm.get('BatchSize'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources

