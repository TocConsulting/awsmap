"""
AWS Translate resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Translate supported regions (from https://docs.aws.amazon.com/general/latest/gr/translate-service.html)
TRANSLATE_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-east-1', 'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1',
}


def collect_translate_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Translate resources: terminologies and parallel data.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in TRANSLATE_REGIONS:
        return []

    resources = []
    translate = session.client('translate', region_name=region)

    # Terminologies
    try:
        paginator = translate.get_paginator('list_terminologies')
        for page in paginator.paginate():
            for term in page.get('TerminologyPropertiesList', []):
                term_name = term['Name']
                term_arn = term.get('Arn', '')

                details = {
                    'source_language_code': term.get('SourceLanguageCode'),
                    'target_language_codes': term.get('TargetLanguageCodes', []),
                    'description': term.get('Description'),
                    'term_count': term.get('TermCount'),
                    'size_bytes': term.get('SizeBytes'),
                    'directionality': term.get('Directionality'),
                    'format': term.get('Format'),
                    'created_at': str(term.get('CreatedAt', '')),
                    'last_updated_at': str(term.get('LastUpdatedAt', '')),
                }

                resources.append({
                    'service': 'translate',
                    'type': 'terminology',
                    'id': term_name,
                    'arn': term_arn,
                    'name': term_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Parallel Data
    try:
        paginator = translate.get_paginator('list_parallel_data')
        for page in paginator.paginate():
            for pd in page.get('ParallelDataPropertiesList', []):
                pd_name = pd['Name']
                pd_arn = pd.get('Arn', '')

                details = {
                    'status': pd.get('Status'),
                    'source_language_code': pd.get('SourceLanguageCode'),
                    'target_language_codes': pd.get('TargetLanguageCodes', []),
                    'description': pd.get('Description'),
                    'parallel_data_config': pd.get('ParallelDataConfig', {}).get('Format'),
                    'imported_data_size': pd.get('ImportedDataSize'),
                    'imported_record_count': pd.get('ImportedRecordCount'),
                    'failed_record_count': pd.get('FailedRecordCount'),
                    'skipped_record_count': pd.get('SkippedRecordCount'),
                    'created_at': str(pd.get('CreatedAt', '')),
                    'last_updated_at': str(pd.get('LastUpdatedAt', '')),
                    'message': pd.get('Message'),
                }

                resources.append({
                    'service': 'translate',
                    'type': 'parallel-data',
                    'id': pd_name,
                    'arn': pd_arn,
                    'name': pd_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
