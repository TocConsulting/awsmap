"""
AWS Resource Groups resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_resourcegroups_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Resource Groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    rg = session.client('resource-groups', region_name=region)

    # Resource Groups
    try:
        paginator = rg.get_paginator('list_groups')
        for page in paginator.paginate():
            for group in page.get('Groups', []):
                group_arn = group['GroupArn']
                group_name = group['Name']

                details = {
                    'description': group.get('Description'),
                    'criticality': group.get('Criticality'),
                    'owner': group.get('Owner'),
                    'display_name': group.get('DisplayName'),
                }

                # Get group query
                try:
                    query_response = rg.get_group_query(Group=group_name)
                    group_query = query_response.get('GroupQuery', {})
                    resource_query = group_query.get('ResourceQuery', {})
                    details['query_type'] = resource_query.get('Type')
                    details['query'] = resource_query.get('Query')
                except Exception:
                    pass

                # Get group configuration
                try:
                    config_response = rg.get_group_configuration(Group=group_name)
                    config = config_response.get('GroupConfiguration', {})
                    details['configuration_status'] = config.get('Status')
                    config_items = config.get('Configuration', [])
                    details['configuration_types'] = [c.get('Type') for c in config_items]
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = rg.get_tags(Arn=group_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'resource-groups',
                    'type': 'group',
                    'id': group_name,
                    'arn': group_arn,
                    'name': group.get('DisplayName', group_name),
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
