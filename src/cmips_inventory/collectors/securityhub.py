"""
Security Hub resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_securityhub_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Security Hub resources: hub, enabled standards, insights, automation rules.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    securityhub = session.client('securityhub', region_name=region)

    # Check if Security Hub is enabled
    try:
        hub_response = securityhub.describe_hub()

        hub_arn = hub_response.get('HubArn')

        # Get tags
        tags = {}
        try:
            tag_response = securityhub.list_tags_for_resource(ResourceArn=hub_arn)
            tags = tag_response.get('Tags', {})
        except Exception:
            pass

        resources.append({
            'service': 'securityhub',
            'type': 'hub',
            'id': hub_arn.split('/')[-1],
            'arn': hub_arn,
            'name': 'security-hub',
            'region': region,
            'details': {
                'subscribed_at': hub_response.get('SubscribedAt'),
                'auto_enable_controls': hub_response.get('AutoEnableControls'),
                'control_finding_generator': hub_response.get('ControlFindingGenerator'),
            },
            'tags': tags
        })

        # Enabled Standards
        try:
            paginator = securityhub.get_paginator('get_enabled_standards')
            for page in paginator.paginate():
                for standard in page.get('StandardsSubscriptions', []):
                    standard_arn = standard['StandardsArn']
                    subscription_arn = standard['StandardsSubscriptionArn']

                    resources.append({
                        'service': 'securityhub',
                        'type': 'enabled-standard',
                        'id': subscription_arn.split('/')[-1],
                        'arn': subscription_arn,
                        'name': standard_arn.split('/')[-1],
                        'region': region,
                        'details': {
                            'standards_arn': standard_arn,
                            'standards_status': standard.get('StandardsStatus'),
                            'standards_status_reason': standard.get('StandardsStatusReason', {}).get('StatusReasonCode'),
                        },
                        'tags': {}
                    })
        except Exception:
            pass

        # Custom Insights
        try:
            paginator = securityhub.get_paginator('get_insights')
            for page in paginator.paginate():
                for insight in page.get('Insights', []):
                    insight_arn = insight['InsightArn']

                    # Skip AWS managed insights (they start with arn:aws:securityhub:::insight/)
                    if ':::insight/' in insight_arn:
                        continue

                    resources.append({
                        'service': 'securityhub',
                        'type': 'insight',
                        'id': insight_arn.split('/')[-1],
                        'arn': insight_arn,
                        'name': insight.get('Name', insight_arn.split('/')[-1]),
                        'region': region,
                        'details': {
                            'group_by_attribute': insight.get('GroupByAttribute'),
                            'filters': bool(insight.get('Filters')),
                        },
                        'tags': {}
                    })
        except Exception:
            pass

        # Automation Rules
        try:
            paginator = securityhub.get_paginator('list_automation_rules')
            for page in paginator.paginate():
                for rule in page.get('AutomationRulesMetadata', []):
                    rule_arn = rule['RuleArn']

                    resources.append({
                        'service': 'securityhub',
                        'type': 'automation-rule',
                        'id': rule_arn.split('/')[-1],
                        'arn': rule_arn,
                        'name': rule.get('RuleName', rule_arn.split('/')[-1]),
                        'region': region,
                        'details': {
                            'rule_status': rule.get('RuleStatus'),
                            'rule_order': rule.get('RuleOrder'),
                            'description': rule.get('Description'),
                            'is_terminal': rule.get('IsTerminal'),
                            'created_at': str(rule.get('CreatedAt', '')),
                            'updated_at': str(rule.get('UpdatedAt', '')),
                            'created_by': rule.get('CreatedBy'),
                        },
                        'tags': {}
                    })
        except Exception:
            pass

    except securityhub.exceptions.InvalidAccessException:
        # Security Hub not enabled
        pass
    except Exception:
        pass

    return resources
