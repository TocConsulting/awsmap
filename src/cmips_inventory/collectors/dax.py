"""
AWS DynamoDB Accelerator (DAX) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# DAX supported regions (from https://docs.aws.amazon.com/general/latest/gr/ddb.html)
DAX_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-south-2', 'eu-north-1',
    'sa-east-1',
}


def collect_dax_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS DAX resources: clusters, parameter groups, and subnet groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in DAX_REGIONS:
        return []

    resources = []
    dax = session.client('dax', region_name=region)

    # Clusters
    try:
        paginator = dax.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for cluster in page.get('Clusters', []):
                cluster_name = cluster['ClusterName']
                cluster_arn = cluster.get('ClusterArn', '')

                details = {
                    'description': cluster.get('Description'),
                    'status': cluster.get('Status'),
                    'node_type': cluster.get('NodeType'),
                    'total_nodes': cluster.get('TotalNodes'),
                    'active_nodes': cluster.get('ActiveNodes'),
                    'cluster_discovery_endpoint': cluster.get('ClusterDiscoveryEndpoint', {}).get('Address'),
                    'cluster_discovery_port': cluster.get('ClusterDiscoveryEndpoint', {}).get('Port'),
                    'preferred_maintenance_window': cluster.get('PreferredMaintenanceWindow'),
                    'subnet_group': cluster.get('SubnetGroup'),
                    'security_groups': [sg.get('SecurityGroupIdentifier') for sg in cluster.get('SecurityGroups', [])],
                    'iam_role_arn': cluster.get('IamRoleArn'),
                    'parameter_group': cluster.get('ParameterGroup', {}).get('ParameterGroupName'),
                    'sse_enabled': cluster.get('SSEDescription', {}).get('Status') == 'ENABLED',
                    'cluster_endpoint_encryption_type': cluster.get('ClusterEndpointEncryptionType'),
                }

                # Node information
                nodes = cluster.get('Nodes', [])
                details['node_ids'] = [n.get('NodeId') for n in nodes]
                details['node_count'] = len(nodes)

                # Get tags
                tags = {}
                try:
                    tag_response = dax.list_tags(ResourceName=cluster_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'dax',
                    'type': 'cluster',
                    'id': cluster_name,
                    'arn': cluster_arn,
                    'name': cluster_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Parameter Groups (only custom, skip default)
    try:
        paginator = dax.get_paginator('describe_parameter_groups')
        for page in paginator.paginate():
            for pg in page.get('ParameterGroups', []):
                pg_name = pg['ParameterGroupName']

                # Skip default parameter group
                if pg_name == 'default.dax1.0':
                    continue

                details = {
                    'description': pg.get('Description'),
                }

                resources.append({
                    'service': 'dax',
                    'type': 'parameter-group',
                    'id': pg_name,
                    'arn': f"arn:aws:dax:{region}:{account_id}:parameter-group/{pg_name}",
                    'name': pg_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Subnet Groups
    try:
        paginator = dax.get_paginator('describe_subnet_groups')
        for page in paginator.paginate():
            for sg in page.get('SubnetGroups', []):
                sg_name = sg['SubnetGroupName']

                details = {
                    'description': sg.get('Description'),
                    'vpc_id': sg.get('VpcId'),
                    'subnets': [s.get('SubnetIdentifier') for s in sg.get('Subnets', [])],
                    'subnet_count': len(sg.get('Subnets', [])),
                }

                resources.append({
                    'service': 'dax',
                    'type': 'subnet-group',
                    'id': sg_name,
                    'arn': f"arn:aws:dax:{region}:{account_id}:subnet-group/{sg_name}",
                    'name': sg_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
