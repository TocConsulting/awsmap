"""
DocumentDB resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_docdb_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect DocumentDB resources: clusters, instances, cluster snapshots.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    docdb = session.client('docdb', region_name=region)

    # DocumentDB Clusters
    try:
        paginator = docdb.get_paginator('describe_db_clusters')
        for page in paginator.paginate(Filters=[{'Name': 'engine', 'Values': ['docdb']}]):
            for cluster in page.get('DBClusters', []):
                cluster_id = cluster['DBClusterIdentifier']
                cluster_arn = cluster['DBClusterArn']

                # Get tags
                tags = {}
                try:
                    tag_response = docdb.list_tags_for_resource(ResourceName=cluster_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'docdb',
                    'type': 'cluster',
                    'id': cluster_id,
                    'arn': cluster_arn,
                    'name': cluster_id,
                    'region': region,
                    'details': {
                        'status': cluster.get('Status'),
                        'engine': cluster.get('Engine'),
                        'engine_version': cluster.get('EngineVersion'),
                        'endpoint': cluster.get('Endpoint'),
                        'reader_endpoint': cluster.get('ReaderEndpoint'),
                        'port': cluster.get('Port'),
                        'master_username': cluster.get('MasterUsername'),
                        'multi_az': cluster.get('MultiAZ'),
                        'storage_encrypted': cluster.get('StorageEncrypted'),
                        'kms_key_id': cluster.get('KmsKeyId'),
                        'db_cluster_members': len(cluster.get('DBClusterMembers', [])),
                        'backup_retention_period': cluster.get('BackupRetentionPeriod'),
                        'deletion_protection': cluster.get('DeletionProtection'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # DocumentDB Instances
    try:
        paginator = docdb.get_paginator('describe_db_instances')
        for page in paginator.paginate(Filters=[{'Name': 'engine', 'Values': ['docdb']}]):
            for instance in page.get('DBInstances', []):
                instance_id = instance['DBInstanceIdentifier']
                instance_arn = instance['DBInstanceArn']

                # Get tags
                tags = {}
                try:
                    tag_response = docdb.list_tags_for_resource(ResourceName=instance_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'docdb',
                    'type': 'instance',
                    'id': instance_id,
                    'arn': instance_arn,
                    'name': instance_id,
                    'region': region,
                    'details': {
                        'cluster_identifier': instance.get('DBClusterIdentifier'),
                        'instance_class': instance.get('DBInstanceClass'),
                        'status': instance.get('DBInstanceStatus'),
                        'engine': instance.get('Engine'),
                        'engine_version': instance.get('EngineVersion'),
                        'endpoint': instance.get('Endpoint', {}).get('Address'),
                        'port': instance.get('Endpoint', {}).get('Port'),
                        'availability_zone': instance.get('AvailabilityZone'),
                        'publicly_accessible': instance.get('PubliclyAccessible'),
                        'storage_encrypted': instance.get('StorageEncrypted'),
                        'ca_certificate_identifier': instance.get('CACertificateIdentifier'),
                        'promotion_tier': instance.get('PromotionTier'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
