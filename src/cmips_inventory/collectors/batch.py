"""
AWS Batch resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_batch_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Batch resources: compute environments, job queues, job definitions, scheduling policies.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    batch = session.client('batch', region_name=region)

    # Compute Environments
    try:
        paginator = batch.get_paginator('describe_compute_environments')
        for page in paginator.paginate():
            for ce in page.get('computeEnvironments', []):
                ce_name = ce['computeEnvironmentName']
                ce_arn = ce['computeEnvironmentArn']

                # Get tags
                tags = ce.get('tags', {})

                resources.append({
                    'service': 'batch',
                    'type': 'compute-environment',
                    'id': ce_name,
                    'arn': ce_arn,
                    'name': ce_name,
                    'region': region,
                    'details': {
                        'state': ce.get('state'),
                        'status': ce.get('status'),
                        'status_reason': ce.get('statusReason'),
                        'type': ce.get('type'),
                        'compute_resources': {
                            'type': ce.get('computeResources', {}).get('type'),
                            'allocation_strategy': ce.get('computeResources', {}).get('allocationStrategy'),
                            'min_vcpus': ce.get('computeResources', {}).get('minvCpus'),
                            'max_vcpus': ce.get('computeResources', {}).get('maxvCpus'),
                            'desired_vcpus': ce.get('computeResources', {}).get('desiredvCpus'),
                            'instance_types': ce.get('computeResources', {}).get('instanceTypes', []),
                        },
                        'service_role': ce.get('serviceRole'),
                        'update_policy': ce.get('updatePolicy'),
                        'eks_configuration': ce.get('eksConfiguration'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Job Queues
    try:
        paginator = batch.get_paginator('describe_job_queues')
        for page in paginator.paginate():
            for jq in page.get('jobQueues', []):
                jq_name = jq['jobQueueName']
                jq_arn = jq['jobQueueArn']

                # Get tags
                tags = jq.get('tags', {})

                resources.append({
                    'service': 'batch',
                    'type': 'job-queue',
                    'id': jq_name,
                    'arn': jq_arn,
                    'name': jq_name,
                    'region': region,
                    'details': {
                        'state': jq.get('state'),
                        'status': jq.get('status'),
                        'status_reason': jq.get('statusReason'),
                        'priority': jq.get('priority'),
                        'scheduling_policy_arn': jq.get('schedulingPolicyArn'),
                        'compute_environment_order': [
                            {
                                'order': ceo.get('order'),
                                'compute_environment': ceo.get('computeEnvironment'),
                            }
                            for ceo in jq.get('computeEnvironmentOrder', [])
                        ],
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Job Definitions (active only, latest revision)
    try:
        paginator = batch.get_paginator('describe_job_definitions')
        for page in paginator.paginate(status='ACTIVE'):
            for jd in page.get('jobDefinitions', []):
                jd_name = jd['jobDefinitionName']
                jd_arn = jd['jobDefinitionArn']

                # Get tags
                tags = jd.get('tags', {})

                resources.append({
                    'service': 'batch',
                    'type': 'job-definition',
                    'id': f"{jd_name}:{jd.get('revision')}",
                    'arn': jd_arn,
                    'name': jd_name,
                    'region': region,
                    'details': {
                        'revision': jd.get('revision'),
                        'status': jd.get('status'),
                        'type': jd.get('type'),
                        'scheduling_priority': jd.get('schedulingPriority'),
                        'platform_capabilities': jd.get('platformCapabilities', []),
                        'propagate_tags': jd.get('propagateTags'),
                        'timeout': jd.get('timeout'),
                        'retry_strategy': jd.get('retryStrategy'),
                        'container_orchestration_type': jd.get('containerOrchestrationType'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Scheduling Policies
    try:
        paginator = batch.get_paginator('list_scheduling_policies')
        for page in paginator.paginate():
            sp_arns = [sp['arn'] for sp in page.get('schedulingPolicies', [])]

            if sp_arns:
                # Describe scheduling policies
                desc_response = batch.describe_scheduling_policies(arns=sp_arns)
                for sp in desc_response.get('schedulingPolicies', []):
                    sp_name = sp['name']
                    sp_arn = sp['arn']

                    tags = sp.get('tags', {})

                    resources.append({
                        'service': 'batch',
                        'type': 'scheduling-policy',
                        'id': sp_name,
                        'arn': sp_arn,
                        'name': sp_name,
                        'region': region,
                        'details': {
                            'fairshare_policy': sp.get('fairsharePolicy'),
                        },
                        'tags': tags
                    })
    except Exception:
        pass

    return resources
