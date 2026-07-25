"""
AWS Database Migration Service (DMS) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_dms_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS DMS resources: replication instances, tasks, endpoints, certificates, and subnet groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    dms = session.client('dms', region_name=region)

    # Replication Instances
    try:
        paginator = dms.get_paginator('describe_replication_instances')
        for page in paginator.paginate():
            for instance in page.get('ReplicationInstances', []):
                instance_id = instance['ReplicationInstanceIdentifier']
                instance_arn = instance.get('ReplicationInstanceArn', '')

                details = {
                    'replication_instance_class': instance.get('ReplicationInstanceClass'),
                    'replication_instance_status': instance.get('ReplicationInstanceStatus'),
                    'allocated_storage': instance.get('AllocatedStorage'),
                    'engine_version': instance.get('EngineVersion'),
                    'auto_minor_version_upgrade': instance.get('AutoMinorVersionUpgrade'),
                    'multi_az': instance.get('MultiAZ'),
                    'publicly_accessible': instance.get('PubliclyAccessible'),
                    'availability_zone': instance.get('AvailabilityZone'),
                    'replication_subnet_group_id': instance.get('ReplicationSubnetGroup', {}).get('ReplicationSubnetGroupIdentifier'),
                    'vpc_security_group_ids': [sg.get('VpcSecurityGroupId') for sg in instance.get('VpcSecurityGroups', [])],
                    'kms_key_id': instance.get('KmsKeyId'),
                    'free_until': str(instance.get('FreeUntil', '')),
                    'instance_create_time': str(instance.get('InstanceCreateTime', '')),
                }

                resources.append({
                    'service': 'dms',
                    'type': 'replication-instance',
                    'id': instance_id,
                    'arn': instance_arn,
                    'name': instance_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Replication Tasks
    try:
        paginator = dms.get_paginator('describe_replication_tasks')
        for page in paginator.paginate():
            for task in page.get('ReplicationTasks', []):
                task_id = task['ReplicationTaskIdentifier']
                task_arn = task.get('ReplicationTaskArn', '')

                details = {
                    'source_endpoint_arn': task.get('SourceEndpointArn'),
                    'target_endpoint_arn': task.get('TargetEndpointArn'),
                    'replication_instance_arn': task.get('ReplicationInstanceArn'),
                    'migration_type': task.get('MigrationType'),
                    'status': task.get('Status'),
                    'stop_reason': task.get('StopReason'),
                    'replication_task_creation_date': str(task.get('ReplicationTaskCreationDate', '')),
                    'replication_task_start_date': str(task.get('ReplicationTaskStartDate', '')),
                    'cdc_start_position': task.get('CdcStartPosition'),
                    'cdc_stop_position': task.get('CdcStopPosition'),
                    'recovery_checkpoint': task.get('RecoveryCheckpoint'),
                }

                stats = task.get('ReplicationTaskStats', {})
                if stats:
                    details['tables_loaded'] = stats.get('TablesLoaded')
                    details['tables_loading'] = stats.get('TablesLoading')
                    details['tables_queued'] = stats.get('TablesQueued')
                    details['tables_errored'] = stats.get('TablesErrored')
                    details['elapsed_time_millis'] = stats.get('ElapsedTimeMillis')

                resources.append({
                    'service': 'dms',
                    'type': 'replication-task',
                    'id': task_id,
                    'arn': task_arn,
                    'name': task_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Endpoints
    try:
        paginator = dms.get_paginator('describe_endpoints')
        for page in paginator.paginate():
            for endpoint in page.get('Endpoints', []):
                endpoint_id = endpoint['EndpointIdentifier']
                endpoint_arn = endpoint.get('EndpointArn', '')

                details = {
                    'endpoint_type': endpoint.get('EndpointType'),
                    'engine_name': endpoint.get('EngineName'),
                    'engine_display_name': endpoint.get('EngineDisplayName'),
                    'server_name': endpoint.get('ServerName'),
                    'port': endpoint.get('Port'),
                    'database_name': endpoint.get('DatabaseName'),
                    'status': endpoint.get('Status'),
                    'kms_key_id': endpoint.get('KmsKeyId'),
                    'ssl_mode': endpoint.get('SslMode'),
                    'certificate_arn': endpoint.get('CertificateArn'),
                }

                resources.append({
                    'service': 'dms',
                    'type': 'endpoint',
                    'id': endpoint_id,
                    'arn': endpoint_arn,
                    'name': endpoint_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Certificates
    try:
        paginator = dms.get_paginator('describe_certificates')
        for page in paginator.paginate():
            for cert in page.get('Certificates', []):
                cert_id = cert['CertificateIdentifier']
                cert_arn = cert.get('CertificateArn', '')

                details = {
                    'certificate_owner': cert.get('CertificateOwner'),
                    'valid_from_date': str(cert.get('ValidFromDate', '')),
                    'valid_to_date': str(cert.get('ValidToDate', '')),
                    'signing_algorithm': cert.get('SigningAlgorithm'),
                    'key_length': cert.get('KeyLength'),
                    'certificate_creation_date': str(cert.get('CertificateCreationDate', '')),
                }

                resources.append({
                    'service': 'dms',
                    'type': 'certificate',
                    'id': cert_id,
                    'arn': cert_arn,
                    'name': cert_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Replication Subnet Groups
    try:
        paginator = dms.get_paginator('describe_replication_subnet_groups')
        for page in paginator.paginate():
            for group in page.get('ReplicationSubnetGroups', []):
                group_id = group['ReplicationSubnetGroupIdentifier']

                details = {
                    'replication_subnet_group_description': group.get('ReplicationSubnetGroupDescription'),
                    'vpc_id': group.get('VpcId'),
                    'subnet_group_status': group.get('SubnetGroupStatus'),
                    'subnets': [s.get('SubnetIdentifier') for s in group.get('Subnets', [])],
                    'supported_network_types': group.get('SupportedNetworkTypes', []),
                }

                resources.append({
                    'service': 'dms',
                    'type': 'replication-subnet-group',
                    'id': group_id,
                    'arn': f"arn:aws:dms:{region}:{account_id}:subgrp:{group_id}",
                    'name': group_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
