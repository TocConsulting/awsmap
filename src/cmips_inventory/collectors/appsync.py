"""
AWS AppSync resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_appsync_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS AppSync resources: GraphQL APIs, data sources, functions,
    resolvers, API keys, and domain names.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    appsync = session.client('appsync', region_name=region)

    # GraphQL APIs
    api_ids = []
    try:
        paginator = appsync.get_paginator('list_graphql_apis')
        for page in paginator.paginate():
            for api in page.get('graphqlApis', []):
                api_id = api['apiId']
                api_ids.append(api_id)
                api_arn = api.get('arn', f"arn:aws:appsync:{region}:{account_id}:apis/{api_id}")
                api_name = api.get('name', api_id)

                details = {
                    'api_type': api.get('apiType'),
                    'authentication_type': api.get('authenticationType'),
                    'uris': api.get('uris', {}),
                    'xray_enabled': api.get('xrayEnabled'),
                    'waf_web_acl_arn': api.get('wafWebAclArn'),
                    'visibility': api.get('visibility'),
                    'owner': api.get('owner'),
                    'owner_contact': api.get('ownerContact'),
                    'introspection_config': api.get('introspectionConfig'),
                    'query_depth_limit': api.get('queryDepthLimit'),
                    'resolver_count_limit': api.get('resolverCountLimit'),
                    'enhanced_metrics_config': api.get('enhancedMetricsConfig'),
                }

                # Get additional auth providers
                additional_auth = api.get('additionalAuthenticationProviders', [])
                if additional_auth:
                    details['additional_auth_types'] = [a.get('authenticationType') for a in additional_auth]

                # Get log config
                log_config = api.get('logConfig', {})
                if log_config:
                    details['cloudwatch_logs_role_arn'] = log_config.get('cloudWatchLogsRoleArn')
                    details['field_log_level'] = log_config.get('fieldLogLevel')
                    details['exclude_verbose_content'] = log_config.get('excludeVerboseContent')

                # Get user pool config
                user_pool = api.get('userPoolConfig', {})
                if user_pool:
                    details['user_pool_id'] = user_pool.get('userPoolId')
                    details['user_pool_region'] = user_pool.get('awsRegion')

                # Get lambda authorizer config
                lambda_auth = api.get('lambdaAuthorizerConfig', {})
                if lambda_auth:
                    details['lambda_authorizer_uri'] = lambda_auth.get('authorizerUri')

                # Get cache info
                try:
                    cache_response = appsync.get_api_cache(apiId=api_id)
                    cache = cache_response.get('apiCache', {})
                    if cache:
                        details['cache_type'] = cache.get('type')
                        details['cache_ttl'] = cache.get('ttl')
                        details['cache_status'] = cache.get('status')
                        details['cache_at_rest_encryption'] = cache.get('atRestEncryptionEnabled')
                        details['cache_transit_encryption'] = cache.get('transitEncryptionEnabled')
                except Exception:
                    pass

                # Get tags
                tags = api.get('tags', {})

                resources.append({
                    'service': 'appsync',
                    'type': 'graphql-api',
                    'id': api_id,
                    'arn': api_arn,
                    'name': api_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Data Sources (per API)
    for api_id in api_ids:
        try:
            paginator = appsync.get_paginator('list_data_sources')
            for page in paginator.paginate(apiId=api_id):
                for ds in page.get('dataSources', []):
                    ds_name = ds['name']
                    ds_arn = ds.get('dataSourceArn', f"arn:aws:appsync:{region}:{account_id}:apis/{api_id}/datasources/{ds_name}")

                    details = {
                        'api_id': api_id,
                        'type': ds.get('type'),
                        'description': ds.get('description'),
                        'service_role_arn': ds.get('serviceRoleArn'),
                    }

                    # Type-specific config
                    ds_type = ds.get('type', '')
                    if ds_type == 'AWS_LAMBDA':
                        lambda_config = ds.get('lambdaConfig', {})
                        details['lambda_function_arn'] = lambda_config.get('lambdaFunctionArn')
                    elif ds_type == 'AMAZON_DYNAMODB':
                        dynamodb_config = ds.get('dynamodbConfig', {})
                        details['dynamodb_table_name'] = dynamodb_config.get('tableName')
                        details['dynamodb_region'] = dynamodb_config.get('awsRegion')
                        details['dynamodb_use_caller_credentials'] = dynamodb_config.get('useCallerCredentials')
                    elif ds_type == 'AMAZON_ELASTICSEARCH' or ds_type == 'AMAZON_OPENSEARCH_SERVICE':
                        es_config = ds.get('elasticsearchConfig') or ds.get('openSearchServiceConfig', {})
                        details['elasticsearch_endpoint'] = es_config.get('endpoint')
                        details['elasticsearch_region'] = es_config.get('awsRegion')
                    elif ds_type == 'HTTP':
                        http_config = ds.get('httpConfig', {})
                        details['http_endpoint'] = http_config.get('endpoint')
                    elif ds_type == 'RELATIONAL_DATABASE':
                        rds_config = ds.get('relationalDatabaseConfig', {})
                        details['rds_source_type'] = rds_config.get('relationalDatabaseSourceType')
                        rds_http = rds_config.get('rdsHttpEndpointConfig', {})
                        details['rds_cluster_arn'] = rds_http.get('dbClusterIdentifier')
                        details['rds_database_name'] = rds_http.get('databaseName')
                    elif ds_type == 'AMAZON_EVENTBRIDGE':
                        eb_config = ds.get('eventBridgeConfig', {})
                        details['eventbridge_bus_arn'] = eb_config.get('eventBusArn')

                    resources.append({
                        'service': 'appsync',
                        'type': 'data-source',
                        'id': f"{api_id}/{ds_name}",
                        'arn': ds_arn,
                        'name': ds_name,
                        'region': region,
                        'details': details,
                        'tags': {}
                    })
        except Exception:
            pass

    # Functions (per API)
    for api_id in api_ids:
        try:
            paginator = appsync.get_paginator('list_functions')
            for page in paginator.paginate(apiId=api_id):
                for func in page.get('functions', []):
                    func_id = func['functionId']
                    func_name = func.get('name', func_id)
                    func_arn = func.get('functionArn', f"arn:aws:appsync:{region}:{account_id}:apis/{api_id}/functions/{func_id}")

                    details = {
                        'api_id': api_id,
                        'description': func.get('description'),
                        'data_source_name': func.get('dataSourceName'),
                        'function_version': func.get('functionVersion'),
                        'max_batch_size': func.get('maxBatchSize'),
                        'runtime_name': func.get('runtime', {}).get('name'),
                        'runtime_version': func.get('runtime', {}).get('runtimeVersion'),
                    }

                    resources.append({
                        'service': 'appsync',
                        'type': 'function',
                        'id': f"{api_id}/{func_id}",
                        'arn': func_arn,
                        'name': func_name,
                        'region': region,
                        'details': details,
                        'tags': {}
                    })
        except Exception:
            pass

    # API Keys (per API)
    for api_id in api_ids:
        try:
            paginator = appsync.get_paginator('list_api_keys')
            for page in paginator.paginate(apiId=api_id):
                for key in page.get('apiKeys', []):
                    key_id = key['id']

                    details = {
                        'api_id': api_id,
                        'description': key.get('description'),
                        'expires': key.get('expires'),
                        'deletes': key.get('deletes'),
                    }

                    resources.append({
                        'service': 'appsync',
                        'type': 'api-key',
                        'id': f"{api_id}/{key_id}",
                        'arn': f"arn:aws:appsync:{region}:{account_id}:apis/{api_id}/apikeys/{key_id}",
                        'name': key.get('description', key_id),
                        'region': region,
                        'details': details,
                        'tags': {}
                    })
        except Exception:
            pass

    # Domain Names
    try:
        paginator = appsync.get_paginator('list_domain_names')
        for page in paginator.paginate():
            for domain in page.get('domainNameConfigs', []):
                domain_name = domain['domainName']

                details = {
                    'appsync_domain_name': domain.get('appsyncDomainName'),
                    'certificate_arn': domain.get('certificateArn'),
                    'description': domain.get('description'),
                    'hosted_zone_id': domain.get('hostedZoneId'),
                }

                resources.append({
                    'service': 'appsync',
                    'type': 'domain-name',
                    'id': domain_name,
                    'arn': f"arn:aws:appsync:{region}:{account_id}:domainnames/{domain_name}",
                    'name': domain_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
