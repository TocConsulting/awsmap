"""
MemoryDB resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

# MemoryDB supported regions
# https://docs.aws.amazon.com/general/latest/gr/memorydb-service.html
MEMORYDB_REGIONS = {
    # US
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    # Asia Pacific
    'ap-east-1', 'ap-south-1', 'ap-northeast-1', 'ap-northeast-2',
    'ap-southeast-1', 'ap-southeast-2',
    # Canada
    'ca-central-1',
    # Europe
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3',
    'eu-south-1', 'eu-south-2', 'eu-north-1',
    # South America
    'sa-east-1',
}


def collect_memorydb_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect MemoryDB resources: clusters, users, ACLs.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions to avoid timeouts
    if region and region not in MEMORYDB_REGIONS:
        return []

    resources = []
    memorydb = session.client('memorydb', region_name=region)

    # MemoryDB Clusters
    try:
        paginator = memorydb.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for cluster in page.get('Clusters', []):
                cluster_name = cluster['Name']
                cluster_arn = cluster['ARN']

                # Get tags
                tags = {}
                try:
                    tag_response = memorydb.list_tags(ResourceArn=cluster_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'memorydb',
                    'type': 'cluster',
                    'id': cluster_name,
                    'arn': cluster_arn,
                    'name': cluster_name,
                    'region': region,
                    'details': {
                        'status': cluster.get('Status'),
                        'node_type': cluster.get('NodeType'),
                        'engine_version': cluster.get('EngineVersion'),
                        'engine_patch_version': cluster.get('EnginePatchVersion'),
                        'number_of_shards': cluster.get('NumberOfShards'),
                        'num_replicas_per_shard': cluster.get('Shards', [{}])[0].get('NumberOfNodes', 1) - 1 if cluster.get('Shards') else 0,
                        'availability_mode': cluster.get('AvailabilityMode'),
                        'cluster_endpoint': cluster.get('ClusterEndpoint', {}).get('Address'),
                        'port': cluster.get('ClusterEndpoint', {}).get('Port'),
                        'parameter_group_name': cluster.get('ParameterGroupName'),
                        'subnet_group_name': cluster.get('SubnetGroupName'),
                        'tls_enabled': cluster.get('TLSEnabled'),
                        'kms_key_id': cluster.get('KmsKeyId'),
                        'acl_name': cluster.get('ACLName'),
                        'snapshot_retention_limit': cluster.get('SnapshotRetentionLimit'),
                        'maintenance_window': cluster.get('MaintenanceWindow'),
                        'sns_topic_arn': cluster.get('SnsTopicArn'),
                        'data_tiering': cluster.get('DataTiering'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # MemoryDB ACLs
    try:
        paginator = memorydb.get_paginator('describe_acls')
        for page in paginator.paginate():
            for acl in page.get('ACLs', []):
                acl_name = acl['Name']
                acl_arn = acl['ARN']

                # Skip default ACL
                if acl_name == 'open-access':
                    continue

                # Get tags
                tags = {}
                try:
                    tag_response = memorydb.list_tags(ResourceArn=acl_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'memorydb',
                    'type': 'acl',
                    'id': acl_name,
                    'arn': acl_arn,
                    'name': acl_name,
                    'region': region,
                    'details': {
                        'status': acl.get('Status'),
                        'user_names': acl.get('UserNames', []),
                        'clusters': acl.get('Clusters', []),
                        'minimum_engine_version': acl.get('MinimumEngineVersion'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # MemoryDB Users
    try:
        paginator = memorydb.get_paginator('describe_users')
        for page in paginator.paginate():
            for user in page.get('Users', []):
                user_name = user['Name']
                user_arn = user['ARN']

                # Skip default user
                if user_name == 'default':
                    continue

                # Get tags
                tags = {}
                try:
                    tag_response = memorydb.list_tags(ResourceArn=user_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'memorydb',
                    'type': 'user',
                    'id': user_name,
                    'arn': user_arn,
                    'name': user_name,
                    'region': region,
                    'details': {
                        'status': user.get('Status'),
                        'access_string': user.get('AccessString'),
                        'acl_names': user.get('ACLNames', []),
                        'minimum_engine_version': user.get('MinimumEngineVersion'),
                        'authentication_mode': user.get('Authentication', {}).get('Type'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
