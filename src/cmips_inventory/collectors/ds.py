"""
Directory Service resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_ds_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Directory Service resources: directories.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ds = session.client('ds', region_name=region)

    # Directories
    try:
        paginator = ds.get_paginator('describe_directories')
        for page in paginator.paginate():
            for directory in page.get('DirectoryDescriptions', []):
                dir_id = directory['DirectoryId']

                # Get tags
                tags = {}
                try:
                    tag_response = ds.list_tags_for_resource(ResourceId=dir_id)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'ds',
                    'type': 'directory',
                    'id': dir_id,
                    'arn': f"arn:aws:ds:{region}:{account_id}:directory/{dir_id}",
                    'name': directory.get('Name', dir_id),
                    'region': region,
                    'details': {
                        'short_name': directory.get('ShortName'),
                        'type': directory.get('Type'),
                        'edition': directory.get('Edition'),
                        'size': directory.get('Size'),
                        'alias': directory.get('Alias'),
                        'access_url': directory.get('AccessUrl'),
                        'stage': directory.get('Stage'),
                        'stage_reason': directory.get('StageReason'),
                        'launch_time': str(directory.get('LaunchTime', '')),
                        'stage_last_updated_date_time': str(directory.get('StageLastUpdatedDateTime', '')),
                        'sso_enabled': directory.get('SsoEnabled'),
                        'vpc_settings': {
                            'vpc_id': directory.get('VpcSettings', {}).get('VpcId'),
                            'subnet_ids': directory.get('VpcSettings', {}).get('SubnetIds', []),
                            'availability_zones': directory.get('VpcSettings', {}).get('AvailabilityZones', []),
                        },
                        'dns_ip_addrs': directory.get('DnsIpAddrs', []),
                        'connect_settings': bool(directory.get('ConnectSettings')),
                        'radius_settings': bool(directory.get('RadiusSettings')),
                        'desired_number_of_domain_controllers': directory.get('DesiredNumberOfDomainControllers'),
                        'owner_directory_description': bool(directory.get('OwnerDirectoryDescription')),
                        'regions_info': directory.get('RegionsInfo'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
