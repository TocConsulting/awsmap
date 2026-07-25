"""
AWS Device Farm resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Device Farm supported regions (from https://docs.aws.amazon.com/general/latest/gr/devicefarm.html)
DEVICEFARM_REGIONS = {
    'us-west-2',
}


def collect_devicefarm_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Device Farm resources: projects, device pools, and test grid projects.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in DEVICEFARM_REGIONS:
        return []

    resources = []
    devicefarm = session.client('devicefarm', region_name=region)

    # Projects
    try:
        paginator = devicefarm.get_paginator('list_projects')
        for page in paginator.paginate():
            for project in page.get('projects', []):
                project_arn = project['arn']
                project_name = project.get('name', project_arn.split('/')[-1])

                details = {}

                resources.append({
                    'service': 'devicefarm',
                    'type': 'project',
                    'id': project_arn.split(':')[-1],
                    'arn': project_arn,
                    'name': project_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Test Grid Projects
    try:
        paginator = devicefarm.get_paginator('list_test_grid_projects')
        for page in paginator.paginate():
            for project in page.get('testGridProjects', []):
                project_arn = project['arn']
                project_name = project.get('name', project_arn.split('/')[-1])

                details = {
                    'description': project.get('description'),
                }

                resources.append({
                    'service': 'devicefarm',
                    'type': 'test-grid-project',
                    'id': project_arn.split(':')[-1],
                    'arn': project_arn,
                    'name': project_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # VPCE Configurations
    try:
        paginator = devicefarm.get_paginator('list_vpce_configurations')
        for page in paginator.paginate():
            for vpce in page.get('vpceConfigurations', []):
                vpce_arn = vpce['arn']
                vpce_name = vpce.get('vpceConfigurationName', vpce_arn.split('/')[-1])

                details = {
                    'vpce_service_name': vpce.get('vpceServiceName'),
                    'service_dns_name': vpce.get('serviceDnsName'),
                }

                resources.append({
                    'service': 'devicefarm',
                    'type': 'vpce-configuration',
                    'id': vpce_arn.split(':')[-1],
                    'arn': vpce_arn,
                    'name': vpce_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
