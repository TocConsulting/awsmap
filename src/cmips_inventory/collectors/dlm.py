"""
AWS Data Lifecycle Manager (DLM) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_dlm_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Data Lifecycle Manager resources: lifecycle policies.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    dlm = session.client('dlm', region_name=region)

    # Lifecycle Policies
    try:
        response = dlm.get_lifecycle_policies()
        for policy_summary in response.get('Policies', []):
            policy_id = policy_summary['PolicyId']

            details = {
                'description': policy_summary.get('Description'),
                'state': policy_summary.get('State'),
                'policy_type': policy_summary.get('PolicyType'),
                'resource_types': policy_summary.get('ResourceTypes', []),
                'default_policy': policy_summary.get('DefaultPolicy'),
            }

            # Get full policy details
            try:
                policy_detail = dlm.get_lifecycle_policy(PolicyId=policy_id)
                policy = policy_detail.get('Policy', {})

                details['execution_role_arn'] = policy.get('ExecutionRoleArn')
                details['date_created'] = str(policy.get('DateCreated', ''))
                details['date_modified'] = str(policy.get('DateModified', ''))
                details['status_message'] = policy.get('StatusMessage')

                # Policy details
                policy_details = policy.get('PolicyDetails', {})
                details['target_tags'] = policy_details.get('TargetTags', [])
                details['schedules_count'] = len(policy_details.get('Schedules', []))
                details['resource_locations'] = policy_details.get('ResourceLocations', [])

                # Get schedule names
                schedules = policy_details.get('Schedules', [])
                details['schedule_names'] = [s.get('Name') for s in schedules]

                tags = policy.get('Tags', {})
            except Exception:
                tags = {}

            resources.append({
                'service': 'dlm',
                'type': 'lifecycle-policy',
                'id': policy_id,
                'arn': f"arn:aws:dlm:{region}:{account_id}:policy/{policy_id}",
                'name': policy_summary.get('Description', policy_id),
                'region': region,
                'details': details,
                'tags': tags
            })
    except Exception:
        pass

    return resources
