"""
QuickSight resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

# QuickSight/QuickSuite supported regions
# https://docs.aws.amazon.com/quicksuite/latest/userguide/regions.html
QUICKSIGHT_REGIONS = {
    # US
    'us-east-1', 'us-east-2', 'us-west-2',
    # Europe
    'eu-central-1', 'eu-central-2', 'eu-west-1', 'eu-west-2', 'eu-west-3',
    'eu-south-1', 'eu-south-2', 'eu-north-1',
    # Asia Pacific
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3',
    'ap-northeast-1', 'ap-northeast-2',
    # Other
    'ca-central-1', 'sa-east-1', 'af-south-1', 'il-central-1', 'me-central-1',
}


def collect_quicksight_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect QuickSight resources: dashboards, data sets, data sources, analyses.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions to avoid timeouts
    if region and region not in QUICKSIGHT_REGIONS:
        return []

    resources = []
    quicksight = session.client('quicksight', region_name=region)

    # QuickSight Dashboards
    try:
        paginator = quicksight.get_paginator('list_dashboards')
        for page in paginator.paginate(AwsAccountId=account_id):
            for dashboard in page.get('DashboardSummaryList', []):
                dashboard_id = dashboard['DashboardId']
                dashboard_arn = dashboard['Arn']

                # Get tags
                tags = {}
                try:
                    tag_response = quicksight.list_tags_for_resource(ResourceArn=dashboard_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'quicksight',
                    'type': 'dashboard',
                    'id': dashboard_id,
                    'arn': dashboard_arn,
                    'name': dashboard.get('Name', dashboard_id),
                    'region': region,
                    'details': {
                        'published_version_number': dashboard.get('PublishedVersionNumber'),
                        'created_time': str(dashboard.get('CreatedTime', '')),
                        'last_updated_time': str(dashboard.get('LastUpdatedTime', '')),
                        'last_published_time': str(dashboard.get('LastPublishedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # QuickSight Data Sets
    try:
        paginator = quicksight.get_paginator('list_data_sets')
        for page in paginator.paginate(AwsAccountId=account_id):
            for dataset in page.get('DataSetSummaries', []):
                dataset_id = dataset['DataSetId']
                dataset_arn = dataset['Arn']

                # Get tags
                tags = {}
                try:
                    tag_response = quicksight.list_tags_for_resource(ResourceArn=dataset_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'quicksight',
                    'type': 'data-set',
                    'id': dataset_id,
                    'arn': dataset_arn,
                    'name': dataset.get('Name', dataset_id),
                    'region': region,
                    'details': {
                        'import_mode': dataset.get('ImportMode'),
                        'created_time': str(dataset.get('CreatedTime', '')),
                        'last_updated_time': str(dataset.get('LastUpdatedTime', '')),
                        'row_level_permission_data_set': bool(dataset.get('RowLevelPermissionDataSet')),
                        'row_level_permission_tag_configuration_applied': dataset.get('RowLevelPermissionTagConfigurationApplied'),
                        'column_level_permission_rules_applied': dataset.get('ColumnLevelPermissionRulesApplied'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # QuickSight Data Sources
    try:
        paginator = quicksight.get_paginator('list_data_sources')
        for page in paginator.paginate(AwsAccountId=account_id):
            for datasource in page.get('DataSources', []):
                datasource_id = datasource['DataSourceId']
                datasource_arn = datasource['Arn']

                # Get tags
                tags = {}
                try:
                    tag_response = quicksight.list_tags_for_resource(ResourceArn=datasource_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'quicksight',
                    'type': 'data-source',
                    'id': datasource_id,
                    'arn': datasource_arn,
                    'name': datasource.get('Name', datasource_id),
                    'region': region,
                    'details': {
                        'type': datasource.get('Type'),
                        'status': datasource.get('Status'),
                        'created_time': str(datasource.get('CreatedTime', '')),
                        'last_updated_time': str(datasource.get('LastUpdatedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # QuickSight Analyses
    try:
        paginator = quicksight.get_paginator('list_analyses')
        for page in paginator.paginate(AwsAccountId=account_id):
            for analysis in page.get('AnalysisSummaryList', []):
                analysis_id = analysis['AnalysisId']
                analysis_arn = analysis['Arn']

                # Get tags
                tags = {}
                try:
                    tag_response = quicksight.list_tags_for_resource(ResourceArn=analysis_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'quicksight',
                    'type': 'analysis',
                    'id': analysis_id,
                    'arn': analysis_arn,
                    'name': analysis.get('Name', analysis_id),
                    'region': region,
                    'details': {
                        'status': analysis.get('Status'),
                        'created_time': str(analysis.get('CreatedTime', '')),
                        'last_updated_time': str(analysis.get('LastUpdatedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
