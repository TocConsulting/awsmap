"""
FSx resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_fsx_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect FSx resources: file systems, volumes, backups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    fsx = session.client('fsx', region_name=region)

    # FSx File Systems
    try:
        paginator = fsx.get_paginator('describe_file_systems')
        for page in paginator.paginate():
            for fs in page.get('FileSystems', []):
                fs_id = fs['FileSystemId']
                fs_arn = fs.get('ResourceARN', f"arn:aws:fsx:{region}:{account_id}:file-system/{fs_id}")

                # Tags are included in the response
                tags = {}
                for tag in fs.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                fs_type = fs.get('FileSystemType', 'UNKNOWN')
                fs_name = tags.get('Name', fs_id)

                resources.append({
                    'service': 'fsx',
                    'type': f'file-system-{fs_type.lower()}',
                    'id': fs_id,
                    'arn': fs_arn,
                    'name': fs_name,
                    'region': region,
                    'details': {
                        'file_system_type': fs_type,
                        'lifecycle': fs.get('Lifecycle'),
                        'storage_capacity': fs.get('StorageCapacity'),
                        'storage_type': fs.get('StorageType'),
                        'vpc_id': fs.get('VpcId'),
                        'subnet_ids': fs.get('SubnetIds', []),
                        'dns_name': fs.get('DNSName'),
                        'kms_key_id': fs.get('KmsKeyId'),
                        'creation_time': str(fs.get('CreationTime', '')),
                        'owner_id': fs.get('OwnerId'),
                        'file_system_type_version': fs.get('FileSystemTypeVersion'),
                        # Type-specific details
                        'windows_configuration': bool(fs.get('WindowsConfiguration')),
                        'lustre_configuration': bool(fs.get('LustreConfiguration')),
                        'ontap_configuration': bool(fs.get('OntapConfiguration')),
                        'openzfs_configuration': bool(fs.get('OpenZFSConfiguration')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # FSx Volumes (ONTAP and OpenZFS)
    try:
        paginator = fsx.get_paginator('describe_volumes')
        for page in paginator.paginate():
            for volume in page.get('Volumes', []):
                vol_id = volume['VolumeId']
                vol_arn = volume.get('ResourceARN', f"arn:aws:fsx:{region}:{account_id}:volume/{vol_id}")

                # Tags are included in the response
                tags = {}
                for tag in volume.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                vol_type = volume.get('VolumeType', 'UNKNOWN')
                vol_name = volume.get('Name') or tags.get('Name', vol_id)

                resources.append({
                    'service': 'fsx',
                    'type': f'volume-{vol_type.lower()}',
                    'id': vol_id,
                    'arn': vol_arn,
                    'name': vol_name,
                    'region': region,
                    'details': {
                        'volume_type': vol_type,
                        'lifecycle': volume.get('Lifecycle'),
                        'file_system_id': volume.get('FileSystemId'),
                        'creation_time': str(volume.get('CreationTime', '')),
                        'ontap_configuration': {
                            'junction_path': volume.get('OntapConfiguration', {}).get('JunctionPath'),
                            'size_in_megabytes': volume.get('OntapConfiguration', {}).get('SizeInMegabytes'),
                            'storage_efficiency_enabled': volume.get('OntapConfiguration', {}).get('StorageEfficiencyEnabled'),
                            'storage_virtual_machine_id': volume.get('OntapConfiguration', {}).get('StorageVirtualMachineId'),
                            'tiering_policy': volume.get('OntapConfiguration', {}).get('TieringPolicy'),
                        } if volume.get('OntapConfiguration') else None,
                        'openzfs_configuration': {
                            'parent_volume_id': volume.get('OpenZFSConfiguration', {}).get('ParentVolumeId'),
                            'volume_path': volume.get('OpenZFSConfiguration', {}).get('VolumePath'),
                            'storage_capacity_quota_gib': volume.get('OpenZFSConfiguration', {}).get('StorageCapacityQuotaGiB'),
                            'data_compression_type': volume.get('OpenZFSConfiguration', {}).get('DataCompressionType'),
                        } if volume.get('OpenZFSConfiguration') else None,
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # FSx Backups
    try:
        paginator = fsx.get_paginator('describe_backups')
        for page in paginator.paginate():
            for backup in page.get('Backups', []):
                backup_id = backup['BackupId']
                backup_arn = backup.get('ResourceARN', f"arn:aws:fsx:{region}:{account_id}:backup/{backup_id}")

                # Tags are included in the response
                tags = {}
                for tag in backup.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                resources.append({
                    'service': 'fsx',
                    'type': 'backup',
                    'id': backup_id,
                    'arn': backup_arn,
                    'name': tags.get('Name', backup_id),
                    'region': region,
                    'details': {
                        'lifecycle': backup.get('Lifecycle'),
                        'type': backup.get('Type'),
                        'file_system_id': backup.get('FileSystem', {}).get('FileSystemId'),
                        'file_system_type': backup.get('FileSystem', {}).get('FileSystemType'),
                        'volume_id': backup.get('Volume', {}).get('VolumeId'),
                        'creation_time': str(backup.get('CreationTime', '')),
                        'progress_percent': backup.get('ProgressPercent'),
                        'kms_key_id': backup.get('KmsKeyId'),
                        'source_backup_id': backup.get('SourceBackupId'),
                        'source_backup_region': backup.get('SourceBackupRegion'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
