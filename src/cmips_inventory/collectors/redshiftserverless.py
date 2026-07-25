"""
Amazon Redshift Serverless resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_redshiftserverless_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Redshift Serverless resources: namespaces, workgroups, snapshots.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    rsserverless = session.client('redshift-serverless', region_name=region)

    # Namespaces
    try:
        paginator = rsserverless.get_paginator('list_namespaces')
        for page in paginator.paginate():
            for namespace in page.get('namespaces', []):
                namespace_arn = namespace.get('namespaceArn', '')
                namespace_name = namespace.get('namespaceName', namespace_arn.split('/')[-1])

                details = {
                    'namespace_id': namespace.get('namespaceId'),
                    'status': namespace.get('status'),
                    'db_name': namespace.get('dbName'),
                    'admin_username': namespace.get('adminUsername'),
                    'creation_date': str(namespace.get('creationDate', '')) if namespace.get('creationDate') else None,
                }

                resources.append({
                    'service': 'redshift-serverless',
                    'type': 'namespace',
                    'id': namespace.get('namespaceId', namespace_name),
                    'arn': namespace_arn,
                    'name': namespace_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Workgroups
    try:
        paginator = rsserverless.get_paginator('list_workgroups')
        for page in paginator.paginate():
            for workgroup in page.get('workgroups', []):
                workgroup_arn = workgroup.get('workgroupArn', '')
                workgroup_name = workgroup.get('workgroupName', workgroup_arn.split('/')[-1])

                details = {
                    'workgroup_id': workgroup.get('workgroupId'),
                    'namespace_name': workgroup.get('namespaceName'),
                    'status': workgroup.get('status'),
                    'base_capacity': workgroup.get('baseCapacity'),
                    'max_capacity': workgroup.get('maxCapacity'),
                    'enhanced_vpc_routing': workgroup.get('enhancedVpcRouting'),
                    'publicly_accessible': workgroup.get('publiclyAccessible'),
                    'creation_date': str(workgroup.get('creationDate', '')) if workgroup.get('creationDate') else None,
                }

                endpoint = workgroup.get('endpoint', {})
                if endpoint:
                    details['endpoint_address'] = endpoint.get('address')
                    details['endpoint_port'] = endpoint.get('port')

                resources.append({
                    'service': 'redshift-serverless',
                    'type': 'workgroup',
                    'id': workgroup.get('workgroupId', workgroup_name),
                    'arn': workgroup_arn,
                    'name': workgroup_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Snapshots
    try:
        paginator = rsserverless.get_paginator('list_snapshots')
        for page in paginator.paginate():
            for snapshot in page.get('snapshots', []):
                snapshot_arn = snapshot.get('snapshotArn', '')
                snapshot_name = snapshot.get('snapshotName', snapshot_arn.split('/')[-1])

                details = {
                    'namespace_name': snapshot.get('namespaceName'),
                    'namespace_arn': snapshot.get('namespaceArn'),
                    'status': snapshot.get('status'),
                    'snapshot_create_time': str(snapshot.get('snapshotCreateTime', '')) if snapshot.get('snapshotCreateTime') else None,
                    'total_backup_size_in_mega_bytes': snapshot.get('totalBackupSizeInMegaBytes'),
                }

                resources.append({
                    'service': 'redshift-serverless',
                    'type': 'snapshot',
                    'id': snapshot_name,
                    'arn': snapshot_arn,
                    'name': snapshot_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
