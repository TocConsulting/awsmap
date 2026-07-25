"""
AWS Elemental MediaLive resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# MediaLive supported regions (from https://docs.aws.amazon.com/general/latest/gr/medialive_region.html)
MEDIALIVE_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ap-south-1', 'ap-south-2', 'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
    'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-4',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1',
    'me-central-1',
    'sa-east-1',
}


def collect_medialive_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS MediaLive resources: channels, inputs, and input security groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in MEDIALIVE_REGIONS:
        return []

    resources = []
    ml = session.client('medialive', region_name=region)

    # Channels
    try:
        paginator = ml.get_paginator('list_channels')
        for page in paginator.paginate():
            for channel in page.get('Channels', []):
                channel_id = channel['Id']
                channel_arn = channel.get('Arn', '')
                channel_name = channel.get('Name', channel_id)

                details = {
                    'state': channel.get('State'),
                    'channel_class': channel.get('ChannelClass'),
                    'log_level': channel.get('LogLevel'),
                    'role_arn': channel.get('RoleArn'),
                    'pipelines_running_count': channel.get('PipelinesRunningCount'),
                    'input_attachments_count': len(channel.get('InputAttachments', [])),
                    'destinations_count': len(channel.get('Destinations', [])),
                }

                maintenance = channel.get('Maintenance', {})
                if maintenance:
                    details['maintenance_day'] = maintenance.get('MaintenanceDay')
                    details['maintenance_start_time'] = maintenance.get('MaintenanceStartTime')

                tags = channel.get('Tags', {})

                resources.append({
                    'service': 'medialive',
                    'type': 'channel',
                    'id': channel_id,
                    'arn': channel_arn,
                    'name': channel_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Inputs
    try:
        paginator = ml.get_paginator('list_inputs')
        for page in paginator.paginate():
            for input_item in page.get('Inputs', []):
                input_id = input_item['Id']
                input_arn = input_item.get('Arn', '')
                input_name = input_item.get('Name', input_id)

                details = {
                    'state': input_item.get('State'),
                    'type': input_item.get('Type'),
                    'input_class': input_item.get('InputClass'),
                    'input_source_type': input_item.get('InputSourceType'),
                    'attached_channels': input_item.get('AttachedChannels', []),
                    'security_groups': input_item.get('SecurityGroups', []),
                    'sources_count': len(input_item.get('Sources', [])),
                    'destinations_count': len(input_item.get('Destinations', [])),
                    'role_arn': input_item.get('RoleArn'),
                }

                tags = input_item.get('Tags', {})

                resources.append({
                    'service': 'medialive',
                    'type': 'input',
                    'id': input_id,
                    'arn': input_arn,
                    'name': input_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Input Security Groups
    try:
        paginator = ml.get_paginator('list_input_security_groups')
        for page in paginator.paginate():
            for sg in page.get('InputSecurityGroups', []):
                sg_id = sg['Id']
                sg_arn = sg.get('Arn', '')

                details = {
                    'state': sg.get('State'),
                    'whitelist_rules_count': len(sg.get('WhitelistRules', [])),
                    'inputs': sg.get('Inputs', []),
                }

                tags = sg.get('Tags', {})

                resources.append({
                    'service': 'medialive',
                    'type': 'input-security-group',
                    'id': sg_id,
                    'arn': sg_arn,
                    'name': sg_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
