"""
AWS Application Auto Scaling resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


# Service namespaces supported by Application Auto Scaling
# Limited to most common namespaces for performance (saves ~98s)
# Full list: ecs, elasticmapreduce, ec2, appstream, dynamodb, rds, sagemaker,
#            custom-resource, comprehend, lambda, cassandra, kafka, elasticache, neptune, workspaces
SERVICE_NAMESPACES = [
    'ecs',
    'dynamodb',
    'rds',
    'lambda',
    'ec2',
    'sagemaker',
    'appstream',
]


def collect_applicationautoscaling_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Application Auto Scaling resources: scalable targets and scaling policies.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    autoscaling = session.client('application-autoscaling', region_name=region)

    for namespace in SERVICE_NAMESPACES:
        # Scalable Targets
        try:
            paginator = autoscaling.get_paginator('describe_scalable_targets')
            for page in paginator.paginate(ServiceNamespace=namespace):
                for target in page.get('ScalableTargets', []):
                    resource_id = target.get('ResourceId', '')

                    details = {
                        'service_namespace': target.get('ServiceNamespace'),
                        'scalable_dimension': target.get('ScalableDimension'),
                        'min_capacity': target.get('MinCapacity'),
                        'max_capacity': target.get('MaxCapacity'),
                        'role_arn': target.get('RoleARN'),
                        'creation_time': str(target.get('CreationTime', '')) if target.get('CreationTime') else None,
                        'suspended_state': target.get('SuspendedState'),
                    }

                    resources.append({
                        'service': 'application-autoscaling',
                        'type': 'scalable-target',
                        'id': f"{namespace}/{resource_id}",
                        'arn': target.get('ScalableTargetARN', f"arn:aws:application-autoscaling:{region}:{account_id}:scalable-target/{namespace}/{resource_id}"),
                        'name': resource_id,
                        'region': region,
                        'details': details,
                        'tags': {}
                    })
        except Exception:
            pass

        # Scaling Policies
        try:
            paginator = autoscaling.get_paginator('describe_scaling_policies')
            for page in paginator.paginate(ServiceNamespace=namespace):
                for policy in page.get('ScalingPolicies', []):
                    policy_name = policy.get('PolicyName', '')
                    policy_arn = policy.get('PolicyARN', '')

                    details = {
                        'service_namespace': policy.get('ServiceNamespace'),
                        'resource_id': policy.get('ResourceId'),
                        'scalable_dimension': policy.get('ScalableDimension'),
                        'policy_type': policy.get('PolicyType'),
                        'creation_time': str(policy.get('CreationTime', '')) if policy.get('CreationTime') else None,
                    }

                    resources.append({
                        'service': 'application-autoscaling',
                        'type': 'scaling-policy',
                        'id': policy_name,
                        'arn': policy_arn,
                        'name': policy_name,
                        'region': region,
                        'details': details,
                        'tags': {}
                    })
        except Exception:
            pass

    return resources
