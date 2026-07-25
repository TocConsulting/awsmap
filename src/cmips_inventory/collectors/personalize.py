"""
AWS Personalize resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Personalize supported regions (from https://docs.aws.amazon.com/general/latest/gr/personalize.html)
PERSONALIZE_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1',
}


def collect_personalize_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Personalize resources: dataset groups, datasets, solutions, and campaigns.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in PERSONALIZE_REGIONS:
        return []

    resources = []
    personalize = session.client('personalize', region_name=region)

    # Dataset Groups
    try:
        paginator = personalize.get_paginator('list_dataset_groups')
        for page in paginator.paginate():
            for dg in page.get('datasetGroups', []):
                dg_arn = dg['datasetGroupArn']
                dg_name = dg.get('name', dg_arn.split('/')[-1])

                details = {
                    'status': dg.get('status'),
                    'creation_date_time': str(dg.get('creationDateTime', '')),
                    'last_updated_date_time': str(dg.get('lastUpdatedDateTime', '')),
                    'failure_reason': dg.get('failureReason'),
                    'domain': dg.get('domain'),
                }

                resources.append({
                    'service': 'personalize',
                    'type': 'dataset-group',
                    'id': dg_name,
                    'arn': dg_arn,
                    'name': dg_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Datasets
    try:
        paginator = personalize.get_paginator('list_datasets')
        for page in paginator.paginate():
            for ds in page.get('datasets', []):
                ds_arn = ds['datasetArn']
                ds_name = ds.get('name', ds_arn.split('/')[-1])

                details = {
                    'dataset_type': ds.get('datasetType'),
                    'status': ds.get('status'),
                    'creation_date_time': str(ds.get('creationDateTime', '')),
                    'last_updated_date_time': str(ds.get('lastUpdatedDateTime', '')),
                }

                resources.append({
                    'service': 'personalize',
                    'type': 'dataset',
                    'id': ds_name,
                    'arn': ds_arn,
                    'name': ds_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Solutions
    try:
        paginator = personalize.get_paginator('list_solutions')
        for page in paginator.paginate():
            for solution in page.get('solutions', []):
                solution_arn = solution['solutionArn']
                solution_name = solution.get('name', solution_arn.split('/')[-1])

                details = {
                    'status': solution.get('status'),
                    'creation_date_time': str(solution.get('creationDateTime', '')),
                    'last_updated_date_time': str(solution.get('lastUpdatedDateTime', '')),
                    'dataset_group_arn': solution.get('datasetGroupArn'),
                    'recipe_arn': solution.get('recipeArn'),
                }

                resources.append({
                    'service': 'personalize',
                    'type': 'solution',
                    'id': solution_name,
                    'arn': solution_arn,
                    'name': solution_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Campaigns
    try:
        paginator = personalize.get_paginator('list_campaigns')
        for page in paginator.paginate():
            for campaign in page.get('campaigns', []):
                campaign_arn = campaign['campaignArn']
                campaign_name = campaign.get('name', campaign_arn.split('/')[-1])

                details = {
                    'status': campaign.get('status'),
                    'creation_date_time': str(campaign.get('creationDateTime', '')),
                    'last_updated_date_time': str(campaign.get('lastUpdatedDateTime', '')),
                    'failure_reason': campaign.get('failureReason'),
                }

                resources.append({
                    'service': 'personalize',
                    'type': 'campaign',
                    'id': campaign_name,
                    'arn': campaign_arn,
                    'name': campaign_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
