"""
AWS DataSync resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_datasync_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS DataSync resources: agents, locations, and tasks.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    datasync = session.client('datasync', region_name=region)

    # Agents
    try:
        paginator = datasync.get_paginator('list_agents')
        for page in paginator.paginate():
            for agent in page.get('Agents', []):
                agent_arn = agent['AgentArn']
                agent_name = agent.get('Name', agent_arn.split('/')[-1])

                details = {
                    'status': agent.get('Status'),
                    'platform': agent.get('Platform', {}).get('Version'),
                }

                # Get full agent details
                try:
                    agent_detail = datasync.describe_agent(AgentArn=agent_arn)
                    details['vpc_endpoint_id'] = agent_detail.get('VpcEndpointId')
                    details['private_link_config'] = agent_detail.get('PrivateLinkConfig')
                    details['created_time'] = str(agent_detail.get('CreationTime', ''))
                    details['last_connection_time'] = str(agent_detail.get('LastConnectionTime', ''))
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_paginator = datasync.get_paginator('list_tags_for_resource')
                    for tag_page in tag_paginator.paginate(ResourceArn=agent_arn):
                        for tag in tag_page.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'datasync',
                    'type': 'agent',
                    'id': agent_arn.split('/')[-1],
                    'arn': agent_arn,
                    'name': agent_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Locations
    try:
        paginator = datasync.get_paginator('list_locations')
        for page in paginator.paginate():
            for location in page.get('Locations', []):
                location_arn = location['LocationArn']
                location_uri = location.get('LocationUri', '')

                details = {
                    'location_uri': location_uri,
                }

                # Determine location type from ARN
                location_type = 'unknown'
                if '/loc-' in location_arn:
                    # Try to get more details based on URI prefix
                    if location_uri.startswith('s3://'):
                        location_type = 's3'
                    elif location_uri.startswith('efs://'):
                        location_type = 'efs'
                    elif location_uri.startswith('nfs://'):
                        location_type = 'nfs'
                    elif location_uri.startswith('smb://'):
                        location_type = 'smb'
                    elif location_uri.startswith('fsxw://'):
                        location_type = 'fsx-windows'
                    elif location_uri.startswith('fsxl://'):
                        location_type = 'fsx-lustre'
                    elif location_uri.startswith('fsxo://'):
                        location_type = 'fsx-ontap'
                    elif location_uri.startswith('fsxz://'):
                        location_type = 'fsx-openzfs'
                    elif location_uri.startswith('hdfs://'):
                        location_type = 'hdfs'
                    elif 'blob.core.windows.net' in location_uri:
                        location_type = 'azure-blob'

                details['location_type'] = location_type

                # Get tags
                tags = {}
                try:
                    tag_paginator = datasync.get_paginator('list_tags_for_resource')
                    for tag_page in tag_paginator.paginate(ResourceArn=location_arn):
                        for tag in tag_page.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'datasync',
                    'type': 'location',
                    'id': location_arn.split('/')[-1],
                    'arn': location_arn,
                    'name': location_uri or location_arn.split('/')[-1],
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Tasks
    try:
        paginator = datasync.get_paginator('list_tasks')
        for page in paginator.paginate():
            for task in page.get('Tasks', []):
                task_arn = task['TaskArn']
                task_name = task.get('Name', task_arn.split('/')[-1])

                details = {
                    'status': task.get('Status'),
                }

                # Get full task details
                try:
                    task_detail = datasync.describe_task(TaskArn=task_arn)
                    details['source_location_arn'] = task_detail.get('SourceLocationArn')
                    details['destination_location_arn'] = task_detail.get('DestinationLocationArn')
                    details['cloud_watch_log_group_arn'] = task_detail.get('CloudWatchLogGroupArn')
                    details['created_time'] = str(task_detail.get('CreationTime', ''))
                    details['current_task_execution_arn'] = task_detail.get('CurrentTaskExecutionArn')

                    options = task_detail.get('Options', {})
                    if options:
                        details['verify_mode'] = options.get('VerifyMode')
                        details['overwrite_mode'] = options.get('OverwriteMode')
                        details['transfer_mode'] = options.get('TransferMode')
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_paginator = datasync.get_paginator('list_tags_for_resource')
                    for tag_page in tag_paginator.paginate(ResourceArn=task_arn):
                        for tag in tag_page.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'datasync',
                    'type': 'task',
                    'id': task_arn.split('/')[-1],
                    'arn': task_arn,
                    'name': task_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
