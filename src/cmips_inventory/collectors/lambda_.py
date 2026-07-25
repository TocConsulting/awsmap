"""
Lambda resource collector.
"""

import asyncio

import aiobotocore.session
import boto3
from typing import List, Dict, Any, Optional


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

    # Fetch tags using asyncio
    tags_map = {}
    if functions:
        profile = session.profile_name
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tags_map = loop.run_until_complete(_fetch_tags_async(profile, region, [f['FunctionArn'] for f in functions]))
        except Exception:
            pass
        finally:
            loop.close()

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


async def _fetch_tags_async(profile: str, region: str, arns: List[str]) -> Dict[str, Dict[str, str]]:
    """Fetch tags for all functions using asyncio."""
    session = aiobotocore.session.AioSession(profile=profile)

    async with session.create_client('lambda', region_name=region) as client:
        async def get_tags(arn):
            try:
                resp = await client.list_tags(Resource=arn)
                return arn, resp.get('Tags', {})
            except Exception:
                return arn, {}

        tasks = [get_tags(arn) for arn in arns]
        results = await asyncio.gather(*tasks)
        return dict(results)
