"""
Redshift resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_redshift_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Redshift resources: clusters, cluster snapshots, parameter groups, subnet groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    redshift = session.client('redshift', region_name=region)

    # Redshift Clusters
    try:
        paginator = redshift.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for cluster in page.get('Clusters', []):
                cluster_id = cluster['ClusterIdentifier']

                # Tags are included in the response
                tags = {}
                for tag in cluster.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                resources.append({
                    'service': 'redshift',
                    'type': 'cluster',
                    'id': cluster_id,
                    'arn': f"arn:aws:redshift:{region}:{account_id}:cluster:{cluster_id}",
                    'name': cluster_id,
                    'region': region,
                    'details': {
                        'node_type': cluster.get('NodeType'),
                        'cluster_status': cluster.get('ClusterStatus'),
                        'modify_status': cluster.get('ModifyStatus'),
                        'master_username': cluster.get('MasterUsername'),
                        'db_name': cluster.get('DBName'),
                        'endpoint': cluster.get('Endpoint', {}).get('Address'),
                        'port': cluster.get('Endpoint', {}).get('Port'),
                        'cluster_create_time': str(cluster.get('ClusterCreateTime', '')),
                        'automated_snapshot_retention_period': cluster.get('AutomatedSnapshotRetentionPeriod'),
                        'number_of_nodes': cluster.get('NumberOfNodes'),
                        'publicly_accessible': cluster.get('PubliclyAccessible'),
                        'encrypted': cluster.get('Encrypted'),
                        'vpc_id': cluster.get('VpcId'),
                        'cluster_version': cluster.get('ClusterVersion'),
                        'enhanced_vpc_routing': cluster.get('EnhancedVpcRouting'),
                        'maintenance_track_name': cluster.get('MaintenanceTrackName'),
                        'elastic_resize_number_of_node_options': cluster.get('ElasticResizeNumberOfNodeOptions'),
                        'total_storage_capacity_in_mega_bytes': cluster.get('TotalStorageCapacityInMegaBytes'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Serverless Workgroups
    try:
        redshift_serverless = session.client('redshift-serverless', region_name=region)
        paginator = redshift_serverless.get_paginator('list_workgroups')
        for page in paginator.paginate():
            for wg in page.get('workgroups', []):
                wg_name = wg['workgroupName']
                wg_arn = wg['workgroupArn']

                # Get tags
                tags = {}
                try:
                    tag_response = redshift_serverless.list_tags_for_resource(resourceArn=wg_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'redshift',
                    'type': 'serverless-workgroup',
                    'id': wg['workgroupId'],
                    'arn': wg_arn,
                    'name': wg_name,
                    'region': region,
                    'details': {
                        'status': wg.get('status'),
                        'namespace_name': wg.get('namespaceName'),
                        'base_capacity': wg.get('baseCapacity'),
                        'enhanced_vpc_routing': wg.get('enhancedVpcRouting'),
                        'publicly_accessible': wg.get('publiclyAccessible'),
                        'endpoint': wg.get('endpoint', {}).get('address'),
                        'port': wg.get('port'),
                        'creation_date': str(wg.get('creationDate', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Serverless Namespaces
    try:
        redshift_serverless = session.client('redshift-serverless', region_name=region)
        paginator = redshift_serverless.get_paginator('list_namespaces')
        for page in paginator.paginate():
            for ns in page.get('namespaces', []):
                ns_name = ns['namespaceName']
                ns_arn = ns['namespaceArn']

                # Get tags
                tags = {}
                try:
                    tag_response = redshift_serverless.list_tags_for_resource(resourceArn=ns_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'redshift',
                    'type': 'serverless-namespace',
                    'id': ns['namespaceId'],
                    'arn': ns_arn,
                    'name': ns_name,
                    'region': region,
                    'details': {
                        'status': ns.get('status'),
                        'admin_username': ns.get('adminUsername'),
                        'db_name': ns.get('dbName'),
                        'kms_key_id': ns.get('kmsKeyId'),
                        'default_iam_role_arn': ns.get('defaultIamRoleArn'),
                        'creation_date': str(ns.get('creationDate', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Custom Parameter Groups (not default)
    try:
        paginator = redshift.get_paginator('describe_cluster_parameter_groups')
        for page in paginator.paginate():
            for pg in page.get('ParameterGroups', []):
                pg_name = pg['ParameterGroupName']

                # Skip default parameter groups
                if pg_name.startswith('default.'):
                    continue

                # Tags are included in the response
                tags = {}
                for tag in pg.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                resources.append({
                    'service': 'redshift',
                    'type': 'parameter-group',
                    'id': pg_name,
                    'arn': f"arn:aws:redshift:{region}:{account_id}:parametergroup:{pg_name}",
                    'name': pg_name,
                    'region': region,
                    'details': {
                        'parameter_group_family': pg.get('ParameterGroupFamily'),
                        'description': pg.get('Description'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Subnet Groups
    try:
        paginator = redshift.get_paginator('describe_cluster_subnet_groups')
        for page in paginator.paginate():
            for sg in page.get('ClusterSubnetGroups', []):
                sg_name = sg['ClusterSubnetGroupName']

                # Tags are included in the response
                tags = {}
                for tag in sg.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                resources.append({
                    'service': 'redshift',
                    'type': 'subnet-group',
                    'id': sg_name,
                    'arn': f"arn:aws:redshift:{region}:{account_id}:subnetgroup:{sg_name}",
                    'name': sg_name,
                    'region': region,
                    'details': {
                        'description': sg.get('Description'),
                        'vpc_id': sg.get('VpcId'),
                        'subnet_group_status': sg.get('SubnetGroupStatus'),
                        'subnets': [s.get('SubnetIdentifier') for s in sg.get('Subnets', [])],
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
