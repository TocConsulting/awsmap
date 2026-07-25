"""
Amazon Managed Prometheus resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_amp_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Amazon Managed Prometheus resources: workspaces, rule groups, alert managers.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    amp = session.client('amp', region_name=region)

    # Prometheus Workspaces
    try:
        paginator = amp.get_paginator('list_workspaces')
        for page in paginator.paginate():
            for workspace in page.get('workspaces', []):
                ws_id = workspace['workspaceId']
                ws_arn = workspace['arn']

                try:
                    # Get workspace details
                    ws_response = amp.describe_workspace(workspaceId=ws_id)
                    ws_detail = ws_response.get('workspace', {})

                    # Get tags
                    tags = ws_detail.get('tags', {})

                    resources.append({
                        'service': 'amp',
                        'type': 'workspace',
                        'id': ws_id,
                        'arn': ws_arn,
                        'name': ws_detail.get('alias') or ws_id,
                        'region': region,
                        'details': {
                            'status': ws_detail.get('status', {}).get('statusCode'),
                            'alias': ws_detail.get('alias'),
                            'prometheus_endpoint': ws_detail.get('prometheusEndpoint'),
                            'created_at': str(ws_detail.get('createdAt', '')),
                            'kms_key_arn': ws_detail.get('kmsKeyArn'),
                        },
                        'tags': tags
                    })

                    # Rule Groups Namespace for this workspace
                    try:
                        rg_paginator = amp.get_paginator('list_rule_groups_namespaces')
                        for rg_page in rg_paginator.paginate(workspaceId=ws_id):
                            for rg in rg_page.get('ruleGroupsNamespaces', []):
                                rg_name = rg['name']
                                rg_arn = rg['arn']

                                rg_tags = rg.get('tags', {})

                                resources.append({
                                    'service': 'amp',
                                    'type': 'rule-groups-namespace',
                                    'id': f"{ws_id}/{rg_name}",
                                    'arn': rg_arn,
                                    'name': rg_name,
                                    'region': region,
                                    'details': {
                                        'workspace_id': ws_id,
                                        'status': rg.get('status', {}).get('statusCode'),
                                        'created_at': str(rg.get('createdAt', '')),
                                        'modified_at': str(rg.get('modifiedAt', '')),
                                    },
                                    'tags': rg_tags
                                })
                    except Exception:
                        pass

                    # Alert Manager Definition for this workspace
                    try:
                        am_response = amp.describe_alert_manager_definition(workspaceId=ws_id)
                        am_detail = am_response.get('alertManagerDefinition', {})

                        if am_detail:
                            resources.append({
                                'service': 'amp',
                                'type': 'alert-manager',
                                'id': f"{ws_id}/alertmanager",
                                'arn': f"{ws_arn}/alertmanager",
                                'name': f"alertmanager-{ws_id[:8]}",
                                'region': region,
                                'details': {
                                    'workspace_id': ws_id,
                                    'status': am_detail.get('status', {}).get('statusCode'),
                                    'created_at': str(am_detail.get('createdAt', '')),
                                    'modified_at': str(am_detail.get('modifiedAt', '')),
                                },
                                'tags': {}
                            })
                    except amp.exceptions.ResourceNotFoundException:
                        pass
                    except Exception:
                        pass

                except Exception:
                    pass
    except Exception:
        pass

    return resources
