"""
AWS IoT SiteWise resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# IoT SiteWise supported regions (from https://docs.aws.amazon.com/general/latest/gr/iot-sitewise.html)
IOTSITEWISE_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1',
}


def collect_iotsitewise_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS IoT SiteWise resources: asset models, assets, gateways, and portals.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in IOTSITEWISE_REGIONS:
        return []

    resources = []
    sitewise = session.client('iotsitewise', region_name=region)

    # Asset Models
    try:
        paginator = sitewise.get_paginator('list_asset_models')
        for page in paginator.paginate():
            for model in page.get('assetModelSummaries', []):
                model_id = model['id']
                model_arn = model.get('arn', f"arn:aws:iotsitewise:{region}:{account_id}:asset-model/{model_id}")
                model_name = model.get('name', model_id)

                status = model.get('status', {})
                details = {
                    'description': model.get('description'),
                    'asset_model_type': model.get('assetModelType'),
                    'status': status.get('state'),
                    'version': model.get('version'),
                }

                resources.append({
                    'service': 'iotsitewise',
                    'type': 'asset-model',
                    'id': model_id,
                    'arn': model_arn,
                    'name': model_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Assets
    try:
        paginator = sitewise.get_paginator('list_assets')
        for page in paginator.paginate():
            for asset in page.get('assetSummaries', []):
                asset_id = asset['id']
                asset_arn = asset.get('arn', f"arn:aws:iotsitewise:{region}:{account_id}:asset/{asset_id}")
                asset_name = asset.get('name', asset_id)

                status = asset.get('status', {})
                details = {
                    'description': asset.get('description'),
                    'asset_model_id': asset.get('assetModelId'),
                    'status': status.get('state'),
                }

                resources.append({
                    'service': 'iotsitewise',
                    'type': 'asset',
                    'id': asset_id,
                    'arn': asset_arn,
                    'name': asset_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Gateways
    try:
        paginator = sitewise.get_paginator('list_gateways')
        for page in paginator.paginate():
            for gateway in page.get('gatewaySummaries', []):
                gateway_id = gateway['gatewayId']
                gateway_arn = f"arn:aws:iotsitewise:{region}:{account_id}:gateway/{gateway_id}"
                gateway_name = gateway.get('gatewayName', gateway_id)

                platform = gateway.get('gatewayPlatform', {})
                platform_type = None
                if 'greengrass' in platform:
                    platform_type = 'greengrass'
                elif 'greengrassV2' in platform:
                    platform_type = 'greengrassV2'
                elif 'siemensIE' in platform:
                    platform_type = 'siemensIE'

                details = {
                    'gateway_version': gateway.get('gatewayVersion'),
                    'platform_type': platform_type,
                }

                resources.append({
                    'service': 'iotsitewise',
                    'type': 'gateway',
                    'id': gateway_id,
                    'arn': gateway_arn,
                    'name': gateway_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Portals
    try:
        paginator = sitewise.get_paginator('list_portals')
        for page in paginator.paginate():
            for portal in page.get('portalSummaries', []):
                portal_id = portal['id']
                portal_arn = f"arn:aws:iotsitewise:{region}:{account_id}:portal/{portal_id}"
                portal_name = portal.get('name', portal_id)

                status = portal.get('status', {})
                details = {
                    'description': portal.get('description'),
                    'start_url': portal.get('startUrl'),
                    'portal_type': portal.get('portalType'),
                    'status': status.get('state'),
                    'role_arn': portal.get('roleArn'),
                }

                resources.append({
                    'service': 'iotsitewise',
                    'type': 'portal',
                    'id': portal_id,
                    'arn': portal_arn,
                    'name': portal_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
