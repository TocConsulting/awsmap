"""
MSK (Managed Streaming for Apache Kafka) resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_kafka_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect MSK resources: clusters, configurations, serverless clusters.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    kafka = session.client('kafka', region_name=region)

    # MSK Clusters (Provisioned)
    try:
        paginator = kafka.get_paginator('list_clusters_v2')
        for page in paginator.paginate():
            for cluster_info in page.get('ClusterInfoList', []):
                cluster_arn = cluster_info['ClusterArn']
                cluster_name = cluster_info['ClusterName']
                cluster_type = cluster_info.get('ClusterType', 'PROVISIONED')

                # Get tags
                tags = cluster_info.get('Tags', {})

                if cluster_type == 'PROVISIONED':
                    provisioned = cluster_info.get('Provisioned', {})
                    resources.append({
                        'service': 'kafka',
                        'type': 'cluster',
                        'id': cluster_arn.split('/')[-1],
                        'arn': cluster_arn,
                        'name': cluster_name,
                        'region': region,
                        'details': {
                            'state': cluster_info.get('State'),
                            'cluster_type': cluster_type,
                            'creation_time': str(cluster_info.get('CreationTime', '')),
                            'broker_node_group_info': provisioned.get('BrokerNodeGroupInfo'),
                            'number_of_broker_nodes': provisioned.get('NumberOfBrokerNodes'),
                            'kafka_version': provisioned.get('CurrentBrokerSoftwareInfo', {}).get('KafkaVersion'),
                            'enhanced_monitoring': provisioned.get('EnhancedMonitoring'),
                            'encryption_at_rest_kms_key_arn': provisioned.get('EncryptionInfo', {}).get('EncryptionAtRest', {}).get('DataVolumeKMSKeyId'),
                            'client_authentication': bool(provisioned.get('ClientAuthentication')),
                            'zookeeper_connect_string': provisioned.get('ZookeeperConnectString'),
                            'storage_mode': provisioned.get('StorageMode'),
                        },
                        'tags': tags
                    })
                elif cluster_type == 'SERVERLESS':
                    serverless = cluster_info.get('Serverless', {})
                    resources.append({
                        'service': 'kafka',
                        'type': 'serverless-cluster',
                        'id': cluster_arn.split('/')[-1],
                        'arn': cluster_arn,
                        'name': cluster_name,
                        'region': region,
                        'details': {
                            'state': cluster_info.get('State'),
                            'cluster_type': cluster_type,
                            'creation_time': str(cluster_info.get('CreationTime', '')),
                            'vpc_configs': serverless.get('VpcConfigs', []),
                            'client_authentication': serverless.get('ClientAuthentication'),
                        },
                        'tags': tags
                    })
    except Exception:
        pass

    # MSK Configurations
    try:
        paginator = kafka.get_paginator('list_configurations')
        for page in paginator.paginate():
            for config in page.get('Configurations', []):
                config_arn = config['Arn']
                config_name = config['Name']

                resources.append({
                    'service': 'kafka',
                    'type': 'configuration',
                    'id': config_arn.split('/')[-1],
                    'arn': config_arn,
                    'name': config_name,
                    'region': region,
                    'details': {
                        'description': config.get('Description'),
                        'state': config.get('State'),
                        'kafka_versions': config.get('KafkaVersions', []),
                        'latest_revision': config.get('LatestRevision', {}).get('Revision'),
                        'creation_time': str(config.get('CreationTime', '')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # MSK Connect Connectors
    try:
        kafkaconnect = session.client('kafkaconnect', region_name=region)
        paginator = kafkaconnect.get_paginator('list_connectors')
        for page in paginator.paginate():
            for connector in page.get('connectors', []):
                connector_arn = connector['connectorArn']
                connector_name = connector['connectorName']

                resources.append({
                    'service': 'kafka',
                    'type': 'connector',
                    'id': connector_arn.split('/')[-1],
                    'arn': connector_arn,
                    'name': connector_name,
                    'region': region,
                    'details': {
                        'connector_state': connector.get('connectorState'),
                        'kafka_cluster_client_authentication_type': connector.get('kafkaClusterClientAuthentication', {}).get('authenticationType'),
                        'kafka_cluster_encryption_in_transit_type': connector.get('kafkaClusterEncryptionInTransit', {}).get('encryptionType'),
                        'kafka_connect_version': connector.get('kafkaConnectVersion'),
                        'creation_time': str(connector.get('creationTime', '')),
                        'current_version': connector.get('currentVersion'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
