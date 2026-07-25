"""
CodePipeline resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_codepipeline_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CodePipeline resources: pipelines.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    codepipeline = session.client('codepipeline', region_name=region)

    try:
        paginator = codepipeline.get_paginator('list_pipelines')
        for page in paginator.paginate():
            for pipeline_summary in page.get('pipelines', []):
                pipeline_name = pipeline_summary['name']

                try:
                    # Get pipeline details
                    pipeline_response = codepipeline.get_pipeline(name=pipeline_name)
                    pipeline = pipeline_response.get('pipeline', {})
                    metadata = pipeline_response.get('metadata', {})

                    pipeline_arn = metadata.get('pipelineArn', f"arn:aws:codepipeline:{region}:{account_id}:{pipeline_name}")

                    # Get tags
                    tags = {}
                    try:
                        tag_response = codepipeline.list_tags_for_resource(resourceArn=pipeline_arn)
                        for tag in tag_response.get('tags', []):
                            tags[tag.get('key', '')] = tag.get('value', '')
                    except Exception:
                        pass

                    # Count stages and actions
                    stages = pipeline.get('stages', [])
                    action_count = sum(len(s.get('actions', [])) for s in stages)

                    resources.append({
                        'service': 'codepipeline',
                        'type': 'pipeline',
                        'id': pipeline_name,
                        'arn': pipeline_arn,
                        'name': pipeline_name,
                        'region': region,
                        'details': {
                            'version': pipeline.get('version'),
                            'role_arn': pipeline.get('roleArn'),
                            'artifact_store_type': pipeline.get('artifactStore', {}).get('type'),
                            'artifact_store_location': pipeline.get('artifactStore', {}).get('location'),
                            'stages_count': len(stages),
                            'actions_count': action_count,
                            'pipeline_type': pipeline.get('pipelineType'),
                            'execution_mode': pipeline.get('executionMode'),
                            'created': str(metadata.get('created', '')),
                            'updated': str(metadata.get('updated', '')),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
