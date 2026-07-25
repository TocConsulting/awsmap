"""
AWS Interactive Video Service (IVS) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# IVS supported regions (from https://docs.aws.amazon.com/general/latest/gr/ivs.html)
IVS_REGIONS = {
    'us-east-1', 'us-west-2',
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2',
    'eu-central-1', 'eu-west-1',
}


def collect_ivs_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS IVS resources: channels, playback key pairs, and recording configurations.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in IVS_REGIONS:
        return []

    resources = []
    ivs = session.client('ivs', region_name=region)

    # Channels
    try:
        paginator = ivs.get_paginator('list_channels')
        for page in paginator.paginate():
            for channel in page.get('channels', []):
                channel_arn = channel['arn']
                channel_name = channel.get('name', channel_arn.split('/')[-1])

                details = {
                    'latency_mode': channel.get('latencyMode'),
                    'authorized': channel.get('authorized'),
                    'recording_configuration_arn': channel.get('recordingConfigurationArn'),
                    'type': channel.get('type'),
                    'preset': channel.get('preset'),
                    'playback_restriction_policy_arn': channel.get('playbackRestrictionPolicyArn'),
                }

                tags = channel.get('tags', {})

                resources.append({
                    'service': 'ivs',
                    'type': 'channel',
                    'id': channel_name,
                    'arn': channel_arn,
                    'name': channel_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Playback Key Pairs
    try:
        paginator = ivs.get_paginator('list_playback_key_pairs')
        for page in paginator.paginate():
            for pkp in page.get('keyPairs', []):
                pkp_arn = pkp['arn']
                pkp_name = pkp.get('name', pkp_arn.split('/')[-1])

                details = {
                    'fingerprint': pkp.get('fingerprint'),
                }

                tags = pkp.get('tags', {})

                resources.append({
                    'service': 'ivs',
                    'type': 'playback-key-pair',
                    'id': pkp_name,
                    'arn': pkp_arn,
                    'name': pkp_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Recording Configurations
    try:
        paginator = ivs.get_paginator('list_recording_configurations')
        for page in paginator.paginate():
            for rc in page.get('recordingConfigurations', []):
                rc_arn = rc['arn']
                rc_name = rc.get('name', rc_arn.split('/')[-1])

                details = {
                    'state': rc.get('state'),
                    'destination_configuration': rc.get('destinationConfiguration', {}),
                }

                tags = rc.get('tags', {})

                resources.append({
                    'service': 'ivs',
                    'type': 'recording-configuration',
                    'id': rc_name,
                    'arn': rc_arn,
                    'name': rc_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
