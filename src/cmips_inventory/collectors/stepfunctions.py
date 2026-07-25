"""
Step Functions resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_stepfunctions_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Step Functions resources: state machines, activities.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sfn = session.client('stepfunctions', region_name=region)

    # State Machines
    try:
        paginator = sfn.get_paginator('list_state_machines')
        for page in paginator.paginate():
            for sm in page.get('stateMachines', []):
                sm_arn = sm['stateMachineArn']
                sm_name = sm['name']

                try:
                    # Get details
                    sm_response = sfn.describe_state_machine(stateMachineArn=sm_arn)

                    # Get tags
                    tags = {}
                    try:
                        tag_response = sfn.list_tags_for_resource(resourceArn=sm_arn)
                        for tag in tag_response.get('tags', []):
                            tags[tag.get('key', '')] = tag.get('value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'stepfunctions',
                        'type': 'state-machine',
                        'id': sm_name,
                        'arn': sm_arn,
                        'name': sm_name,
                        'region': region,
                        'details': {
                            'status': sm_response.get('status'),
                            'type': sm_response.get('type'),
                            'role_arn': sm_response.get('roleArn'),
                            'creation_date': str(sm_response.get('creationDate', '')),
                            'logging_configuration': sm_response.get('loggingConfiguration'),
                            'tracing_configuration': sm_response.get('tracingConfiguration'),
                            'revision_id': sm_response.get('revisionId'),
                            'description': sm_response.get('description'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # Activities
    try:
        paginator = sfn.get_paginator('list_activities')
        for page in paginator.paginate():
            for activity in page.get('activities', []):
                activity_arn = activity['activityArn']
                activity_name = activity['name']

                # Get tags
                tags = {}
                try:
                    tag_response = sfn.list_tags_for_resource(resourceArn=activity_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'stepfunctions',
                    'type': 'activity',
                    'id': activity_name,
                    'arn': activity_arn,
                    'name': activity_name,
                    'region': region,
                    'details': {
                        'creation_date': str(activity.get('creationDate', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
