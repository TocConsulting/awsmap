"""
AWS Elemental MediaConnect resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_mediaconnect_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Elemental MediaConnect resources: flows, bridges, gateways.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    mediaconnect = session.client('mediaconnect', region_name=region)

    # Flows
    try:
        paginator = mediaconnect.get_paginator('list_flows')
        for page in paginator.paginate():
            for flow in page.get('Flows', []):
                flow_arn = flow.get('FlowArn', '')
                flow_name = flow.get('Name', flow_arn.split('/')[-1])

                details = {
                    'status': flow.get('Status'),
                    'availability_zone': flow.get('AvailabilityZone'),
                    'description': flow.get('Description'),
                    'source_type': flow.get('SourceType'),
                }

                resources.append({
                    'service': 'mediaconnect',
                    'type': 'flow',
                    'id': flow_name,
                    'arn': flow_arn,
                    'name': flow_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Gateways
    try:
        paginator = mediaconnect.get_paginator('list_gateways')
        for page in paginator.paginate():
            for gateway in page.get('Gateways', []):
                gateway_arn = gateway.get('GatewayArn', '')
                gateway_name = gateway.get('Name', gateway_arn.split('/')[-1])

                details = {
                    'gateway_state': gateway.get('GatewayState'),
                }

                resources.append({
                    'service': 'mediaconnect',
                    'type': 'gateway',
                    'id': gateway_name,
                    'arn': gateway_arn,
                    'name': gateway_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Bridges
    try:
        paginator = mediaconnect.get_paginator('list_bridges')
        for page in paginator.paginate():
            for bridge in page.get('Bridges', []):
                bridge_arn = bridge.get('BridgeArn', '')
                bridge_name = bridge.get('Name', bridge_arn.split('/')[-1])

                details = {
                    'bridge_state': bridge.get('BridgeState'),
                    'bridge_type': bridge.get('BridgeType'),
                    'placement_arn': bridge.get('PlacementArn'),
                }

                resources.append({
                    'service': 'mediaconnect',
                    'type': 'bridge',
                    'id': bridge_name,
                    'arn': bridge_arn,
                    'name': bridge_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
