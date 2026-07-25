"""
AWS AppFlow resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_appflow_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS AppFlow resources: flows and connector profiles.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    appflow = session.client('appflow', region_name=region)

    # Flows
    try:
        paginator = appflow.get_paginator('list_flows')
        for page in paginator.paginate():
            for flow in page.get('flows', []):
                flow_name = flow['flowName']
                flow_arn = flow.get('flowArn', f"arn:aws:appflow:{region}:{account_id}:flow/{flow_name}")

                details = {
                    'flow_status': flow.get('flowStatus'),
                    'source_connector_type': flow.get('sourceConnectorType'),
                    'source_connector_label': flow.get('sourceConnectorLabel'),
                    'destination_connector_type': flow.get('destinationConnectorType'),
                    'destination_connector_label': flow.get('destinationConnectorLabel'),
                    'trigger_type': flow.get('triggerType'),
                    'created_at': str(flow.get('createdAt', '')),
                    'last_updated_at': str(flow.get('lastUpdatedAt', '')),
                    'created_by': flow.get('createdBy'),
                    'last_updated_by': flow.get('lastUpdatedBy'),
                    'description': flow.get('description'),
                }

                last_run = flow.get('lastRunExecutionDetails', {})
                if last_run:
                    details['last_run_status'] = last_run.get('mostRecentExecutionStatus')
                    details['last_run_time'] = str(last_run.get('mostRecentExecutionTime', ''))

                tags = flow.get('tags', {})

                resources.append({
                    'service': 'appflow',
                    'type': 'flow',
                    'id': flow_name,
                    'arn': flow_arn,
                    'name': flow_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Connector Profiles
    try:
        paginator = appflow.get_paginator('describe_connector_profiles')
        for page in paginator.paginate():
            for profile in page.get('connectorProfileDetails', []):
                profile_name = profile['connectorProfileName']
                profile_arn = profile.get('connectorProfileArn', f"arn:aws:appflow:{region}:{account_id}:connectorprofile/{profile_name}")

                details = {
                    'connector_type': profile.get('connectorType'),
                    'connector_label': profile.get('connectorLabel'),
                    'connection_mode': profile.get('connectionMode'),
                    'credentials_arn': profile.get('credentialsArn'),
                    'created_at': str(profile.get('createdAt', '')),
                    'last_updated_at': str(profile.get('lastUpdatedAt', '')),
                    'private_connection_provisioning_state': profile.get('privateConnectionProvisioningState', {}).get('status'),
                }

                resources.append({
                    'service': 'appflow',
                    'type': 'connector-profile',
                    'id': profile_name,
                    'arn': profile_arn,
                    'name': profile_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
