"""
API Gateway v2 (HTTP/WebSocket APIs) resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_apigatewayv2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect API Gateway v2 resources: HTTP APIs, WebSocket APIs, stages.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    apigwv2 = session.client('apigatewayv2', region_name=region)

    # HTTP and WebSocket APIs
    try:
        paginator = apigwv2.get_paginator('get_apis')
        for page in paginator.paginate():
            for api in page.get('Items', []):
                api_id = api['ApiId']
                api_name = api.get('Name', api_id)

                # Get tags
                tags = api.get('Tags', {})

                api_type = api.get('ProtocolType', 'HTTP')

                resources.append({
                    'service': 'apigatewayv2',
                    'type': f"{api_type.lower()}-api",
                    'id': api_id,
                    'arn': f"arn:aws:apigateway:{region}::/apis/{api_id}",
                    'name': api_name,
                    'region': region,
                    'details': {
                        'protocol_type': api_type,
                        'description': api.get('Description'),
                        'api_endpoint': api.get('ApiEndpoint'),
                        'created_date': str(api.get('CreatedDate', '')),
                        'version': api.get('Version'),
                        'route_selection_expression': api.get('RouteSelectionExpression'),
                        'api_gateway_managed': api.get('ApiGatewayManaged'),
                        'disable_execute_api_endpoint': api.get('DisableExecuteApiEndpoint'),
                    },
                    'tags': tags
                })

                # Stages for this API
                try:
                    stages_paginator = apigwv2.get_paginator('get_stages')
                    for stages_page in stages_paginator.paginate(ApiId=api_id):
                        for stage in stages_page.get('Items', []):
                            stage_name = stage['StageName']

                            stage_tags = stage.get('Tags', {})

                            resources.append({
                                'service': 'apigatewayv2',
                                'type': 'stage',
                                'id': f"{api_id}/{stage_name}",
                                'arn': f"arn:aws:apigateway:{region}::/apis/{api_id}/stages/{stage_name}",
                                'name': f"{api_name}/{stage_name}",
                                'region': region,
                                'details': {
                                    'api_id': api_id,
                                    'api_name': api_name,
                                    'deployment_id': stage.get('DeploymentId'),
                                    'description': stage.get('Description'),
                                    'auto_deploy': stage.get('AutoDeploy'),
                                    'created_date': str(stage.get('CreatedDate', '')),
                                    'last_updated_date': str(stage.get('LastUpdatedDate', '')),
                                    'default_route_settings': stage.get('DefaultRouteSettings'),
                                },
                                'tags': stage_tags
                            })
                except Exception:
                    pass
    except Exception:
        pass

    # VPC Links (v2)
    try:
        paginator = apigwv2.get_paginator('get_vpc_links')
        for page in paginator.paginate():
            for vpc_link in page.get('Items', []):
                vl_id = vpc_link['VpcLinkId']
                vl_name = vpc_link.get('Name', vl_id)

                tags = vpc_link.get('Tags', {})

                resources.append({
                    'service': 'apigatewayv2',
                    'type': 'vpc-link',
                    'id': vl_id,
                    'arn': f"arn:aws:apigateway:{region}::/vpclinks/{vl_id}",
                    'name': vl_name,
                    'region': region,
                    'details': {
                        'status': vpc_link.get('VpcLinkStatus'),
                        'status_message': vpc_link.get('VpcLinkStatusMessage'),
                        'vpc_link_version': vpc_link.get('VpcLinkVersion'),
                        'subnet_ids': vpc_link.get('SubnetIds', []),
                        'security_group_ids': vpc_link.get('SecurityGroupIds', []),
                        'created_date': str(vpc_link.get('CreatedDate', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Domain Names
    try:
        paginator = apigwv2.get_paginator('get_domain_names')
        for page in paginator.paginate():
            for domain in page.get('Items', []):
                domain_name = domain['DomainName']

                tags = domain.get('Tags', {})

                resources.append({
                    'service': 'apigatewayv2',
                    'type': 'domain-name',
                    'id': domain_name,
                    'arn': f"arn:aws:apigateway:{region}::/domainnames/{domain_name}",
                    'name': domain_name,
                    'region': region,
                    'details': {
                        'domain_name_configurations': domain.get('DomainNameConfigurations', []),
                        'mutual_tls_authentication': domain.get('MutualTlsAuthentication'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
