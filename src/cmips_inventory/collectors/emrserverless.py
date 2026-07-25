"""
Amazon EMR Serverless resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_emrserverless_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EMR Serverless resources: applications.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    emr_serverless = session.client('emr-serverless', region_name=region)

    # Applications
    try:
        paginator = emr_serverless.get_paginator('list_applications')
        for page in paginator.paginate():
            for app in page.get('applications', []):
                app_id = app.get('id', '')
                app_arn = app.get('arn', '')
                app_name = app.get('name', app_id)

                details = {
                    'state': app.get('state'),
                    'state_details': app.get('stateDetails'),
                    'type': app.get('type'),
                    'release_label': app.get('releaseLabel'),
                    'architecture': app.get('architecture'),
                    'created_at': str(app.get('createdAt', '')) if app.get('createdAt') else None,
                    'updated_at': str(app.get('updatedAt', '')) if app.get('updatedAt') else None,
                }

                resources.append({
                    'service': 'emr-serverless',
                    'type': 'application',
                    'id': app_id,
                    'arn': app_arn,
                    'name': app_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
