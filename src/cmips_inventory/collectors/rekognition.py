"""
AWS Rekognition resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Rekognition supported regions (from https://docs.aws.amazon.com/general/latest/gr/rekognition.html)
REKOGNITION_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-south-2',
    'il-central-1',
}


def collect_rekognition_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Rekognition resources: collections, projects, and stream processors.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in REKOGNITION_REGIONS:
        return []

    resources = []
    rek = session.client('rekognition', region_name=region)

    # Collections
    try:
        paginator = rek.get_paginator('list_collections')
        for page in paginator.paginate():
            for collection_id in page.get('CollectionIds', []):
                details = {}

                # Get collection details
                try:
                    coll_info = rek.describe_collection(CollectionId=collection_id)
                    details['face_count'] = coll_info.get('FaceCount')
                    details['face_model_version'] = coll_info.get('FaceModelVersion')
                    details['creation_timestamp'] = str(coll_info.get('CreationTimestamp', ''))
                    details['user_count'] = coll_info.get('UserCount')
                    collection_arn = coll_info.get('CollectionARN', '')
                except Exception:
                    collection_arn = f"arn:aws:rekognition:{region}:{account_id}:collection/{collection_id}"

                resources.append({
                    'service': 'rekognition',
                    'type': 'collection',
                    'id': collection_id,
                    'arn': collection_arn,
                    'name': collection_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Projects (Custom Labels)
    try:
        paginator = rek.get_paginator('describe_projects')
        for page in paginator.paginate():
            for project in page.get('ProjectDescriptions', []):
                project_arn = project['ProjectArn']
                project_name = project_arn.split('/')[-1] if '/' in project_arn else project_arn

                details = {
                    'status': project.get('Status'),
                    'creation_timestamp': str(project.get('CreationTimestamp', '')),
                    'feature': project.get('Feature'),
                    'auto_update': project.get('AutoUpdate'),
                }

                # Count datasets
                datasets = project.get('Datasets', [])
                if datasets:
                    details['dataset_count'] = len(datasets)

                resources.append({
                    'service': 'rekognition',
                    'type': 'project',
                    'id': project_name,
                    'arn': project_arn,
                    'name': project_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Stream Processors
    try:
        paginator = rek.get_paginator('list_stream_processors')
        for page in paginator.paginate():
            for processor in page.get('StreamProcessors', []):
                processor_name = processor['Name']
                processor_arn = processor.get('StreamProcessorArn', '')

                details = {
                    'status': processor.get('Status'),
                }

                # Get stream processor details
                try:
                    sp_info = rek.describe_stream_processor(Name=processor_name)
                    details['status'] = sp_info.get('Status')
                    details['status_message'] = sp_info.get('StatusMessage')
                    details['creation_timestamp'] = str(sp_info.get('CreationTimestamp', ''))
                    details['last_update_timestamp'] = str(sp_info.get('LastUpdateTimestamp', ''))
                    details['kinesis_video_stream_arn'] = sp_info.get('Input', {}).get('KinesisVideoStream', {}).get('Arn')
                    details['kinesis_data_stream_arn'] = sp_info.get('Output', {}).get('KinesisDataStream', {}).get('Arn')
                    details['role_arn'] = sp_info.get('RoleArn')
                except Exception:
                    pass

                resources.append({
                    'service': 'rekognition',
                    'type': 'stream-processor',
                    'id': processor_name,
                    'arn': processor_arn,
                    'name': processor_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
