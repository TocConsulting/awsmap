"""
SNS resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_sns_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect SNS resources: topics, subscriptions.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sns = session.client('sns', region_name=region)

    # SNS Topics
    topics = []
    try:
        paginator = sns.get_paginator('list_topics')
        for page in paginator.paginate():
            for topic in page.get('Topics', []):
                topics.append(topic['TopicArn'])
    except Exception:
        pass

    for topic_arn in topics:
        try:
            # Get topic attributes
            attr_response = sns.get_topic_attributes(TopicArn=topic_arn)
            attributes = attr_response.get('Attributes', {})

            topic_name = topic_arn.split(':')[-1]

            # Get tags
            tags = {}
            try:
                tag_response = sns.list_tags_for_resource(ResourceArn=topic_arn)
                for tag in tag_response.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            resources.append({
                'service': 'sns',
                'type': 'topic',
                'id': topic_name,
                'arn': topic_arn,
                'name': attributes.get('DisplayName') or topic_name,
                'region': region,
                'details': {
                    'display_name': attributes.get('DisplayName'),
                    'subscriptions_confirmed': int(attributes.get('SubscriptionsConfirmed', 0)),
                    'subscriptions_pending': int(attributes.get('SubscriptionsPending', 0)),
                    'subscriptions_deleted': int(attributes.get('SubscriptionsDeleted', 0)),
                    'delivery_policy': attributes.get('DeliveryPolicy'),
                    'effective_delivery_policy': attributes.get('EffectiveDeliveryPolicy'),
                    'kms_master_key_id': attributes.get('KmsMasterKeyId'),
                    'fifo_topic': attributes.get('FifoTopic') == 'true',
                    'content_based_deduplication': attributes.get('ContentBasedDeduplication') == 'true',
                },
                'tags': tags
            })
        except Exception:
            pass

    # SNS Subscriptions
    try:
        paginator = sns.get_paginator('list_subscriptions')
        for page in paginator.paginate():
            for sub in page.get('Subscriptions', []):
                sub_arn = sub.get('SubscriptionArn', '')

                # Skip pending confirmations
                if sub_arn == 'PendingConfirmation':
                    continue

                topic_arn = sub.get('TopicArn', '')
                topic_name = topic_arn.split(':')[-1] if topic_arn else 'unknown'

                resources.append({
                    'service': 'sns',
                    'type': 'subscription',
                    'id': sub_arn.split(':')[-1] if ':' in sub_arn else sub_arn,
                    'arn': sub_arn,
                    'name': f"{topic_name}-{sub.get('Protocol', '')}",
                    'region': region,
                    'details': {
                        'topic_arn': topic_arn,
                        'protocol': sub.get('Protocol'),
                        'endpoint': sub.get('Endpoint'),
                        'owner': sub.get('Owner'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
