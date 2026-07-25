"""
AWS Health resource collector.

Note: AWS Health API requires Business, Enterprise On-Ramp, or Enterprise Support plan.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_health_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Health events affecting the account.

    Note: Requires Business or Enterprise Support plan. Returns empty if not available.

    Args:
        session: boto3.Session to use
        region: AWS region (ignored - Health is a global service using us-east-1)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    # Health API must be called from us-east-1
    health = session.client('health', region_name='us-east-1')

    # Events (open events only, not historical)
    try:
        paginator = health.get_paginator('describe_events')
        for page in paginator.paginate(
            filter={
                'eventStatusCodes': ['open', 'upcoming']
            }
        ):
            for event in page.get('events', []):
                event_arn = event.get('arn', '')
                event_type = event.get('eventTypeCode', '')

                details = {
                    'service': event.get('service'),
                    'event_type_code': event_type,
                    'event_type_category': event.get('eventTypeCategory'),
                    'event_scope_code': event.get('eventScopeCode'),
                    'availability_zone': event.get('availabilityZone'),
                    'start_time': str(event.get('startTime', '')),
                    'end_time': str(event.get('endTime', '')),
                    'last_updated_time': str(event.get('lastUpdatedTime', '')),
                    'status_code': event.get('statusCode'),
                }

                # Get event details
                try:
                    detail_response = health.describe_event_details(eventArns=[event_arn])
                    for detail in detail_response.get('successfulSet', []):
                        event_detail = detail.get('event', {})
                        event_description = detail.get('eventDescription', {})
                        details['description'] = event_description.get('latestDescription')
                except Exception:
                    pass

                # Get affected entities count
                try:
                    entities_response = health.describe_affected_entities(
                        filter={'eventArns': [event_arn]}
                    )
                    entities = entities_response.get('entities', [])
                    details['affected_entities_count'] = len(entities)
                    details['affected_entity_values'] = [e.get('entityValue') for e in entities[:10]]
                except Exception:
                    pass

                resources.append({
                    'service': 'health',
                    'type': 'event',
                    'id': event_arn.split('/')[-1] if event_arn else event_type,
                    'arn': event_arn,
                    'name': event_type,
                    'region': event.get('region', 'global'),
                    'details': details,
                    'tags': {}
                })
    except health.exceptions.SubscriptionRequiredException:
        # Account doesn't have Business/Enterprise Support
        return []
    except Exception:
        pass

    return resources
