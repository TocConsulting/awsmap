"""
SQS resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_sqs_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect SQS resources: queues.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sqs = session.client('sqs', region_name=region)

    try:
        paginator = sqs.get_paginator('list_queues')
        for page in paginator.paginate():
            for queue_url in page.get('QueueUrls', []):
                try:
                    # Get queue attributes
                    attr_response = sqs.get_queue_attributes(
                        QueueUrl=queue_url,
                        AttributeNames=['All']
                    )
                    attributes = attr_response.get('Attributes', {})

                    queue_arn = attributes.get('QueueArn', '')
                    queue_name = queue_url.split('/')[-1]

                    # Get tags
                    tags = {}
                    try:
                        tag_response = sqs.list_queue_tags(QueueUrl=queue_url)
                        tags = tag_response.get('Tags', {})
                    except Exception:
                        pass

                    resources.append({
                        'service': 'sqs',
                        'type': 'queue',
                        'id': queue_name,
                        'arn': queue_arn,
                        'name': queue_name,
                        'region': region,
                        'details': {
                            'url': queue_url,
                            'approximate_messages': int(attributes.get('ApproximateNumberOfMessages', 0)),
                            'approximate_messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                            'approximate_messages_not_visible': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                            'visibility_timeout': int(attributes.get('VisibilityTimeout', 0)),
                            'message_retention_period': int(attributes.get('MessageRetentionPeriod', 0)),
                            'maximum_message_size': int(attributes.get('MaximumMessageSize', 0)),
                            'delay_seconds': int(attributes.get('DelaySeconds', 0)),
                            'receive_message_wait_time': int(attributes.get('ReceiveMessageWaitTimeSeconds', 0)),
                            'fifo_queue': attributes.get('FifoQueue') == 'true',
                            'content_based_deduplication': attributes.get('ContentBasedDeduplication') == 'true',
                            'kms_master_key_id': attributes.get('KmsMasterKeyId'),
                            'dead_letter_target_arn': attributes.get('RedrivePolicy'),
                            'created_timestamp': attributes.get('CreatedTimestamp'),
                            'last_modified_timestamp': attributes.get('LastModifiedTimestamp'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
