"""
RDS resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_rds_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect RDS resources: DB instances, clusters, cluster snapshots, DB snapshots,
    subnet groups, parameter groups, option groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    rds = session.client('rds', region_name=region)

    # DB Instances
    try:
        paginator = rds.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for db in page.get('DBInstances', []):
                db_id = db['DBInstanceIdentifier']

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=db['DBInstanceArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'db-instance',
                    'id': db_id,
                    'arn': db['DBInstanceArn'],
                    'name': db_id,
                    'region': region,
                    'details': {
                        'engine': db.get('Engine'),
                        'engine_version': db.get('EngineVersion'),
                        'instance_class': db.get('DBInstanceClass'),
                        'status': db.get('DBInstanceStatus'),
                        'storage_type': db.get('StorageType'),
                        'allocated_storage': db.get('AllocatedStorage'),
                        'multi_az': db.get('MultiAZ'),
                        'publicly_accessible': db.get('PubliclyAccessible'),
                        'encrypted': db.get('StorageEncrypted'),
                        'endpoint': db.get('Endpoint', {}).get('Address'),
                        'port': db.get('Endpoint', {}).get('Port'),
                        'vpc_id': db.get('DBSubnetGroup', {}).get('VpcId'),
                        'cluster_identifier': db.get('DBClusterIdentifier'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # DB Clusters (Aurora)
    try:
        paginator = rds.get_paginator('describe_db_clusters')
        for page in paginator.paginate():
            for cluster in page.get('DBClusters', []):
                cluster_id = cluster['DBClusterIdentifier']

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=cluster['DBClusterArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'db-cluster',
                    'id': cluster_id,
                    'arn': cluster['DBClusterArn'],
                    'name': cluster_id,
                    'region': region,
                    'details': {
                        'engine': cluster.get('Engine'),
                        'engine_version': cluster.get('EngineVersion'),
                        'engine_mode': cluster.get('EngineMode'),
                        'status': cluster.get('Status'),
                        'multi_az': cluster.get('MultiAZ'),
                        'encrypted': cluster.get('StorageEncrypted'),
                        'endpoint': cluster.get('Endpoint'),
                        'reader_endpoint': cluster.get('ReaderEndpoint'),
                        'port': cluster.get('Port'),
                        'members': len(cluster.get('DBClusterMembers', [])),
                        'serverless_v2_scaling': cluster.get('ServerlessV2ScalingConfiguration'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # DB Snapshots (manual only, owned by account)
    try:
        paginator = rds.get_paginator('describe_db_snapshots')
        for page in paginator.paginate(SnapshotType='manual'):
            for snapshot in page.get('DBSnapshots', []):
                snapshot_id = snapshot['DBSnapshotIdentifier']

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=snapshot['DBSnapshotArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'db-snapshot',
                    'id': snapshot_id,
                    'arn': snapshot['DBSnapshotArn'],
                    'name': snapshot_id,
                    'region': region,
                    'details': {
                        'db_instance_identifier': snapshot.get('DBInstanceIdentifier'),
                        'engine': snapshot.get('Engine'),
                        'engine_version': snapshot.get('EngineVersion'),
                        'status': snapshot.get('Status'),
                        'allocated_storage': snapshot.get('AllocatedStorage'),
                        'encrypted': snapshot.get('Encrypted'),
                        'snapshot_create_time': str(snapshot.get('SnapshotCreateTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # DB Cluster Snapshots (manual only)
    try:
        paginator = rds.get_paginator('describe_db_cluster_snapshots')
        for page in paginator.paginate(SnapshotType='manual'):
            for snapshot in page.get('DBClusterSnapshots', []):
                snapshot_id = snapshot['DBClusterSnapshotIdentifier']

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=snapshot['DBClusterSnapshotArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'db-cluster-snapshot',
                    'id': snapshot_id,
                    'arn': snapshot['DBClusterSnapshotArn'],
                    'name': snapshot_id,
                    'region': region,
                    'details': {
                        'db_cluster_identifier': snapshot.get('DBClusterIdentifier'),
                        'engine': snapshot.get('Engine'),
                        'engine_version': snapshot.get('EngineVersion'),
                        'status': snapshot.get('Status'),
                        'allocated_storage': snapshot.get('AllocatedStorage'),
                        'encrypted': snapshot.get('StorageEncrypted'),
                        'snapshot_create_time': str(snapshot.get('SnapshotCreateTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # DB Subnet Groups
    try:
        paginator = rds.get_paginator('describe_db_subnet_groups')
        for page in paginator.paginate():
            for sg in page.get('DBSubnetGroups', []):
                sg_name = sg['DBSubnetGroupName']

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=sg['DBSubnetGroupArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'db-subnet-group',
                    'id': sg_name,
                    'arn': sg['DBSubnetGroupArn'],
                    'name': sg_name,
                    'region': region,
                    'details': {
                        'description': sg.get('DBSubnetGroupDescription'),
                        'vpc_id': sg.get('VpcId'),
                        'status': sg.get('SubnetGroupStatus'),
                        'subnets': [s.get('SubnetIdentifier') for s in sg.get('Subnets', [])],
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # DB Parameter Groups (non-default)
    try:
        paginator = rds.get_paginator('describe_db_parameter_groups')
        for page in paginator.paginate():
            for pg in page.get('DBParameterGroups', []):
                pg_name = pg['DBParameterGroupName']

                # Skip default parameter groups
                if pg_name.startswith('default.'):
                    continue

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=pg['DBParameterGroupArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'db-parameter-group',
                    'id': pg_name,
                    'arn': pg['DBParameterGroupArn'],
                    'name': pg_name,
                    'region': region,
                    'details': {
                        'family': pg.get('DBParameterGroupFamily'),
                        'description': pg.get('Description'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # DB Option Groups (non-default)
    try:
        paginator = rds.get_paginator('describe_option_groups')
        for page in paginator.paginate():
            for og in page.get('OptionGroupsList', []):
                og_name = og['OptionGroupName']

                # Skip default option groups
                if og_name.startswith('default:'):
                    continue

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=og['OptionGroupArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'option-group',
                    'id': og_name,
                    'arn': og['OptionGroupArn'],
                    'name': og_name,
                    'region': region,
                    'details': {
                        'engine_name': og.get('EngineName'),
                        'major_engine_version': og.get('MajorEngineVersion'),
                        'description': og.get('OptionGroupDescription'),
                        'options_count': len(og.get('Options', [])),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # RDS Proxies
    try:
        paginator = rds.get_paginator('describe_db_proxies')
        for page in paginator.paginate():
            for proxy in page.get('DBProxies', []):
                proxy_name = proxy['DBProxyName']

                # Get tags
                tags = {}
                try:
                    tag_response = rds.list_tags_for_resource(
                        ResourceName=proxy['DBProxyArn']
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'rds',
                    'type': 'db-proxy',
                    'id': proxy_name,
                    'arn': proxy['DBProxyArn'],
                    'name': proxy_name,
                    'region': region,
                    'details': {
                        'status': proxy.get('Status'),
                        'engine_family': proxy.get('EngineFamily'),
                        'endpoint': proxy.get('Endpoint'),
                        'vpc_id': proxy.get('VpcId'),
                        'require_tls': proxy.get('RequireTLS'),
                        'idle_client_timeout': proxy.get('IdleClientTimeout'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
