"""
AWS Fault Injection Simulator (FIS) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_fis_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS FIS resources: experiment templates and experiments.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    fis = session.client('fis', region_name=region)

    # Experiment Templates
    try:
        paginator = fis.get_paginator('list_experiment_templates')
        for page in paginator.paginate():
            for template in page.get('experimentTemplates', []):
                template_id = template['id']
                template_arn = template.get('arn', f"arn:aws:fis:{region}:{account_id}:experiment-template/{template_id}")

                details = {
                    'description': template.get('description'),
                }

                tags = template.get('tags', {})

                resources.append({
                    'service': 'fis',
                    'type': 'experiment-template',
                    'id': template_id,
                    'arn': template_arn,
                    'name': template.get('description', template_id),
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Experiments (running or completed)
    try:
        paginator = fis.get_paginator('list_experiments')
        for page in paginator.paginate():
            for experiment in page.get('experiments', []):
                experiment_id = experiment['id']
                experiment_arn = experiment.get('arn', f"arn:aws:fis:{region}:{account_id}:experiment/{experiment_id}")

                state = experiment.get('state', {})
                details = {
                    'experiment_template_id': experiment.get('experimentTemplateId'),
                    'state': state.get('status'),
                    'state_reason': state.get('reason'),
                }

                tags = experiment.get('tags', {})

                resources.append({
                    'service': 'fis',
                    'type': 'experiment',
                    'id': experiment_id,
                    'arn': experiment_arn,
                    'name': experiment_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
