"""
Lake Formation resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_lakeformation_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Lake Formation resources: data lake settings, resources, LF-tags.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    lf = session.client('lakeformation', region_name=region)

    # Note: data-lake-settings skipped - exists by default in every AWS account/region

    # Lake Formation Registered Resources
    try:
        paginator = lf.get_paginator('list_resources')
        for page in paginator.paginate():
            for resource in page.get('ResourceInfoList', []):
                resource_arn = resource.get('ResourceArn')
                if not resource_arn:
                    continue

                resources.append({
                    'service': 'lakeformation',
                    'type': 'registered-resource',
                    'id': resource_arn.split(':')[-1] if ':' in resource_arn else resource_arn,
                    'arn': resource_arn,
                    'name': resource_arn.split('/')[-1] if '/' in resource_arn else resource_arn.split(':')[-1],
                    'region': region,
                    'details': {
                        'role_arn': resource.get('RoleArn'),
                        'last_modified': str(resource.get('LastModified', '')),
                        'with_federation': resource.get('WithFederation'),
                        'hybrid_access_enabled': resource.get('HybridAccessEnabled'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # LF-Tags
    try:
        response = lf.list_lf_tags()
        for lf_tag in response.get('LFTags', []):
            tag_key = lf_tag['TagKey']
            catalog_id = lf_tag.get('CatalogId', account_id)

            resources.append({
                'service': 'lakeformation',
                'type': 'lf-tag',
                'id': tag_key,
                'arn': f"arn:aws:lakeformation:{region}:{catalog_id}:tag/{tag_key}",
                'name': tag_key,
                'region': region,
                'details': {
                    'catalog_id': catalog_id,
                    'tag_values': lf_tag.get('TagValues', []),
                },
                'tags': {}
            })
    except Exception:
        pass

    # Data Cells Filters
    try:
        paginator = lf.get_paginator('list_data_cells_filter')
        for page in paginator.paginate():
            for dcf in page.get('DataCellsFilters', []):
                filter_name = dcf['Name']
                table_catalog_id = dcf.get('TableCatalogId', account_id)
                database_name = dcf.get('DatabaseName')
                table_name = dcf.get('TableName')

                resources.append({
                    'service': 'lakeformation',
                    'type': 'data-cells-filter',
                    'id': f"{database_name}/{table_name}/{filter_name}",
                    'arn': f"arn:aws:lakeformation:{region}:{table_catalog_id}:datacellsfilter/{database_name}/{table_name}/{filter_name}",
                    'name': filter_name,
                    'region': region,
                    'details': {
                        'table_catalog_id': table_catalog_id,
                        'database_name': database_name,
                        'table_name': table_name,
                        'column_names': dcf.get('ColumnNames', []),
                        'column_wildcard': bool(dcf.get('ColumnWildcard')),
                        'row_filter': bool(dcf.get('RowFilter')),
                        'version_id': dcf.get('VersionId'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
