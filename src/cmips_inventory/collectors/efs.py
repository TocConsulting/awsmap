"""
EFS resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_efs_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EFS resources: file systems, access points.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    efs = session.client('efs', region_name=region)

    # File Systems
    file_systems = []
    try:
        paginator = efs.get_paginator('describe_file_systems')
        for page in paginator.paginate():
            for fs in page.get('FileSystems', []):
                file_systems.append(fs)
                fs_id = fs['FileSystemId']
                fs_arn = fs.get('FileSystemArn', f"arn:aws:elasticfilesystem:{region}:{account_id}:file-system/{fs_id}")

                # Tags are included in response
                tags = {}
                for tag in fs.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                fs_name = tags.get('Name', fs_id)

                resources.append({
                    'service': 'efs',
                    'type': 'file-system',
                    'id': fs_id,
                    'arn': fs_arn,
                    'name': fs_name,
                    'region': region,
                    'details': {
                        'lifecycle_state': fs.get('LifeCycleState'),
                        'performance_mode': fs.get('PerformanceMode'),
                        'throughput_mode': fs.get('ThroughputMode'),
                        'provisioned_throughput': fs.get('ProvisionedThroughputInMibps'),
                        'size_in_bytes': fs.get('SizeInBytes', {}).get('Value'),
                        'number_of_mount_targets': fs.get('NumberOfMountTargets'),
                        'encrypted': fs.get('Encrypted'),
                        'kms_key_id': fs.get('KmsKeyId'),
                        'creation_time': str(fs.get('CreationTime', '')),
                        'availability_zone_name': fs.get('AvailabilityZoneName'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Access Points
    try:
        paginator = efs.get_paginator('describe_access_points')
        for page in paginator.paginate():
            for ap in page.get('AccessPoints', []):
                ap_id = ap['AccessPointId']
                ap_arn = ap.get('AccessPointArn', f"arn:aws:elasticfilesystem:{region}:{account_id}:access-point/{ap_id}")

                # Tags are included in response
                tags = {}
                for tag in ap.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                ap_name = ap.get('Name') or tags.get('Name', ap_id)

                resources.append({
                    'service': 'efs',
                    'type': 'access-point',
                    'id': ap_id,
                    'arn': ap_arn,
                    'name': ap_name,
                    'region': region,
                    'details': {
                        'file_system_id': ap.get('FileSystemId'),
                        'lifecycle_state': ap.get('LifeCycleState'),
                        'root_directory_path': ap.get('RootDirectory', {}).get('Path'),
                        'posix_user': ap.get('PosixUser'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Replication Configurations
    for fs in file_systems:
        fs_id = fs['FileSystemId']
        try:
            repl_response = efs.describe_replication_configurations(FileSystemId=fs_id)
            for repl in repl_response.get('Replications', []):
                source_fs_id = repl.get('SourceFileSystemId')
                destinations = repl.get('Destinations', [])

                for dest in destinations:
                    dest_fs_id = dest.get('FileSystemId')

                    resources.append({
                        'service': 'efs',
                        'type': 'replication-configuration',
                        'id': f"{source_fs_id}-{dest_fs_id}",
                        'arn': f"arn:aws:elasticfilesystem:{region}:{account_id}:file-system/{source_fs_id}/replication",
                        'name': f"replication-{source_fs_id[:8]}",
                        'region': region,
                        'details': {
                            'source_file_system_id': source_fs_id,
                            'source_file_system_region': repl.get('SourceFileSystemRegion'),
                            'source_file_system_arn': repl.get('SourceFileSystemArn'),
                            'original_source_file_system_arn': repl.get('OriginalSourceFileSystemArn'),
                            'creation_time': str(repl.get('CreationTime', '')),
                            'destination_file_system_id': dest_fs_id,
                            'destination_status': dest.get('Status'),
                            'destination_region': dest.get('Region'),
                        },
                        'tags': {}
                    })
        except Exception:
            pass

    return resources
