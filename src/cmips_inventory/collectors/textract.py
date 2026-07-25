"""
AWS Textract resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Textract supported regions (from https://docs.aws.amazon.com/general/latest/gr/textract.html)
TEXTRACT_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-south-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-south-2',
}


def collect_textract_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Textract resources: adapters.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in TEXTRACT_REGIONS:
        return []

    resources = []
    textract = session.client('textract', region_name=region)

    # Adapters
    try:
        paginator = textract.get_paginator('list_adapters')
        for page in paginator.paginate():
            for adapter in page.get('Adapters', []):
                adapter_id = adapter['AdapterId']
                adapter_name = adapter.get('AdapterName', adapter_id)

                details = {
                    'creation_time': str(adapter.get('CreationTime', '')),
                    'feature_types': adapter.get('FeatureTypes', []),
                }

                # Get adapter details
                try:
                    adapter_info = textract.get_adapter(AdapterId=adapter_id)
                    details['description'] = adapter_info.get('Description')
                    details['auto_update'] = adapter_info.get('AutoUpdate')
                    tags = adapter_info.get('Tags', {})
                except Exception:
                    tags = {}

                resources.append({
                    'service': 'textract',
                    'type': 'adapter',
                    'id': adapter_id,
                    'arn': f"arn:aws:textract:{region}:{account_id}:adapter/{adapter_id}",
                    'name': adapter_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
