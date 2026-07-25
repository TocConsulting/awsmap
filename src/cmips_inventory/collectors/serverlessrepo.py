"""
AWS Serverless Application Repository resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Serverless Application Repository supported regions (from https://docs.aws.amazon.com/general/latest/gr/serverlessrepo.html)
SERVERLESSREPO_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-east-1', 'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1',
    'me-south-1',
    'sa-east-1',
}


def collect_serverlessrepo_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Serverless Application Repository resources: applications.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in SERVERLESSREPO_REGIONS:
        return []

    resources = []
    sar = session.client('serverlessrepo', region_name=region)

    # Applications
    try:
        paginator = sar.get_paginator('list_applications')
        for page in paginator.paginate():
            for app in page.get('Applications', []):
                # ApplicationId is actually the ARN
                app_arn = app['ApplicationId']
                app_name = app.get('Name', app_arn.split('/')[-1])
                # Extract just the ID from the ARN
                app_id = app_arn.split('/')[-1] if '/' in app_arn else app_arn

                details = {
                    'author': app.get('Author'),
                    'description': app.get('Description'),
                    'home_page_url': app.get('HomePageUrl'),
                    'labels': app.get('Labels', []),
                    'spdx_license_id': app.get('SpdxLicenseId'),
                }

                resources.append({
                    'service': 'serverlessrepo',
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
