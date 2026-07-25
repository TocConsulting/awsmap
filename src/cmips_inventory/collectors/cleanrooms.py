"""
AWS Clean Rooms resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


# Clean Rooms supported regions
CLEANROOMS_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-north-1',
}


def collect_cleanrooms_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Clean Rooms resources: collaborations, memberships, configured tables.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in CLEANROOMS_REGIONS:
        return []

    resources = []
    cleanrooms = session.client('cleanrooms', region_name=region)

    # Collaborations
    try:
        paginator = cleanrooms.get_paginator('list_collaborations')
        for page in paginator.paginate():
            for collab in page.get('collaborationList', []):
                collab_id = collab.get('id', '')
                collab_arn = collab.get('arn', '')
                collab_name = collab.get('name', collab_id)

                details = {
                    'creator_account_id': collab.get('creatorAccountId'),
                    'creator_display_name': collab.get('creatorDisplayName'),
                    'member_status': collab.get('memberStatus'),
                    'membership_id': collab.get('membershipId'),
                    'create_time': str(collab.get('createTime', '')) if collab.get('createTime') else None,
                    'update_time': str(collab.get('updateTime', '')) if collab.get('updateTime') else None,
                }

                resources.append({
                    'service': 'cleanrooms',
                    'type': 'collaboration',
                    'id': collab_id,
                    'arn': collab_arn,
                    'name': collab_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Memberships
    try:
        paginator = cleanrooms.get_paginator('list_memberships')
        for page in paginator.paginate():
            for membership in page.get('membershipSummaries', []):
                membership_id = membership.get('id', '')
                membership_arn = membership.get('arn', '')

                details = {
                    'collaboration_id': membership.get('collaborationId'),
                    'collaboration_arn': membership.get('collaborationArn'),
                    'collaboration_name': membership.get('collaborationName'),
                    'status': membership.get('status'),
                    'member_abilities': membership.get('memberAbilities'),
                    'create_time': str(membership.get('createTime', '')) if membership.get('createTime') else None,
                    'update_time': str(membership.get('updateTime', '')) if membership.get('updateTime') else None,
                }

                resources.append({
                    'service': 'cleanrooms',
                    'type': 'membership',
                    'id': membership_id,
                    'arn': membership_arn,
                    'name': membership.get('collaborationName', membership_id),
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Configured Tables
    try:
        paginator = cleanrooms.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            for table in page.get('configuredTableSummaries', []):
                table_id = table.get('id', '')
                table_arn = table.get('arn', '')
                table_name = table.get('name', table_id)

                details = {
                    'analysis_method': table.get('analysisMethod'),
                    'analysis_rule_types': table.get('analysisRuleTypes'),
                    'create_time': str(table.get('createTime', '')) if table.get('createTime') else None,
                    'update_time': str(table.get('updateTime', '')) if table.get('updateTime') else None,
                }

                resources.append({
                    'service': 'cleanrooms',
                    'type': 'configured-table',
                    'id': table_id,
                    'arn': table_arn,
                    'name': table_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
