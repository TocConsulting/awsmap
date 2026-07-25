"""
WorkSpaces resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

# WorkSpaces supported regions
# https://docs.aws.amazon.com/general/latest/gr/wsp.html
WORKSPACES_REGIONS = {
    # US
    'us-east-1', 'us-west-2',
    # Asia Pacific
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    # Canada
    'ca-central-1',
    # Europe
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3',
    # South America
    'sa-east-1',
    # Africa
    'af-south-1',
    # Israel
    'il-central-1',
}


def collect_workspaces_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect WorkSpaces resources: workspaces, directories, bundles, images.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions to avoid timeouts
    if region and region not in WORKSPACES_REGIONS:
        return []

    resources = []
    workspaces = session.client('workspaces', region_name=region)

    # WorkSpaces
    try:
        paginator = workspaces.get_paginator('describe_workspaces')
        for page in paginator.paginate():
            for ws in page.get('Workspaces', []):
                ws_id = ws['WorkspaceId']

                # Get tags
                tags = {}
                try:
                    tag_response = workspaces.describe_tags(ResourceId=ws_id)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'workspaces',
                    'type': 'workspace',
                    'id': ws_id,
                    'arn': f"arn:aws:workspaces:{region}:{account_id}:workspace/{ws_id}",
                    'name': ws.get('ComputerName') or ws.get('UserName') or ws_id,
                    'region': region,
                    'details': {
                        'directory_id': ws.get('DirectoryId'),
                        'user_name': ws.get('UserName'),
                        'ip_address': ws.get('IpAddress'),
                        'state': ws.get('State'),
                        'bundle_id': ws.get('BundleId'),
                        'subnet_id': ws.get('SubnetId'),
                        'computer_name': ws.get('ComputerName'),
                        'volume_encryption_key': ws.get('VolumeEncryptionKey'),
                        'user_volume_encryption_enabled': ws.get('UserVolumeEncryptionEnabled'),
                        'root_volume_encryption_enabled': ws.get('RootVolumeEncryptionEnabled'),
                        'running_mode': ws.get('WorkspaceProperties', {}).get('RunningMode'),
                        'running_mode_auto_stop_timeout': ws.get('WorkspaceProperties', {}).get('RunningModeAutoStopTimeoutInMinutes'),
                        'root_volume_size': ws.get('WorkspaceProperties', {}).get('RootVolumeSizeGib'),
                        'user_volume_size': ws.get('WorkspaceProperties', {}).get('UserVolumeSizeGib'),
                        'compute_type': ws.get('WorkspaceProperties', {}).get('ComputeTypeName'),
                        'protocols': ws.get('WorkspaceProperties', {}).get('Protocols', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # WorkSpaces Directories
    try:
        paginator = workspaces.get_paginator('describe_workspace_directories')
        for page in paginator.paginate():
            for directory in page.get('Directories', []):
                dir_id = directory['DirectoryId']

                # Get tags
                tags = {}
                try:
                    tag_response = workspaces.describe_tags(ResourceId=dir_id)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'workspaces',
                    'type': 'directory',
                    'id': dir_id,
                    'arn': f"arn:aws:workspaces:{region}:{account_id}:directory/{dir_id}",
                    'name': directory.get('DirectoryName') or dir_id,
                    'region': region,
                    'details': {
                        'directory_name': directory.get('DirectoryName'),
                        'directory_type': directory.get('DirectoryType'),
                        'registration_code': directory.get('RegistrationCode'),
                        'state': directory.get('State'),
                        'workspace_creation_properties': directory.get('WorkspaceCreationProperties'),
                        'alias': directory.get('Alias'),
                        'customer_user_name': directory.get('CustomerUserName'),
                        'iam_role_id': directory.get('IamRoleId'),
                        'workspace_security_group_id': directory.get('WorkspaceSecurityGroupId'),
                        'dns_ip_addresses': directory.get('DnsIpAddresses', []),
                        'subnet_ids': directory.get('SubnetIds', []),
                        'ip_group_ids': directory.get('ipGroupIds', []),
                        'tenancy': directory.get('Tenancy'),
                        'selfservice_permissions': directory.get('SelfservicePermissions'),
                        'saml_properties': bool(directory.get('SamlProperties')),
                        'certificate_based_auth_properties': bool(directory.get('CertificateBasedAuthProperties')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Note: Bundles and Images skipped for performance (saves ~82s)
    # They are rarely used custom resources

    return resources
