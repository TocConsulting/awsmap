"""
AWS App Runner resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_apprunner_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS App Runner resources: services, connections, auto scaling configurations,
    VPC connectors, observability configurations, VPC ingress connections.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    apprunner = session.client('apprunner', region_name=region)

    # Services
    try:
        paginator = apprunner.get_paginator('list_services')
        for page in paginator.paginate():
            for svc in page.get('ServiceSummaryList', []):
                service_arn = svc['ServiceArn']
                service_name = svc['ServiceName']

                # Get detailed service info
                details = {}
                try:
                    desc_response = apprunner.describe_service(ServiceArn=service_arn)
                    service = desc_response.get('Service', {})
                    details = {
                        'status': service.get('Status'),
                        'service_url': service.get('ServiceUrl'),
                        'source_type': service.get('SourceConfiguration', {}).get('CodeRepository', {}).get('RepositoryUrl') or
                                      service.get('SourceConfiguration', {}).get('ImageRepository', {}).get('ImageIdentifier'),
                        'instance_cpu': service.get('InstanceConfiguration', {}).get('Cpu'),
                        'instance_memory': service.get('InstanceConfiguration', {}).get('Memory'),
                        'instance_role_arn': service.get('InstanceConfiguration', {}).get('InstanceRoleArn'),
                        'auto_scaling_config_arn': service.get('AutoScalingConfigurationSummary', {}).get('AutoScalingConfigurationArn'),
                        'health_check_protocol': service.get('HealthCheckConfiguration', {}).get('Protocol'),
                        'created_at': str(service.get('CreatedAt', '')),
                        'updated_at': str(service.get('UpdatedAt', '')),
                    }
                except Exception:
                    details = {
                        'status': svc.get('Status'),
                        'service_url': svc.get('ServiceUrl'),
                        'created_at': str(svc.get('CreatedAt', '')),
                        'updated_at': str(svc.get('UpdatedAt', '')),
                    }

                # Get tags
                tags = {}
                try:
                    tag_response = apprunner.list_tags_for_resource(ResourceArn=service_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'apprunner',
                    'type': 'service',
                    'id': svc.get('ServiceId', service_name),
                    'arn': service_arn,
                    'name': service_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Connections
    try:
        paginator = apprunner.get_paginator('list_connections')
        for page in paginator.paginate():
            for conn in page.get('ConnectionSummaryList', []):
                conn_arn = conn['ConnectionArn']
                conn_name = conn['ConnectionName']

                # Get tags
                tags = {}
                try:
                    tag_response = apprunner.list_tags_for_resource(ResourceArn=conn_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'apprunner',
                    'type': 'connection',
                    'id': conn_name,
                    'arn': conn_arn,
                    'name': conn_name,
                    'region': region,
                    'details': {
                        'provider_type': conn.get('ProviderType'),
                        'status': conn.get('Status'),
                        'created_at': str(conn.get('CreatedAt', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Auto Scaling Configurations
    try:
        paginator = apprunner.get_paginator('list_auto_scaling_configurations')
        for page in paginator.paginate():
            for config in page.get('AutoScalingConfigurationSummaryList', []):
                config_arn = config['AutoScalingConfigurationArn']
                config_name = config['AutoScalingConfigurationName']

                # Skip default configurations
                if config_name == 'DefaultConfiguration':
                    continue

                # Get detailed config
                details = {
                    'revision': config.get('AutoScalingConfigurationRevision'),
                    'status': config.get('Status'),
                    'created_at': str(config.get('CreatedAt', '')),
                    'has_associated_service': config.get('HasAssociatedService'),
                    'is_default': config.get('IsDefault'),
                }

                try:
                    desc_response = apprunner.describe_auto_scaling_configuration(
                        AutoScalingConfigurationArn=config_arn
                    )
                    asc = desc_response.get('AutoScalingConfiguration', {})
                    details.update({
                        'max_concurrency': asc.get('MaxConcurrency'),
                        'min_size': asc.get('MinSize'),
                        'max_size': asc.get('MaxSize'),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = apprunner.list_tags_for_resource(ResourceArn=config_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'apprunner',
                    'type': 'auto-scaling-configuration',
                    'id': f"{config_name}/{config.get('AutoScalingConfigurationRevision', '1')}",
                    'arn': config_arn,
                    'name': config_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # VPC Connectors
    try:
        paginator = apprunner.get_paginator('list_vpc_connectors')
        for page in paginator.paginate():
            for connector in page.get('VpcConnectors', []):
                connector_arn = connector['VpcConnectorArn']
                connector_name = connector['VpcConnectorName']

                # Get tags
                tags = {}
                try:
                    tag_response = apprunner.list_tags_for_resource(ResourceArn=connector_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'apprunner',
                    'type': 'vpc-connector',
                    'id': connector_name,
                    'arn': connector_arn,
                    'name': connector_name,
                    'region': region,
                    'details': {
                        'revision': connector.get('VpcConnectorRevision'),
                        'status': connector.get('Status'),
                        'subnets': connector.get('Subnets', []),
                        'security_groups': connector.get('SecurityGroups', []),
                        'created_at': str(connector.get('CreatedAt', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Observability Configurations
    try:
        paginator = apprunner.get_paginator('list_observability_configurations')
        for page in paginator.paginate():
            for config in page.get('ObservabilityConfigurationSummaryList', []):
                config_arn = config['ObservabilityConfigurationArn']
                config_name = config['ObservabilityConfigurationName']

                # Get tags
                tags = {}
                try:
                    tag_response = apprunner.list_tags_for_resource(ResourceArn=config_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'apprunner',
                    'type': 'observability-configuration',
                    'id': f"{config_name}/{config.get('ObservabilityConfigurationRevision', '1')}",
                    'arn': config_arn,
                    'name': config_name,
                    'region': region,
                    'details': {
                        'revision': config.get('ObservabilityConfigurationRevision'),
                        'trace_configuration': config.get('TraceConfiguration'),
                        'latest': config.get('Latest'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # VPC Ingress Connections
    try:
        paginator = apprunner.get_paginator('list_vpc_ingress_connections')
        for page in paginator.paginate():
            for conn in page.get('VpcIngressConnectionSummaryList', []):
                conn_arn = conn['VpcIngressConnectionArn']
                conn_name = conn.get('VpcIngressConnectionName', conn_arn.split('/')[-1])

                # Get detailed info
                details = {
                    'service_arn': conn.get('ServiceArn'),
                }

                try:
                    desc_response = apprunner.describe_vpc_ingress_connection(
                        VpcIngressConnectionArn=conn_arn
                    )
                    vic = desc_response.get('VpcIngressConnection', {})
                    details.update({
                        'status': vic.get('Status'),
                        'account_id': vic.get('AccountId'),
                        'domain_name': vic.get('DomainName'),
                        'vpc_id': vic.get('IngressVpcConfiguration', {}).get('VpcId'),
                        'vpc_endpoint_id': vic.get('IngressVpcConfiguration', {}).get('VpcEndpointId'),
                        'created_at': str(vic.get('CreatedAt', '')),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = apprunner.list_tags_for_resource(ResourceArn=conn_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'apprunner',
                    'type': 'vpc-ingress-connection',
                    'id': conn_name,
                    'arn': conn_arn,
                    'name': conn_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
