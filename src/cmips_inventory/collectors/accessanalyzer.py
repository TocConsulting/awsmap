"""
AWS IAM Access Analyzer resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_accessanalyzer_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS IAM Access Analyzer resources: analyzers and archive rules.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    aa = session.client('accessanalyzer', region_name=region)

    # Analyzers
    try:
        paginator = aa.get_paginator('list_analyzers')
        for page in paginator.paginate():
            for analyzer in page.get('analyzers', []):
                analyzer_name = analyzer['name']
                analyzer_arn = analyzer['arn']

                details = {
                    'type': analyzer.get('type'),
                    'status': analyzer.get('status'),
                    'status_reason': analyzer.get('statusReason', {}).get('code'),
                    'created_at': str(analyzer.get('createdAt', '')),
                    'last_resource_analyzed': analyzer.get('lastResourceAnalyzed'),
                    'last_resource_analyzed_at': str(analyzer.get('lastResourceAnalyzedAt', '')),
                }

                # Get configuration details
                config = analyzer.get('configuration', {})
                if config:
                    if 'unusedAccess' in config:
                        details['unused_access_age'] = config['unusedAccess'].get('unusedAccessAge')

                # Get tags
                tags = analyzer.get('tags', {})

                resources.append({
                    'service': 'accessanalyzer',
                    'type': 'analyzer',
                    'id': analyzer_name,
                    'arn': analyzer_arn,
                    'name': analyzer_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })

                # Archive Rules for this analyzer
                try:
                    rule_paginator = aa.get_paginator('list_archive_rules')
                    for rule_page in rule_paginator.paginate(analyzerName=analyzer_name):
                        for rule in rule_page.get('archiveRules', []):
                            rule_name = rule['ruleName']

                            rule_details = {
                                'analyzer_name': analyzer_name,
                                'created_at': str(rule.get('createdAt', '')),
                                'updated_at': str(rule.get('updatedAt', '')),
                                'filter_count': len(rule.get('filter', {})),
                            }

                            resources.append({
                                'service': 'accessanalyzer',
                                'type': 'archive-rule',
                                'id': rule_name,
                                'arn': f"{analyzer_arn}/archive-rule/{rule_name}",
                                'name': rule_name,
                                'region': region,
                                'details': rule_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
