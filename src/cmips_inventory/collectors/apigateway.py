"""
API Gateway v1 (REST APIs) resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_apigateway_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect API Gateway v1 resources: REST APIs, stages, API keys, usage plans.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    apigw = session.client('apigateway', region_name=region)

    # REST APIs
    rest_apis = []
    try:
        paginator = apigw.get_paginator('get_rest_apis')
        for page in paginator.paginate():
            for api in page.get('items', []):
                rest_apis.append(api)
                api_id = api['id']
                api_name = api.get('name', api_id)

                # Get tags
                tags = api.get('tags', {})

                resources.append({
                    'service': 'apigateway',
                    'type': 'rest-api',
                    'id': api_id,
                    'arn': f"arn:aws:apigateway:{region}::/restapis/{api_id}",
                    'name': api_name,
                    'region': region,
                    'details': {
                        'description': api.get('description'),
                        'created_date': str(api.get('createdDate', '')),
                        'version': api.get('version'),
                        'api_key_source': api.get('apiKeySource'),
                        'endpoint_configuration': api.get('endpointConfiguration', {}).get('types', []),
                        'disable_execute_api_endpoint': api.get('disableExecuteApiEndpoint'),
                    },
                    'tags': tags
                })

                # Stages for this API
                try:
                    stages_response = apigw.get_stages(restApiId=api_id)
                    for stage in stages_response.get('item', []):
                        stage_name = stage['stageName']

                        stage_tags = stage.get('tags', {})

                        resources.append({
                            'service': 'apigateway',
                            'type': 'stage',
                            'id': f"{api_id}/{stage_name}",
                            'arn': f"arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{stage_name}",
                            'name': f"{api_name}/{stage_name}",
                            'region': region,
                            'details': {
                                'api_id': api_id,
                                'api_name': api_name,
                                'deployment_id': stage.get('deploymentId'),
                                'description': stage.get('description'),
                                'cache_cluster_enabled': stage.get('cacheClusterEnabled'),
                                'cache_cluster_size': stage.get('cacheClusterSize'),
                                'tracing_enabled': stage.get('tracingEnabled'),
                                'web_acl_arn': stage.get('webAclArn'),
                                'created_date': str(stage.get('createdDate', '')),
                                'last_updated_date': str(stage.get('lastUpdatedDate', '')),
                            },
                            'tags': stage_tags
                        })
                except Exception:
                    pass
    except Exception:
        pass

    # API Keys
    try:
        paginator = apigw.get_paginator('get_api_keys')
        for page in paginator.paginate():
            for key in page.get('items', []):
                key_id = key['id']
                key_name = key.get('name', key_id)

                tags = key.get('tags', {})

                resources.append({
                    'service': 'apigateway',
                    'type': 'api-key',
                    'id': key_id,
                    'arn': f"arn:aws:apigateway:{region}::/apikeys/{key_id}",
                    'name': key_name,
                    'region': region,
                    'details': {
                        'description': key.get('description'),
                        'enabled': key.get('enabled'),
                        'created_date': str(key.get('createdDate', '')),
                        'last_updated_date': str(key.get('lastUpdatedDate', '')),
                        'stage_keys': key.get('stageKeys', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Usage Plans
    try:
        paginator = apigw.get_paginator('get_usage_plans')
        for page in paginator.paginate():
            for plan in page.get('items', []):
                plan_id = plan['id']
                plan_name = plan.get('name', plan_id)

                tags = plan.get('tags', {})

                resources.append({
                    'service': 'apigateway',
                    'type': 'usage-plan',
                    'id': plan_id,
                    'arn': f"arn:aws:apigateway:{region}::/usageplans/{plan_id}",
                    'name': plan_name,
                    'region': region,
                    'details': {
                        'description': plan.get('description'),
                        'api_stages': plan.get('apiStages', []),
                        'throttle': plan.get('throttle'),
                        'quota': plan.get('quota'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # VPC Links
    try:
        paginator = apigw.get_paginator('get_vpc_links')
        for page in paginator.paginate():
            for vpc_link in page.get('items', []):
                vl_id = vpc_link['id']
                vl_name = vpc_link.get('name', vl_id)

                tags = vpc_link.get('tags', {})

                resources.append({
                    'service': 'apigateway',
                    'type': 'vpc-link',
                    'id': vl_id,
                    'arn': f"arn:aws:apigateway:{region}::/vpclinks/{vl_id}",
                    'name': vl_name,
                    'region': region,
                    'details': {
                        'description': vpc_link.get('description'),
                        'status': vpc_link.get('status'),
                        'status_message': vpc_link.get('statusMessage'),
                        'target_arns': vpc_link.get('targetArns', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
