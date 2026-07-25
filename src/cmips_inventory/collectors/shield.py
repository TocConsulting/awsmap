"""
AWS Shield Advanced resource collector.

Note: Shield Advanced is a global service that requires us-east-1 for API operations.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_shield_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Shield Advanced resources: subscription, protections, and protection groups.

    Note: Shield Advanced APIs must be called from us-east-1 region.

    Args:
        session: boto3.Session to use
        region: AWS region (ignored - always uses us-east-1)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    # Shield Advanced requires us-east-1 for all API calls
    shield = session.client('shield', region_name='us-east-1')

    # Check if Shield Advanced is active
    try:
        sub_state = shield.get_subscription_state()
        if sub_state.get('SubscriptionState') != 'ACTIVE':
            return []
    except Exception:
        return []

    # Subscription details
    try:
        sub = shield.describe_subscription()
        subscription = sub.get('Subscription', {})

        details = {
            'start_time': str(subscription.get('StartTime', '')),
            'end_time': str(subscription.get('EndTime', '')),
            'time_commitment_in_seconds': subscription.get('TimeCommitmentInSeconds'),
            'auto_renew': subscription.get('AutoRenew'),
            'proactive_engagement_status': subscription.get('ProactiveEngagementStatus'),
            'subscription_arn': subscription.get('SubscriptionArn'),
        }

        # Limits
        limits = subscription.get('Limits', [])
        for limit in limits:
            limit_type = limit.get('Type', '').lower().replace(' ', '_')
            details[f"limit_{limit_type}"] = limit.get('Max')

        resources.append({
            'service': 'shield',
            'type': 'subscription',
            'id': 'shield-advanced-subscription',
            'arn': subscription.get('SubscriptionArn', f"arn:aws:shield::{account_id}:subscription"),
            'name': 'Shield Advanced Subscription',
            'region': 'global',
            'details': details,
            'tags': {}
        })
    except Exception:
        pass

    # Protections
    try:
        paginator = shield.get_paginator('list_protections')
        for page in paginator.paginate():
            for protection in page.get('Protections', []):
                protection_id = protection['Id']
                protection_name = protection.get('Name', protection_id)
                protection_arn = protection.get('ProtectionArn', '')

                details = {
                    'resource_arn': protection.get('ResourceArn'),
                    'health_check_ids': protection.get('HealthCheckIds', []),
                    'application_layer_automatic_response_status': protection.get('ApplicationLayerAutomaticResponseConfiguration', {}).get('Status'),
                }

                # Get tags
                tags = {}
                if protection_arn:
                    try:
                        tag_response = shield.list_tags_for_resource(ResourceARN=protection_arn)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                resources.append({
                    'service': 'shield',
                    'type': 'protection',
                    'id': protection_id,
                    'arn': protection_arn,
                    'name': protection_name,
                    'region': 'global',
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Protection Groups
    try:
        response = shield.list_protection_groups()
        for group in response.get('ProtectionGroups', []):
            group_id = group['ProtectionGroupId']
            group_arn = group.get('ProtectionGroupArn', '')

            details = {
                'aggregation': group.get('Aggregation'),
                'pattern': group.get('Pattern'),
                'resource_type': group.get('ResourceType'),
                'members': group.get('Members', []),
                'members_count': len(group.get('Members', [])),
            }

            # Get tags
            tags = {}
            if group_arn:
                try:
                    tag_response = shield.list_tags_for_resource(ResourceARN=group_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

            resources.append({
                'service': 'shield',
                'type': 'protection-group',
                'id': group_id,
                'arn': group_arn,
                'name': group_id,
                'region': 'global',
                'details': details,
                'tags': tags
            })
    except Exception:
        pass

    return resources
