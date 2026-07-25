"""
X-Ray resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_xray_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect X-Ray resources: groups, sampling rules.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    xray = session.client('xray', region_name=region)

    # X-Ray Groups (skip AWS default group that exists in every region)
    try:
        paginator = xray.get_paginator('get_groups')
        for page in paginator.paginate():
            for group in page.get('Groups', []):
                group_name = group['GroupName']

                # Skip the AWS default group
                if group_name == 'Default':
                    continue

                group_arn = group['GroupARN']

                # Get tags
                tags = {}
                try:
                    tag_response = xray.list_tags_for_resource(ResourceARN=group_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'xray',
                    'type': 'group',
                    'id': group_name,
                    'arn': group_arn,
                    'name': group_name,
                    'region': region,
                    'details': {
                        'filter_expression': group.get('FilterExpression'),
                        'insights_configuration': group.get('InsightsConfiguration'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # X-Ray Sampling Rules (custom only)
    try:
        response = xray.get_sampling_rules()
        for rule_record in response.get('SamplingRuleRecords', []):
            rule = rule_record.get('SamplingRule', {})
            rule_name = rule.get('RuleName')

            # Skip the default rule
            if rule_name == 'Default':
                continue

            rule_arn = rule.get('RuleARN')

            # Get tags
            tags = {}
            if rule_arn:
                try:
                    tag_response = xray.list_tags_for_resource(ResourceARN=rule_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

            resources.append({
                'service': 'xray',
                'type': 'sampling-rule',
                'id': rule_name,
                'arn': rule_arn or f"arn:aws:xray:{region}:{account_id}:sampling-rule/{rule_name}",
                'name': rule_name,
                'region': region,
                'details': {
                    'priority': rule.get('Priority'),
                    'fixed_rate': rule.get('FixedRate'),
                    'reservoir_size': rule.get('ReservoirSize'),
                    'service_name': rule.get('ServiceName'),
                    'service_type': rule.get('ServiceType'),
                    'host': rule.get('Host'),
                    'http_method': rule.get('HTTPMethod'),
                    'url_path': rule.get('URLPath'),
                    'version': rule.get('Version'),
                    'created_at': str(rule_record.get('CreatedAt', '')),
                    'modified_at': str(rule_record.get('ModifiedAt', '')),
                },
                'tags': tags
            })
    except Exception:
        pass

    return resources
