"""
Amazon MQ resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_mq_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Amazon MQ resources: brokers and configurations.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    mq = session.client('mq', region_name=region)

    # Brokers
    try:
        paginator = mq.get_paginator('list_brokers')
        for page in paginator.paginate():
            for broker in page.get('BrokerSummaries', []):
                broker_id = broker['BrokerId']
                broker_name = broker.get('BrokerName', broker_id)
                broker_arn = broker.get('BrokerArn', f"arn:aws:mq:{region}:{account_id}:broker:{broker_id}")

                # Get detailed broker info
                details = {
                    'broker_state': broker.get('BrokerState'),
                    'deployment_mode': broker.get('DeploymentMode'),
                    'engine_type': broker.get('EngineType'),
                    'host_instance_type': broker.get('HostInstanceType'),
                    'created': str(broker.get('Created', '')),
                }

                try:
                    desc_response = mq.describe_broker(BrokerId=broker_id)
                    details.update({
                        'engine_version': desc_response.get('EngineVersion'),
                        'auto_minor_version_upgrade': desc_response.get('AutoMinorVersionUpgrade'),
                        'publicly_accessible': desc_response.get('PubliclyAccessible'),
                        'storage_type': desc_response.get('StorageType'),
                        'authentication_strategy': desc_response.get('AuthenticationStrategy'),
                        'pending_engine_version': desc_response.get('PendingEngineVersion'),
                        'maintenance_window': desc_response.get('MaintenanceWindowStartTime', {}).get('DayOfWeek'),
                        'data_replication_mode': desc_response.get('DataReplicationMode'),
                    })

                    # Get broker endpoints
                    broker_instances = desc_response.get('BrokerInstances', [])
                    if broker_instances:
                        endpoints = []
                        for instance in broker_instances:
                            endpoints.extend(instance.get('Endpoints', []))
                        if endpoints:
                            details['endpoints_count'] = len(endpoints)

                    # Get configuration info
                    config = desc_response.get('Configurations', {})
                    if config.get('Current'):
                        details['configuration_id'] = config['Current'].get('Id')
                        details['configuration_revision'] = config['Current'].get('Revision')

                    # Get security groups and subnets
                    details['security_groups'] = desc_response.get('SecurityGroups', [])
                    details['subnet_ids'] = desc_response.get('SubnetIds', [])

                    # Get users count
                    users = desc_response.get('Users', [])
                    details['users_count'] = len(users)

                    # Get logs config
                    logs = desc_response.get('Logs', {})
                    if logs:
                        details['audit_log_enabled'] = logs.get('Audit', False)
                        details['general_log_enabled'] = logs.get('General', False)

                    # Get encryption config
                    encryption = desc_response.get('EncryptionOptions', {})
                    if encryption:
                        details['kms_key_id'] = encryption.get('KmsKeyId')
                        details['use_aws_owned_key'] = encryption.get('UseAwsOwnedKey')

                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = mq.list_tags(ResourceArn=broker_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'mq',
                    'type': 'broker',
                    'id': broker_id,
                    'arn': broker_arn,
                    'name': broker_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Configurations
    try:
        paginator = mq.get_paginator('list_configurations')
        for page in paginator.paginate():
            for config in page.get('Configurations', []):
                config_id = config['Id']
                config_name = config.get('Name', config_id)
                config_arn = config.get('Arn', f"arn:aws:mq:{region}:{account_id}:configuration:{config_id}")

                details = {
                    'engine_type': config.get('EngineType'),
                    'engine_version': config.get('EngineVersion'),
                    'authentication_strategy': config.get('AuthenticationStrategy'),
                    'created': str(config.get('Created', '')),
                }

                # Get detailed configuration info
                try:
                    desc_response = mq.describe_configuration(ConfigurationId=config_id)
                    details.update({
                        'description': desc_response.get('Description'),
                        'latest_revision': desc_response.get('LatestRevision', {}).get('Revision'),
                        'latest_revision_created': str(desc_response.get('LatestRevision', {}).get('Created', '')),
                        'latest_revision_description': desc_response.get('LatestRevision', {}).get('Description'),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = mq.list_tags(ResourceArn=config_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'mq',
                    'type': 'configuration',
                    'id': config_id,
                    'arn': config_arn,
                    'name': config_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
