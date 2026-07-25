"""
AWS Elemental MediaPackage resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_mediapackage_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS MediaPackage resources: channels and origin endpoints.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    mp = session.client('mediapackage', region_name=region)

    # Channels
    try:
        paginator = mp.get_paginator('list_channels')
        for page in paginator.paginate():
            for channel in page.get('Channels', []):
                channel_id = channel['Id']
                channel_arn = channel.get('Arn', '')

                details = {
                    'description': channel.get('Description'),
                    'created_at': channel.get('CreatedAt'),
                    'egress_access_logs': channel.get('EgressAccessLogs', {}).get('LogGroupName'),
                    'ingress_access_logs': channel.get('IngressAccessLogs', {}).get('LogGroupName'),
                }

                hls_ingest = channel.get('HlsIngest', {})
                if hls_ingest:
                    ingest_endpoints = hls_ingest.get('IngestEndpoints', [])
                    details['ingest_endpoint_count'] = len(ingest_endpoints)

                tags = channel.get('Tags', {})

                resources.append({
                    'service': 'mediapackage',
                    'type': 'channel',
                    'id': channel_id,
                    'arn': channel_arn,
                    'name': channel_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Origin Endpoints
    try:
        paginator = mp.get_paginator('list_origin_endpoints')
        for page in paginator.paginate():
            for endpoint in page.get('OriginEndpoints', []):
                endpoint_id = endpoint['Id']
                endpoint_arn = endpoint.get('Arn', '')

                details = {
                    'channel_id': endpoint.get('ChannelId'),
                    'description': endpoint.get('Description'),
                    'url': endpoint.get('Url'),
                    'manifest_name': endpoint.get('ManifestName'),
                    'startover_window_seconds': endpoint.get('StartoverWindowSeconds'),
                    'time_delay_seconds': endpoint.get('TimeDelaySeconds'),
                    'origination': endpoint.get('Origination'),
                    'created_at': endpoint.get('CreatedAt'),
                }

                # Check which packaging format is configured
                if endpoint.get('HlsPackage'):
                    details['packaging_format'] = 'HLS'
                elif endpoint.get('DashPackage'):
                    details['packaging_format'] = 'DASH'
                elif endpoint.get('MssPackage'):
                    details['packaging_format'] = 'MSS'
                elif endpoint.get('CmafPackage'):
                    details['packaging_format'] = 'CMAF'

                tags = endpoint.get('Tags', {})

                resources.append({
                    'service': 'mediapackage',
                    'type': 'origin-endpoint',
                    'id': endpoint_id,
                    'arn': endpoint_arn,
                    'name': endpoint_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
