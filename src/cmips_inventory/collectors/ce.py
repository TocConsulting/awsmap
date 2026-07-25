"""
Cost Explorer resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_ce_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Cost Explorer resources: cost anomaly monitors, cost anomaly subscriptions, cost categories.

    Args:
        session: boto3.Session to use
        region: Not used for Cost Explorer (global service)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ce = session.client('ce', region_name='us-east-1')  # CE is global, use us-east-1

    # Cost Anomaly Monitors
    try:
        response = ce.get_anomaly_monitors()
        for monitor in response.get('AnomalyMonitors', []):
            monitor_arn = monitor['MonitorArn']
            monitor_name = monitor['MonitorName']

            resources.append({
                'service': 'ce',
                'type': 'anomaly-monitor',
                'id': monitor_arn.split('/')[-1],
                'arn': monitor_arn,
                'name': monitor_name,
                'region': 'global',
                'details': {
                    'monitor_type': monitor.get('MonitorType'),
                    'monitor_dimension': monitor.get('MonitorDimension'),
                    'monitor_specification': monitor.get('MonitorSpecification'),
                    'creation_date': str(monitor.get('CreationDate', '')),
                    'last_evaluated_date': str(monitor.get('LastEvaluatedDate', '')),
                    'last_updated_date': str(monitor.get('LastUpdatedDate', '')),
                    'dimensional_value_count': monitor.get('DimensionalValueCount'),
                },
                'tags': {}
            })
    except Exception:
        pass

    # Cost Anomaly Subscriptions
    try:
        response = ce.get_anomaly_subscriptions()
        for subscription in response.get('AnomalySubscriptions', []):
            sub_arn = subscription['SubscriptionArn']
            sub_name = subscription['SubscriptionName']

            resources.append({
                'service': 'ce',
                'type': 'anomaly-subscription',
                'id': sub_arn.split('/')[-1],
                'arn': sub_arn,
                'name': sub_name,
                'region': 'global',
                'details': {
                    'monitor_arn_list': subscription.get('MonitorArnList', []),
                    'subscribers': subscription.get('Subscribers', []),
                    'threshold': subscription.get('Threshold'),
                    'frequency': subscription.get('Frequency'),
                    'threshold_expression': subscription.get('ThresholdExpression'),
                },
                'tags': {}
            })
    except Exception:
        pass

    # Cost Categories
    try:
        response = ce.list_cost_category_definitions()
        for category in response.get('CostCategoryReferences', []):
            category_arn = category['CostCategoryArn']
            category_name = category['Name']

            try:
                # Get category details
                cat_response = ce.describe_cost_category_definition(
                    CostCategoryArn=category_arn
                )
                cat_detail = cat_response.get('CostCategory', {})

                resources.append({
                    'service': 'ce',
                    'type': 'cost-category',
                    'id': category_arn.split('/')[-1],
                    'arn': category_arn,
                    'name': category_name,
                    'region': 'global',
                    'details': {
                        'effective_start': category.get('EffectiveStart'),
                        'effective_end': category.get('EffectiveEnd'),
                        'number_of_rules': category.get('NumberOfRules'),
                        'rule_version': cat_detail.get('RuleVersion'),
                        'default_value': cat_detail.get('DefaultValue'),
                        'split_charge_rules_count': len(cat_detail.get('SplitChargeRules', [])),
                    },
                    'tags': {}
                })
            except Exception:
                pass
    except Exception:
        pass

    # Savings Plans
    try:
        savingsplans = session.client('savingsplans', region_name='us-east-1')
        response = savingsplans.describe_savings_plans()
        for sp in response.get('savingsPlans', []):
            sp_arn = sp['savingsPlanArn']
            sp_id = sp['savingsPlanId']

            # Get tags
            tags = sp.get('tags', {})

            resources.append({
                'service': 'ce',
                'type': 'savings-plan',
                'id': sp_id,
                'arn': sp_arn,
                'name': sp.get('description') or sp_id,
                'region': 'global',
                'details': {
                    'state': sp.get('state'),
                    'savings_plan_type': sp.get('savingsPlanType'),
                    'payment_option': sp.get('paymentOption'),
                    'commitment': sp.get('commitment'),
                    'upfront_payment_amount': sp.get('upfrontPaymentAmount'),
                    'recurring_payment_amount': sp.get('recurringPaymentAmount'),
                    'term_duration_in_seconds': sp.get('termDurationInSeconds'),
                    'start': str(sp.get('start', '')),
                    'end': str(sp.get('end', '')),
                    'ec2_instance_family': sp.get('ec2InstanceFamily'),
                    'region_filter': sp.get('region'),
                },
                'tags': tags
            })
    except Exception:
        pass

    return resources
