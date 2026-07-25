"""
AWS Transcribe resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_transcribe_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Transcribe resources: vocabularies, vocabulary filters, and language models.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    transcribe = session.client('transcribe', region_name=region)

    # Vocabularies
    try:
        paginator = transcribe.get_paginator('list_vocabularies')
        for page in paginator.paginate():
            for vocab in page.get('Vocabularies', []):
                vocab_name = vocab['VocabularyName']

                details = {
                    'language_code': vocab.get('LanguageCode'),
                    'vocabulary_state': vocab.get('VocabularyState'),
                    'last_modified_time': str(vocab.get('LastModifiedTime', '')),
                }

                resources.append({
                    'service': 'transcribe',
                    'type': 'vocabulary',
                    'id': vocab_name,
                    'arn': f"arn:aws:transcribe:{region}:{account_id}:vocabulary/{vocab_name}",
                    'name': vocab_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Vocabulary Filters
    try:
        paginator = transcribe.get_paginator('list_vocabulary_filters')
        for page in paginator.paginate():
            for filter_item in page.get('VocabularyFilters', []):
                filter_name = filter_item['VocabularyFilterName']

                details = {
                    'language_code': filter_item.get('LanguageCode'),
                    'last_modified_time': str(filter_item.get('LastModifiedTime', '')),
                }

                resources.append({
                    'service': 'transcribe',
                    'type': 'vocabulary-filter',
                    'id': filter_name,
                    'arn': f"arn:aws:transcribe:{region}:{account_id}:vocabulary-filter/{filter_name}",
                    'name': filter_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Language Models
    try:
        paginator = transcribe.get_paginator('list_language_models')
        for page in paginator.paginate():
            for model in page.get('Models', []):
                model_name = model['ModelName']

                details = {
                    'language_code': model.get('LanguageCode'),
                    'base_model_name': model.get('BaseModelName'),
                    'model_status': model.get('ModelStatus'),
                    'create_time': str(model.get('CreateTime', '')),
                    'last_modified_time': str(model.get('LastModifiedTime', '')),
                    'upgrade_availability': model.get('UpgradeAvailability'),
                }

                input_data = model.get('InputDataConfig', {})
                if input_data:
                    details['s3_uri'] = input_data.get('S3Uri')
                    details['data_access_role_arn'] = input_data.get('DataAccessRoleArn')

                resources.append({
                    'service': 'transcribe',
                    'type': 'language-model',
                    'id': model_name,
                    'arn': f"arn:aws:transcribe:{region}:{account_id}:language-model/{model_name}",
                    'name': model_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Call Analytics Categories
    try:
        paginator = transcribe.get_paginator('list_call_analytics_categories')
        for page in paginator.paginate():
            for category in page.get('Categories', []):
                category_name = category['CategoryName']

                details = {
                    'create_time': str(category.get('CreateTime', '')),
                    'last_update_time': str(category.get('LastUpdateTime', '')),
                    'input_type': category.get('InputType'),
                }

                resources.append({
                    'service': 'transcribe',
                    'type': 'call-analytics-category',
                    'id': category_name,
                    'arn': f"arn:aws:transcribe:{region}:{account_id}:analytics-category/{category_name}",
                    'name': category_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
