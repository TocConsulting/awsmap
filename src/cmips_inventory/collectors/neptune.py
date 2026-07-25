"""
Neptune resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_neptune_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Neptune resources: clusters, instances.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    neptune = session.client('neptune', region_name=region)

    # Neptune Clusters
    try:
        paginator = neptune.get_paginator('describe_db_clusters')
        for page in paginator.paginate(Filters=[{'Name': 'engine', 'Values': ['neptune']}]):
            for cluster in page.get('DBClusters', []):
                cluster_id = cluster['DBClusterIdentifier']
                cluster_arn = cluster['DBClusterArn']

                # Get tags
                tags = {}
                try:
                    tag_response = neptune.list_tags_for_resource(ResourceName=cluster_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'neptune',
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
                        'multi_az': cluster.get('MultiAZ'),
                        'storage_encrypted': cluster.get('StorageEncrypted'),
                        'kms_key_id': cluster.get('KmsKeyId'),
                        'db_cluster_members': len(cluster.get('DBClusterMembers', [])),
                        'backup_retention_period': cluster.get('BackupRetentionPeriod'),
                        'deletion_protection': cluster.get('DeletionProtection'),
                        'iam_database_authentication_enabled': cluster.get('IAMDatabaseAuthenticationEnabled'),
                        'serverless_v2_scaling_configuration': cluster.get('ServerlessV2ScalingConfiguration'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Neptune Instances
    try:
        paginator = neptune.get_paginator('describe_db_instances')
        for page in paginator.paginate(Filters=[{'Name': 'engine', 'Values': ['neptune']}]):
            for instance in page.get('DBInstances', []):
                instance_id = instance['DBInstanceIdentifier']
                instance_arn = instance['DBInstanceArn']

                # Get tags
                tags = {}
                try:
                    tag_response = neptune.list_tags_for_resource(ResourceName=instance_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'neptune',
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
                        'promotion_tier': instance.get('PromotionTier'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
