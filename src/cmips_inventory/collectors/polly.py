"""
AWS Polly resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_polly_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Polly resources: lexicons.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    polly = session.client('polly', region_name=region)

    # Lexicons
    try:
        response = polly.list_lexicons()
        for lexicon in response.get('Lexicons', []):
            lexicon_name = lexicon['Name']
            attributes = lexicon.get('Attributes', {})

            details = {
                'alphabet': attributes.get('Alphabet'),
                'language_code': attributes.get('LanguageCode'),
                'last_modified': str(attributes.get('LastModified', '')),
                'lexicon_arn': attributes.get('LexiconArn'),
                'lexemes_count': attributes.get('LexemesCount'),
                'size': attributes.get('Size'),
            }

            resources.append({
                'service': 'polly',
                'type': 'lexicon',
                'id': lexicon_name,
                'arn': attributes.get('LexiconArn', f"arn:aws:polly:{region}:{account_id}:lexicon/{lexicon_name}"),
                'name': lexicon_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    return resources
