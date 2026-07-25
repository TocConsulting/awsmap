"""
Athena resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_athena_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Athena resources: workgroups, data catalogs, named queries.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    athena = session.client('athena', region_name=region)

    # Workgroups
    try:
        paginator = athena.get_paginator('list_work_groups')
        for page in paginator.paginate():
            for wg in page.get('WorkGroups', []):
                wg_name = wg['Name']

                try:
                    # Get workgroup details
                    wg_response = athena.get_work_group(WorkGroup=wg_name)
                    wg_detail = wg_response.get('WorkGroup', {})

                    wg_arn = f"arn:aws:athena:{region}:{account_id}:workgroup/{wg_name}"

                    # Get tags
                    tags = {}
                    try:
                        tag_response = athena.list_tags_for_resource(ResourceARN=wg_arn)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    config = wg_detail.get('Configuration', {})

                    resources.append({
                        'service': 'athena',
                        'type': 'workgroup',
                        'id': wg_name,
                        'arn': wg_arn,
                        'name': wg_name,
                        'region': region,
                        'details': {
                            'state': wg_detail.get('State'),
                            'description': wg_detail.get('Description'),
                            'creation_time': str(wg_detail.get('CreationTime', '')),
                            'engine_version': config.get('EngineVersion', {}).get('SelectedEngineVersion'),
                            'result_output_location': config.get('ResultConfiguration', {}).get('OutputLocation'),
                            'enforce_workgroup_configuration': config.get('EnforceWorkGroupConfiguration'),
                            'publish_cloudwatch_metrics_enabled': config.get('PublishCloudWatchMetricsEnabled'),
                            'bytes_scanned_cutoff_per_query': config.get('BytesScannedCutoffPerQuery'),
                            'requester_pays_enabled': config.get('RequesterPaysEnabled'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # Data Catalogs (non-default)
    try:
        paginator = athena.get_paginator('list_data_catalogs')
        for page in paginator.paginate():
            for catalog in page.get('DataCatalogsSummary', []):
                catalog_name = catalog['CatalogName']

                # Skip the default AWS Glue catalog
                if catalog_name == 'AwsDataCatalog':
                    continue

                try:
                    # Get catalog details
                    catalog_response = athena.get_data_catalog(Name=catalog_name)
                    catalog_detail = catalog_response.get('DataCatalog', {})

                    catalog_arn = f"arn:aws:athena:{region}:{account_id}:datacatalog/{catalog_name}"

                    # Get tags
                    tags = {}
                    try:
                        tag_response = athena.list_tags_for_resource(ResourceARN=catalog_arn)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'athena',
                        'type': 'data-catalog',
                        'id': catalog_name,
                        'arn': catalog_arn,
                        'name': catalog_name,
                        'region': region,
                        'details': {
                            'type': catalog_detail.get('Type'),
                            'description': catalog_detail.get('Description'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # Named Queries
    try:
        paginator = athena.get_paginator('list_named_queries')
        for page in paginator.paginate():
            query_ids = page.get('NamedQueryIds', [])

            # Batch get named queries (max 50 at a time)
            for i in range(0, len(query_ids), 50):
                batch = query_ids[i:i+50]
                try:
                    response = athena.batch_get_named_query(NamedQueryIds=batch)
                    for query in response.get('NamedQueries', []):
                        query_id = query['NamedQueryId']
                        query_name = query['Name']

                        resources.append({
                            'service': 'athena',
                            'type': 'named-query',
                            'id': query_id,
                            'arn': f"arn:aws:athena:{region}:{account_id}:namedquery/{query_id}",
                            'name': query_name,
                            'region': region,
                            'details': {
                                'database': query.get('Database'),
                                'description': query.get('Description'),
                                'workgroup': query.get('WorkGroup'),
                            },
                            'tags': {}
                        })
                except Exception:
                    pass
    except Exception:
        pass

    # Note: Prepared statements skipped for performance (requires N×M API calls per workgroup)

    return resources
