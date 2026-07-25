"""
Amazon EventBridge Pipes resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_pipes_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EventBridge Pipes resources.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    pipes = session.client('pipes', region_name=region)

    # Pipes
    try:
        paginator = pipes.get_paginator('list_pipes')
        for page in paginator.paginate():
            for pipe in page.get('Pipes', []):
                pipe_arn = pipe.get('Arn', '')
                pipe_name = pipe.get('Name', pipe_arn.split('/')[-1])

                details = {
                    'current_state': pipe.get('CurrentState'),
                    'desired_state': pipe.get('DesiredState'),
                    'source': pipe.get('Source'),
                    'target': pipe.get('Target'),
                    'enrichment': pipe.get('Enrichment'),
                    'creation_time': str(pipe.get('CreationTime', '')) if pipe.get('CreationTime') else None,
                }

                resources.append({
                    'service': 'pipes',
                    'type': 'pipe',
                    'id': pipe_name,
                    'arn': pipe_arn,
                    'name': pipe_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
