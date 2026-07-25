"""
Timestream for InfluxDB resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_timestream_influxdb_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Timestream for InfluxDB resources: DB instances, DB parameter groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    client = session.client('timestream-influxdb', region_name=region)

    # DB Instances
    try:
        paginator = client.get_paginator('list_db_instances')
        for page in paginator.paginate():
            for instance in page.get('items', []):
                instance_id = instance['id']
                instance_arn = instance['arn']
                instance_name = instance.get('name', instance_id)

                # Get detailed instance info
                details = {}
                try:
                    detail = client.get_db_instance(identifier=instance_id)
                    details = {
                        'status': detail.get('status'),
                        'endpoint': detail.get('endpoint'),
                        'port': detail.get('port'),
                        'network_type': detail.get('networkType'),
                        'db_instance_type': detail.get('dbInstanceType'),
                        'db_storage_type': detail.get('dbStorageType'),
                        'allocated_storage': detail.get('allocatedStorage'),
                        'deployment_type': detail.get('deploymentType'),
                        'publicly_accessible': detail.get('publiclyAccessible'),
                        'availability_zone': detail.get('availabilityZone'),
                        'secondary_availability_zone': detail.get('secondaryAvailabilityZone'),
                        'vpc_subnet_ids': detail.get('vpcSubnetIds'),
                        'vpc_security_group_ids': detail.get('vpcSecurityGroupIds'),
                        'db_parameter_group_identifier': detail.get('dbParameterGroupIdentifier'),
                        'influx_auth_parameters_secret_arn': detail.get('influxAuthParametersSecretArn'),
                        'log_delivery_configuration': detail.get('logDeliveryConfiguration'),
                    }
                except Exception:
                    details = {
                        'status': instance.get('status'),
                        'endpoint': instance.get('endpoint'),
                        'port': instance.get('port'),
                        'network_type': instance.get('networkType'),
                        'db_instance_type': instance.get('dbInstanceType'),
                        'db_storage_type': instance.get('dbStorageType'),
                        'allocated_storage': instance.get('allocatedStorage'),
                        'deployment_type': instance.get('deploymentType'),
                    }

                # Get tags
                tags = {}
                try:
                    tag_response = client.list_tags_for_resource(resourceArn=instance_arn)
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'timestream-influxdb',
                    'type': 'db-instance',
                    'id': instance_id,
                    'arn': instance_arn,
                    'name': instance_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # DB Parameter Groups (skip AWS default groups that exist in every account)
    try:
        paginator = client.get_paginator('list_db_parameter_groups')
        for page in paginator.paginate():
            for group in page.get('items', []):
                group_id = group['id']
                group_arn = group['arn']
                group_name = group.get('name', group_id)

                # Skip AWS default parameter groups (they have empty ARN)
                if not group_arn:
                    continue

                # Get tags
                tags = {}
                try:
                    tag_response = client.list_tags_for_resource(resourceArn=group_arn)
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'timestream-influxdb',
                    'type': 'db-parameter-group',
                    'id': group_id,
                    'arn': group_arn,
                    'name': group_name,
                    'region': region,
                    'details': {
                        'description': group.get('description'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
