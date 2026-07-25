"""
AWS CloudHSM v2 resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_cloudhsmv2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS CloudHSM v2 resources: clusters and backups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    cloudhsm = session.client('cloudhsmv2', region_name=region)

    # Clusters
    try:
        paginator = cloudhsm.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for cluster in page.get('Clusters', []):
                cluster_id = cluster['ClusterId']

                details = {
                    'state': cluster.get('State'),
                    'state_message': cluster.get('StateMessage'),
                    'hsm_type': cluster.get('HsmType'),
                    'vpc_id': cluster.get('VpcId'),
                    'subnet_mapping': cluster.get('SubnetMapping', {}),
                    'security_group': cluster.get('SecurityGroup'),
                    'create_timestamp': str(cluster.get('CreateTimestamp', '')),
                    'backup_policy': cluster.get('BackupPolicy'),
                    'backup_retention_policy': cluster.get('BackupRetentionPolicy', {}),
                    'source_backup_id': cluster.get('SourceBackupId'),
                    'mode': cluster.get('Mode'),
                }

                # HSMs in the cluster
                hsms = cluster.get('Hsms', [])
                details['hsm_count'] = len(hsms)
                details['hsm_ids'] = [h.get('HsmId') for h in hsms]
                details['hsm_states'] = [h.get('State') for h in hsms]

                # Certificates
                certs = cluster.get('Certificates', {})
                if certs:
                    details['cluster_csr'] = bool(certs.get('ClusterCsr'))
                    details['hsm_certificate'] = bool(certs.get('HsmCertificate'))
                    details['aws_hardware_certificate'] = bool(certs.get('AwsHardwareCertificate'))
                    details['manufacturer_hardware_certificate'] = bool(certs.get('ManufacturerHardwareCertificate'))
                    details['cluster_certificate'] = bool(certs.get('ClusterCertificate'))

                # Get tags
                tags = {}
                try:
                    tag_paginator = cloudhsm.get_paginator('list_tags')
                    for tag_page in tag_paginator.paginate(ResourceId=cluster_id):
                        for tag in tag_page.get('TagList', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'cloudhsmv2',
                    'type': 'cluster',
                    'id': cluster_id,
                    'arn': f"arn:aws:cloudhsm:{region}:{account_id}:cluster/{cluster_id}",
                    'name': cluster_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Backups
    try:
        paginator = cloudhsm.get_paginator('describe_backups')
        for page in paginator.paginate():
            for backup in page.get('Backups', []):
                backup_id = backup['BackupId']

                details = {
                    'backup_state': backup.get('BackupState'),
                    'cluster_id': backup.get('ClusterId'),
                    'create_timestamp': str(backup.get('CreateTimestamp', '')),
                    'copy_timestamp': str(backup.get('CopyTimestamp', '')),
                    'never_expires': backup.get('NeverExpires'),
                    'source_region': backup.get('SourceRegion'),
                    'source_backup': backup.get('SourceBackup'),
                    'source_cluster': backup.get('SourceCluster'),
                    'delete_timestamp': str(backup.get('DeleteTimestamp', '')),
                    'hsm_type': backup.get('HsmType'),
                    'mode': backup.get('Mode'),
                }

                # Get tags
                tags = {}
                try:
                    tag_paginator = cloudhsm.get_paginator('list_tags')
                    for tag_page in tag_paginator.paginate(ResourceId=backup_id):
                        for tag in tag_page.get('TagList', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'cloudhsmv2',
                    'type': 'backup',
                    'id': backup_id,
                    'arn': f"arn:aws:cloudhsm:{region}:{account_id}:backup/{backup_id}",
                    'name': backup_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
