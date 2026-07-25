"""
AWS Elemental MediaConvert resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_mediaconvert_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS MediaConvert resources: queues, job templates, and presets.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []

    # First get the endpoint for this region
    try:
        mc_endpoints = session.client('mediaconvert', region_name=region)
        endpoints_response = mc_endpoints.describe_endpoints()
        endpoints = endpoints_response.get('Endpoints', [])
        if not endpoints:
            return resources
        endpoint_url = endpoints[0].get('Url')
        if not endpoint_url:
            return resources
    except Exception:
        return resources

    # Create client with the account-specific endpoint
    mc = session.client('mediaconvert', region_name=region, endpoint_url=endpoint_url)

    # Queues (skip AWS default queue that exists in every region)
    try:
        paginator = mc.get_paginator('list_queues')
        for page in paginator.paginate():
            for queue in page.get('Queues', []):
                queue_name = queue['Name']

                # Skip the AWS default queue
                if queue_name == 'Default':
                    continue

                queue_arn = queue.get('Arn', '')

                details = {
                    'status': queue.get('Status'),
                    'type': queue.get('Type'),
                    'pricing_plan': queue.get('PricingPlan'),
                    'submitted_jobs_count': queue.get('SubmittedJobsCount'),
                    'progressing_jobs_count': queue.get('ProgressingJobsCount'),
                    'created_at': str(queue.get('CreatedAt', '')),
                    'last_updated': str(queue.get('LastUpdated', '')),
                    'description': queue.get('Description'),
                }

                resources.append({
                    'service': 'mediaconvert',
                    'type': 'queue',
                    'id': queue_name,
                    'arn': queue_arn,
                    'name': queue_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Job Templates
    try:
        paginator = mc.get_paginator('list_job_templates')
        for page in paginator.paginate():
            for template in page.get('JobTemplates', []):
                template_name = template['Name']
                template_arn = template.get('Arn', '')

                details = {
                    'type': template.get('Type'),
                    'category': template.get('Category'),
                    'description': template.get('Description'),
                    'created_at': str(template.get('CreatedAt', '')),
                    'last_updated': str(template.get('LastUpdated', '')),
                }

                resources.append({
                    'service': 'mediaconvert',
                    'type': 'job-template',
                    'id': template_name,
                    'arn': template_arn,
                    'name': template_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Presets
    try:
        paginator = mc.get_paginator('list_presets')
        for page in paginator.paginate():
            for preset in page.get('Presets', []):
                preset_name = preset['Name']
                preset_arn = preset.get('Arn', '')

                details = {
                    'type': preset.get('Type'),
                    'category': preset.get('Category'),
                    'description': preset.get('Description'),
                    'created_at': str(preset.get('CreatedAt', '')),
                    'last_updated': str(preset.get('LastUpdated', '')),
                }

                resources.append({
                    'service': 'mediaconvert',
                    'type': 'preset',
                    'id': preset_name,
                    'arn': preset_arn,
                    'name': preset_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
