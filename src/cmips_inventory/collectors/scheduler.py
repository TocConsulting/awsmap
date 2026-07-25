"""
Amazon EventBridge Scheduler resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_scheduler_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EventBridge Scheduler resources: schedules and schedule groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    scheduler = session.client('scheduler', region_name=region)

    # Schedule Groups
    try:
        paginator = scheduler.get_paginator('list_schedule_groups')
        for page in paginator.paginate():
            for group in page.get('ScheduleGroups', []):
                group_arn = group.get('Arn', '')
                group_name = group.get('Name', group_arn.split('/')[-1])

                # Skip default group
                if group_name == 'default':
                    continue

                details = {
                    'state': group.get('State'),
                    'creation_date': str(group.get('CreationDate', '')) if group.get('CreationDate') else None,
                }

                resources.append({
                    'service': 'scheduler',
                    'type': 'schedule-group',
                    'id': group_name,
                    'arn': group_arn,
                    'name': group_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Schedules
    try:
        paginator = scheduler.get_paginator('list_schedules')
        for page in paginator.paginate():
            for schedule in page.get('Schedules', []):
                schedule_arn = schedule.get('Arn', '')
                schedule_name = schedule.get('Name', schedule_arn.split('/')[-1])

                details = {
                    'state': schedule.get('State'),
                    'group_name': schedule.get('GroupName'),
                    'schedule_expression': schedule.get('ScheduleExpression'),
                    'creation_date': str(schedule.get('CreationDate', '')) if schedule.get('CreationDate') else None,
                }

                target = schedule.get('Target', {})
                if target:
                    details['target_arn'] = target.get('Arn')

                resources.append({
                    'service': 'scheduler',
                    'type': 'schedule',
                    'id': schedule_name,
                    'arn': schedule_arn,
                    'name': schedule_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
