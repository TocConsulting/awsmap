"""
AWS Elemental MediaTailor resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


# MediaTailor supported regions (from https://docs.aws.amazon.com/general/latest/gr/mediatailor.html)
MEDIATAILOR_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'af-south-1',
    'ap-south-1', 'ap-south-2', 'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
    'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-4',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-3', 'eu-north-1',
    'me-central-1',
    'sa-east-1',
}


def collect_mediatailor_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Elemental MediaTailor resources: playback configurations, channels, source locations.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in MEDIATAILOR_REGIONS:
        return []

    resources = []
    mediatailor = session.client('mediatailor', region_name=region)

    # Playback Configurations
    try:
        paginator = mediatailor.get_paginator('list_playback_configurations')
        for page in paginator.paginate():
            for config in page.get('Items', []):
                config_arn = config.get('PlaybackConfigurationArn', '')
                config_name = config.get('Name', config_arn.split('/')[-1])

                details = {
                    'ad_decision_server_url': config.get('AdDecisionServerUrl'),
                    'video_content_source_url': config.get('VideoContentSourceUrl'),
                    'personalization_threshold_seconds': config.get('PersonalizationThresholdSeconds'),
                    'session_initialization_endpoint_prefix': config.get('SessionInitializationEndpointPrefix'),
                }

                resources.append({
                    'service': 'mediatailor',
                    'type': 'playback-configuration',
                    'id': config_name,
                    'arn': config_arn,
                    'name': config_name,
                    'region': region,
                    'details': details,
                    'tags': config.get('Tags', {})
                })
    except Exception:
        pass

    # Channels
    try:
        paginator = mediatailor.get_paginator('list_channels')
        for page in paginator.paginate():
            for channel in page.get('Items', []):
                channel_arn = channel.get('Arn', '')
                channel_name = channel.get('ChannelName', channel_arn.split('/')[-1])

                details = {
                    'channel_state': channel.get('ChannelState'),
                    'creation_time': str(channel.get('CreationTime', '')) if channel.get('CreationTime') else None,
                    'playback_mode': channel.get('PlaybackMode'),
                    'tier': channel.get('Tier'),
                }

                resources.append({
                    'service': 'mediatailor',
                    'type': 'channel',
                    'id': channel_name,
                    'arn': channel_arn,
                    'name': channel_name,
                    'region': region,
                    'details': details,
                    'tags': channel.get('Tags', {})
                })
    except Exception:
        pass

    # Source Locations
    try:
        paginator = mediatailor.get_paginator('list_source_locations')
        for page in paginator.paginate():
            for location in page.get('Items', []):
                location_arn = location.get('Arn', '')
                location_name = location.get('SourceLocationName', location_arn.split('/')[-1])

                http_config = location.get('HttpConfiguration', {})
                details = {
                    'base_url': http_config.get('BaseUrl'),
                    'creation_time': str(location.get('CreationTime', '')) if location.get('CreationTime') else None,
                }

                resources.append({
                    'service': 'mediatailor',
                    'type': 'source-location',
                    'id': location_name,
                    'arn': location_arn,
                    'name': location_name,
                    'region': region,
                    'details': details,
                    'tags': location.get('Tags', {})
                })
    except Exception:
        pass

    return resources
