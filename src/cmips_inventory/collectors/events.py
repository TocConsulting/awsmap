"""
EventBridge resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_events_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EventBridge resources: event buses, rules, archives, connections, API destinations.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    events = session.client('events', region_name=region)

    # Event Buses (not pageable)
    event_buses = []
    try:
        response = events.list_event_buses()
        for bus in response.get('EventBuses', []):
            event_buses.append(bus)
            bus_name = bus['Name']
            bus_arn = bus['Arn']

            # Skip default bus (AWS-created)
            if bus_name == 'default':
                continue

            # Get tags
            tags = {}
            try:
                tag_response = events.list_tags_for_resource(ResourceARN=bus_arn)
                for tag in tag_response.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            resources.append({
                'service': 'events',
                'type': 'event-bus',
                'id': bus_name,
                'arn': bus_arn,
                'name': bus_name,
                'region': region,
                'details': {
                    'policy': bus.get('Policy'),
                },
                'tags': tags
            })
    except Exception:
        pass

    # Rules (for each event bus)
    for bus in event_buses:
        bus_name = bus['Name']
        try:
            paginator = events.get_paginator('list_rules')
            for page in paginator.paginate(EventBusName=bus_name):
                for rule in page.get('Rules', []):
                    rule_name = rule['Name']
                    rule_arn = rule['Arn']

                    # Get tags
                    tags = {}
                    try:
                        tag_response = events.list_tags_for_resource(ResourceARN=rule_arn)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    # Get targets count
                    targets_count = 0
                    try:
                        targets_response = events.list_targets_by_rule(
                            Rule=rule_name,
                            EventBusName=bus_name
                        )
                        targets_count = len(targets_response.get('Targets', []))
                    except Exception:
                        pass

                    resources.append({
                        'service': 'events',
                        'type': 'rule',
                        'id': rule_name,
                        'arn': rule_arn,
                        'name': rule_name,
                        'region': region,
                        'details': {
                            'event_bus_name': bus_name,
                            'description': rule.get('Description'),
                            'state': rule.get('State'),
                            'schedule_expression': rule.get('ScheduleExpression'),
                            'event_pattern': rule.get('EventPattern'),
                            'managed_by': rule.get('ManagedBy'),
                            'targets_count': targets_count,
                        },
                        'tags': tags
                    })
        except Exception:
            pass

    # Archives
    try:
        response = events.list_archives()
        for archive in response.get('Archives', []):
            archive_name = archive['ArchiveName']
            archive_arn = f"arn:aws:events:{region}:{account_id}:archive/{archive_name}"

            resources.append({
                'service': 'events',
                'type': 'archive',
                'id': archive_name,
                'arn': archive_arn,
                'name': archive_name,
                'region': region,
                'details': {
                    'event_source_arn': archive.get('EventSourceArn'),
                    'state': archive.get('State'),
                    'state_reason': archive.get('StateReason'),
                    'retention_days': archive.get('RetentionDays'),
                    'size_bytes': archive.get('SizeBytes'),
                    'event_count': archive.get('EventCount'),
                    'creation_time': str(archive.get('CreationTime', '')),
                },
                'tags': {}
            })
    except Exception:
        pass

    # Connections (for API Destinations)
    try:
        response = events.list_connections()
        for conn in response.get('Connections', []):
            conn_name = conn['Name']
            conn_arn = conn['ConnectionArn']

            resources.append({
                'service': 'events',
                'type': 'connection',
                'id': conn_name,
                'arn': conn_arn,
                'name': conn_name,
                'region': region,
                'details': {
                    'state': conn.get('ConnectionState'),
                    'state_reason': conn.get('StateReason'),
                    'authorization_type': conn.get('AuthorizationType'),
                    'creation_time': str(conn.get('CreationTime', '')),
                    'last_modified_time': str(conn.get('LastModifiedTime', '')),
                    'last_authorized_time': str(conn.get('LastAuthorizedTime', '')),
                },
                'tags': {}
            })
    except Exception:
        pass

    # API Destinations
    try:
        response = events.list_api_destinations()
        for dest in response.get('ApiDestinations', []):
            dest_name = dest['Name']
            dest_arn = dest['ApiDestinationArn']

            resources.append({
                'service': 'events',
                'type': 'api-destination',
                'id': dest_name,
                'arn': dest_arn,
                'name': dest_name,
                'region': region,
                'details': {
                    'state': dest.get('ApiDestinationState'),
                    'connection_arn': dest.get('ConnectionArn'),
                    'invocation_endpoint': dest.get('InvocationEndpoint'),
                    'http_method': dest.get('HttpMethod'),
                    'invocation_rate_limit': dest.get('InvocationRateLimitPerSecond'),
                    'creation_time': str(dest.get('CreationTime', '')),
                    'last_modified_time': str(dest.get('LastModifiedTime', '')),
                },
                'tags': {}
            })
    except Exception:
        pass

    return resources
