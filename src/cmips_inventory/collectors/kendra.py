"""
AWS Kendra resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Kendra supported regions (from https://docs.aws.amazon.com/general/latest/gr/kendra.html)
KENDRA_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
    'ca-central-1',
    'eu-west-1', 'eu-west-2',
}


def collect_kendra_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Kendra resources: indexes and data sources.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in KENDRA_REGIONS:
        return []

    resources = []
    kendra = session.client('kendra', region_name=region)

    # Indexes
    try:
        paginator = kendra.get_paginator('list_indices')
        for page in paginator.paginate():
            for index in page.get('IndexConfigurationSummaryItems', []):
                index_id = index['Id']
                index_name = index.get('Name', index_id)

                details = {
                    'status': index.get('Status'),
                    'edition': index.get('Edition'),
                    'created_at': str(index.get('CreatedAt', '')),
                    'updated_at': str(index.get('UpdatedAt', '')),
                }

                resources.append({
                    'service': 'kendra',
                    'type': 'index',
                    'id': index_id,
                    'arn': f"arn:aws:kendra:{region}:{account_id}:index/{index_id}",
                    'name': index_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })

                # Data Sources for this index
                try:
                    ds_paginator = kendra.get_paginator('list_data_sources')
                    for ds_page in ds_paginator.paginate(IndexId=index_id):
                        for ds in ds_page.get('SummaryItems', []):
                            ds_id = ds['Id']
                            ds_name = ds.get('Name', ds_id)

                            ds_details = {
                                'index_id': index_id,
                                'type': ds.get('Type'),
                                'status': ds.get('Status'),
                                'created_at': str(ds.get('CreatedAt', '')),
                                'updated_at': str(ds.get('UpdatedAt', '')),
                                'language_code': ds.get('LanguageCode'),
                            }

                            resources.append({
                                'service': 'kendra',
                                'type': 'data-source',
                                'id': ds_id,
                                'arn': f"arn:aws:kendra:{region}:{account_id}:index/{index_id}/data-source/{ds_id}",
                                'name': ds_name,
                                'region': region,
                                'details': ds_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
