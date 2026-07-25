"""
AWS Storage Gateway resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_storagegateway_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Storage Gateway resources: gateways, volumes, file shares, and tapes.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sgw = session.client('storagegateway', region_name=region)

    # Gateways
    try:
        paginator = sgw.get_paginator('list_gateways')
        for page in paginator.paginate():
            for gateway in page.get('Gateways', []):
                gateway_arn = gateway['GatewayARN']
                gateway_id = gateway.get('GatewayId', gateway_arn.split('/')[-1])
                gateway_name = gateway.get('GatewayName', gateway_id)

                details = {
                    'gateway_type': gateway.get('GatewayType'),
                    'gateway_operational_state': gateway.get('GatewayOperationalState'),
                    'ec2_instance_id': gateway.get('Ec2InstanceId'),
                    'ec2_instance_region': gateway.get('Ec2InstanceRegion'),
                    'host_environment': gateway.get('HostEnvironment'),
                    'host_environment_id': gateway.get('HostEnvironmentId'),
                    'deprecation_date': gateway.get('DeprecationDate'),
                    'software_version': gateway.get('SoftwareVersion'),
                }

                # Get detailed gateway info
                try:
                    gw_info = sgw.describe_gateway_information(GatewayARN=gateway_arn)
                    details['gateway_timezone'] = gw_info.get('GatewayTimezone')
                    details['gateway_state'] = gw_info.get('GatewayState')
                    details['gateway_network_interfaces'] = len(gw_info.get('GatewayNetworkInterfaces', []))
                    details['cloud_watch_log_group_arn'] = gw_info.get('CloudWatchLogGroupARN')
                    details['endpoint_type'] = gw_info.get('EndpointType')
                    details['software_updates_end_date'] = gw_info.get('SoftwareUpdatesEndDate')

                    tags = {t['Key']: t['Value'] for t in gw_info.get('Tags', [])}
                except Exception:
                    tags = {}

                resources.append({
                    'service': 'storagegateway',
                    'type': 'gateway',
                    'id': gateway_id,
                    'arn': gateway_arn,
                    'name': gateway_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Volumes
    try:
        paginator = sgw.get_paginator('list_volumes')
        for page in paginator.paginate():
            for volume in page.get('VolumeInfos', []):
                volume_arn = volume['VolumeARN']
                volume_id = volume.get('VolumeId', volume_arn.split('/')[-1])

                details = {
                    'gateway_arn': volume.get('GatewayARN'),
                    'gateway_id': volume.get('GatewayId'),
                    'volume_type': volume.get('VolumeType'),
                    'volume_size_in_bytes': volume.get('VolumeSizeInBytes'),
                    'volume_attachment_status': volume.get('VolumeAttachmentStatus'),
                }

                resources.append({
                    'service': 'storagegateway',
                    'type': 'volume',
                    'id': volume_id,
                    'arn': volume_arn,
                    'name': volume_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # File Shares
    try:
        paginator = sgw.get_paginator('list_file_shares')
        for page in paginator.paginate():
            for share in page.get('FileShareInfoList', []):
                share_arn = share['FileShareARN']
                share_id = share.get('FileShareId', share_arn.split('/')[-1])

                details = {
                    'file_share_type': share.get('FileShareType'),
                    'file_share_status': share.get('FileShareStatus'),
                    'gateway_arn': share.get('GatewayARN'),
                }

                resources.append({
                    'service': 'storagegateway',
                    'type': 'file-share',
                    'id': share_id,
                    'arn': share_arn,
                    'name': share_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Tapes
    try:
        paginator = sgw.get_paginator('list_tapes')
        for page in paginator.paginate():
            for tape in page.get('TapeInfos', []):
                tape_arn = tape['TapeARN']
                tape_barcode = tape.get('TapeBarcode', tape_arn.split('/')[-1])

                details = {
                    'tape_barcode': tape_barcode,
                    'tape_size_in_bytes': tape.get('TapeSizeInBytes'),
                    'tape_status': tape.get('TapeStatus'),
                    'gateway_arn': tape.get('GatewayARN'),
                    'pool_id': tape.get('PoolId'),
                    'retention_start_date': str(tape.get('RetentionStartDate', '')),
                    'pool_entry_date': str(tape.get('PoolEntryDate', '')),
                }

                resources.append({
                    'service': 'storagegateway',
                    'type': 'tape',
                    'id': tape_barcode,
                    'arn': tape_arn,
                    'name': tape_barcode,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
