"""
Kinesis Data Streams resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_kinesis_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Kinesis Data Streams resources.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    kinesis = session.client('kinesis', region_name=region)

    # Data Streams
    try:
        paginator = kinesis.get_paginator('list_streams')
        for page in paginator.paginate():
            for stream_summary in page.get('StreamSummaries', []):
                stream_name = stream_summary['StreamName']
                stream_arn = stream_summary['StreamARN']

                try:
                    # Get stream details
                    stream_response = kinesis.describe_stream_summary(StreamName=stream_name)
                    stream_desc = stream_response.get('StreamDescriptionSummary', {})

                    # Get tags
                    tags = {}
                    try:
                        tag_response = kinesis.list_tags_for_stream(StreamName=stream_name)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'kinesis',
                        'type': 'stream',
                        'id': stream_name,
                        'arn': stream_arn,
                        'name': stream_name,
                        'region': region,
                        'details': {
                            'status': stream_desc.get('StreamStatus'),
                            'stream_mode': stream_desc.get('StreamModeDetails', {}).get('StreamMode'),
                            'retention_period_hours': stream_desc.get('RetentionPeriodHours'),
                            'shard_count': stream_desc.get('OpenShardCount'),
                            'consumer_count': stream_desc.get('ConsumerCount'),
                            'encryption_type': stream_desc.get('EncryptionType'),
                            'key_id': stream_desc.get('KeyId'),
                            'creation_timestamp': str(stream_desc.get('StreamCreationTimestamp', '')),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # Stream Consumers
    try:
        paginator = kinesis.get_paginator('list_streams')
        for page in paginator.paginate():
            for stream_summary in page.get('StreamSummaries', []):
                stream_arn = stream_summary['StreamARN']
                stream_name = stream_summary['StreamName']

                try:
                    consumer_paginator = kinesis.get_paginator('list_stream_consumers')
                    for consumer_page in consumer_paginator.paginate(StreamARN=stream_arn):
                        for consumer in consumer_page.get('Consumers', []):
                            consumer_name = consumer['ConsumerName']
                            consumer_arn = consumer['ConsumerARN']

                            resources.append({
                                'service': 'kinesis',
                                'type': 'stream-consumer',
                                'id': consumer_name,
                                'arn': consumer_arn,
                                'name': consumer_name,
                                'region': region,
                                'details': {
                                    'stream_arn': stream_arn,
                                    'stream_name': stream_name,
                                    'consumer_status': consumer.get('ConsumerStatus'),
                                    'consumer_creation_timestamp': str(consumer.get('ConsumerCreationTimestamp', '')),
                                },
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
