"""
AWS Resilience Hub resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_resiliencehub_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Resilience Hub resources: apps and resiliency policies.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    resiliencehub = session.client('resiliencehub', region_name=region)

    # Apps
    try:
        paginator = resiliencehub.get_paginator('list_apps')
        for page in paginator.paginate():
            for app in page.get('appSummaries', []):
                app_arn = app['appArn']
                app_name = app.get('name', app_arn.split('/')[-1])

                details = {
                    'description': app.get('description'),
                    'status': app.get('status'),
                    'compliance_status': app.get('complianceStatus'),
                    'resiliency_score': app.get('resiliencyScore'),
                    'assessment_schedule': app.get('assessmentSchedule'),
                }

                resources.append({
                    'service': 'resiliencehub',
                    'type': 'app',
                    'id': app_arn.split('/')[-1],
                    'arn': app_arn,
                    'name': app_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Resiliency Policies
    try:
        paginator = resiliencehub.get_paginator('list_resiliency_policies')
        for page in paginator.paginate():
            for policy in page.get('resiliencyPolicies', []):
                policy_arn = policy['policyArn']
                policy_name = policy.get('policyName', policy_arn.split('/')[-1])

                details = {
                    'description': policy.get('policyDescription'),
                    'tier': policy.get('tier'),
                    'data_location_constraint': policy.get('dataLocationConstraint'),
                }

                resources.append({
                    'service': 'resiliencehub',
                    'type': 'resiliency-policy',
                    'id': policy_arn.split('/')[-1],
                    'arn': policy_arn,
                    'name': policy_name,
                    'region': region,
                    'details': details,
                    'tags': policy.get('tags', {})
                })
    except Exception:
        pass

    return resources
