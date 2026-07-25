"""
ElastiCache resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_elasticache_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect ElastiCache resources: clusters, replication groups, users, user groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    elasticache = session.client('elasticache', region_name=region)

    # Cache Clusters
    try:
        paginator = elasticache.get_paginator('describe_cache_clusters')
        for page in paginator.paginate(ShowCacheNodeInfo=True):
            for cluster in page.get('CacheClusters', []):
                cluster_id = cluster['CacheClusterId']

                # Get tags
                tags = {}
                try:
                    arn = cluster.get('ARN', f"arn:aws:elasticache:{region}:{account_id}:cluster:{cluster_id}")
                    tag_response = elasticache.list_tags_for_resource(ResourceName=arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'elasticache',
                    'type': 'cluster',
                    'id': cluster_id,
                    'arn': cluster.get('ARN', f"arn:aws:elasticache:{region}:{account_id}:cluster:{cluster_id}"),
                    'name': cluster_id,
                    'region': region,
                    'details': {
                        'engine': cluster.get('Engine'),
                        'engine_version': cluster.get('EngineVersion'),
                        'cache_node_type': cluster.get('CacheNodeType'),
                        'num_cache_nodes': cluster.get('NumCacheNodes'),
                        'status': cluster.get('CacheClusterStatus'),
                        'preferred_availability_zone': cluster.get('PreferredAvailabilityZone'),
                        'cache_subnet_group_name': cluster.get('CacheSubnetGroupName'),
                        'replication_group_id': cluster.get('ReplicationGroupId'),
                        'snapshot_retention_limit': cluster.get('SnapshotRetentionLimit'),
                        'transit_encryption_enabled': cluster.get('TransitEncryptionEnabled'),
                        'at_rest_encryption_enabled': cluster.get('AtRestEncryptionEnabled'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Replication Groups (Redis with clustering or replicas)
    try:
        paginator = elasticache.get_paginator('describe_replication_groups')
        for page in paginator.paginate():
            for rg in page.get('ReplicationGroups', []):
                rg_id = rg['ReplicationGroupId']

                # Get tags
                tags = {}
                try:
                    arn = rg.get('ARN', f"arn:aws:elasticache:{region}:{account_id}:replicationgroup:{rg_id}")
                    tag_response = elasticache.list_tags_for_resource(ResourceName=arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                node_groups = rg.get('NodeGroups', [])

                resources.append({
                    'service': 'elasticache',
                    'type': 'replication-group',
                    'id': rg_id,
                    'arn': rg.get('ARN', f"arn:aws:elasticache:{region}:{account_id}:replicationgroup:{rg_id}"),
                    'name': rg_id,
                    'region': region,
                    'details': {
                        'description': rg.get('Description'),
                        'status': rg.get('Status'),
                        'cluster_enabled': rg.get('ClusterEnabled'),
                        'automatic_failover': rg.get('AutomaticFailover'),
                        'multi_az': rg.get('MultiAZ'),
                        'num_node_groups': len(node_groups),
                        'member_clusters': rg.get('MemberClusters', []),
                        'snapshot_retention_limit': rg.get('SnapshotRetentionLimit'),
                        'transit_encryption_enabled': rg.get('TransitEncryptionEnabled'),
                        'at_rest_encryption_enabled': rg.get('AtRestEncryptionEnabled'),
                        'auth_token_enabled': rg.get('AuthTokenEnabled'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Serverless Caches
    try:
        paginator = elasticache.get_paginator('describe_serverless_caches')
        for page in paginator.paginate():
            for sc in page.get('ServerlessCaches', []):
                sc_name = sc['ServerlessCacheName']
                sc_arn = sc['ARN']

                # Get tags
                tags = {}
                try:
                    tag_response = elasticache.list_tags_for_resource(ResourceName=sc_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'elasticache',
                    'type': 'serverless-cache',
                    'id': sc_name,
                    'arn': sc_arn,
                    'name': sc_name,
                    'region': region,
                    'details': {
                        'engine': sc.get('Engine'),
                        'status': sc.get('Status'),
                        'major_engine_version': sc.get('MajorEngineVersion'),
                        'full_engine_version': sc.get('FullEngineVersion'),
                        'cache_usage_limits': sc.get('CacheUsageLimits'),
                        'kms_key_id': sc.get('KmsKeyId'),
                        'security_group_ids': sc.get('SecurityGroupIds', []),
                        'endpoint': sc.get('Endpoint'),
                        'reader_endpoint': sc.get('ReaderEndpoint'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # User Groups
    try:
        paginator = elasticache.get_paginator('describe_user_groups')
        for page in paginator.paginate():
            for ug in page.get('UserGroups', []):
                ug_id = ug['UserGroupId']
                ug_arn = ug['ARN']

                # Get tags
                tags = {}
                try:
                    tag_response = elasticache.list_tags_for_resource(ResourceName=ug_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'elasticache',
                    'type': 'user-group',
                    'id': ug_id,
                    'arn': ug_arn,
                    'name': ug_id,
                    'region': region,
                    'details': {
                        'status': ug.get('Status'),
                        'engine': ug.get('Engine'),
                        'user_ids': ug.get('UserIds', []),
                        'replication_groups': ug.get('ReplicationGroups', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
