"""
Amazon Managed Grafana resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

# Amazon Managed Grafana supported regions
# https://docs.aws.amazon.com/grafana/latest/userguide/what-is-Amazon-Managed-Service-Grafana.html
GRAFANA_REGIONS = {
    # US
    'us-east-1', 'us-east-2', 'us-west-2',
    # Asia Pacific
    'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    # Europe
    'eu-central-1', 'eu-west-1', 'eu-west-2',
}


def collect_grafana_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Amazon Managed Grafana resources: workspaces.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions to avoid timeouts
    if region and region not in GRAFANA_REGIONS:
        return []

    resources = []
    grafana = session.client('grafana', region_name=region)

    # Grafana Workspaces
    try:
        paginator = grafana.get_paginator('list_workspaces')
        for page in paginator.paginate():
            for workspace in page.get('workspaces', []):
                ws_id = workspace['id']
                ws_name = workspace.get('name', ws_id)

                try:
                    # Get workspace details
                    ws_response = grafana.describe_workspace(workspaceId=ws_id)
                    ws_detail = ws_response.get('workspace', {})

                    # Get tags
                    tags = ws_detail.get('tags', {})

                    resources.append({
                        'service': 'grafana',
                        'type': 'workspace',
                        'id': ws_id,
                        'arn': ws_detail.get('arn', f"arn:aws:grafana:{region}:{account_id}:/workspaces/{ws_id}"),
                        'name': ws_name,
                        'region': region,
                        'details': {
                            'status': ws_detail.get('status'),
                            'description': ws_detail.get('description'),
                            'endpoint': ws_detail.get('endpoint'),
                            'grafana_version': ws_detail.get('grafanaVersion'),
                            'account_access_type': ws_detail.get('accountAccessType'),
                            'authentication_providers': ws_detail.get('authentication', {}).get('providers', []),
                            'permission_type': ws_detail.get('permissionType'),
                            'license_type': ws_detail.get('licenseType'),
                            'stack_set_name': ws_detail.get('stackSetName'),
                            'data_sources': ws_detail.get('dataSources', []),
                            'notification_destinations': ws_detail.get('notificationDestinations', []),
                            'created': str(ws_detail.get('created', '')),
                            'modified': str(ws_detail.get('modified', '')),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
