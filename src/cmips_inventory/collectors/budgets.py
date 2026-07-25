"""
AWS Budgets resource collector.

Note: Budgets is a global service.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_budgets_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Budgets resources: budgets and budget actions.

    Note: Budgets is a global service, called from us-east-1.

    Args:
        session: boto3.Session to use
        region: AWS region (ignored - global service)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    budgets = session.client('budgets', region_name='us-east-1')

    # Budgets
    try:
        paginator = budgets.get_paginator('describe_budgets')
        for page in paginator.paginate(AccountId=account_id):
            for budget in page.get('Budgets', []):
                budget_name = budget['BudgetName']

                budget_limit = budget.get('BudgetLimit', {})
                calculated_spend = budget.get('CalculatedSpend', {})
                actual_spend = calculated_spend.get('ActualSpend', {})
                forecasted_spend = calculated_spend.get('ForecastedSpend', {})

                details = {
                    'budget_type': budget.get('BudgetType'),
                    'time_unit': budget.get('TimeUnit'),
                    'limit_amount': budget_limit.get('Amount'),
                    'limit_unit': budget_limit.get('Unit'),
                    'actual_spend_amount': actual_spend.get('Amount'),
                    'actual_spend_unit': actual_spend.get('Unit'),
                    'forecasted_spend_amount': forecasted_spend.get('Amount'),
                    'forecasted_spend_unit': forecasted_spend.get('Unit'),
                    'time_period_start': str(budget.get('TimePeriod', {}).get('Start', '')),
                    'time_period_end': str(budget.get('TimePeriod', {}).get('End', '')),
                    'last_updated_time': str(budget.get('LastUpdatedTime', '')),
                    'auto_adjust_type': budget.get('AutoAdjustData', {}).get('AutoAdjustType'),
                }

                # Cost filters
                cost_filters = budget.get('CostFilters', {})
                if cost_filters:
                    details['cost_filter_keys'] = list(cost_filters.keys())

                # Cost types
                cost_types = budget.get('CostTypes', {})
                if cost_types:
                    details['include_tax'] = cost_types.get('IncludeTax')
                    details['include_subscription'] = cost_types.get('IncludeSubscription')
                    details['use_blended'] = cost_types.get('UseBlended')

                resources.append({
                    'service': 'budgets',
                    'type': 'budget',
                    'id': budget_name,
                    'arn': f"arn:aws:budgets::{account_id}:budget/{budget_name}",
                    'name': budget_name,
                    'region': 'global',
                    'details': details,
                    'tags': {}
                })

                # Budget Actions for this budget
                try:
                    action_paginator = budgets.get_paginator('describe_budget_actions_for_budget')
                    for action_page in action_paginator.paginate(AccountId=account_id, BudgetName=budget_name):
                        for action in action_page.get('Actions', []):
                            action_id = action['ActionId']

                            action_details = {
                                'budget_name': budget_name,
                                'notification_type': action.get('NotificationType'),
                                'action_type': action.get('ActionType'),
                                'action_threshold_type': action.get('ActionThreshold', {}).get('ActionThresholdType'),
                                'action_threshold_value': action.get('ActionThreshold', {}).get('ActionThresholdValue'),
                                'status': action.get('Status'),
                                'execution_role_arn': action.get('ExecutionRoleArn'),
                                'approval_model': action.get('ApprovalModel'),
                            }

                            # Action definition
                            definition = action.get('Definition', {})
                            if 'IamActionDefinition' in definition:
                                action_details['iam_action_policy_arn'] = definition['IamActionDefinition'].get('PolicyArn')
                            if 'ScpActionDefinition' in definition:
                                action_details['scp_action_policy_id'] = definition['ScpActionDefinition'].get('PolicyId')
                            if 'SsmActionDefinition' in definition:
                                action_details['ssm_action_type'] = definition['SsmActionDefinition'].get('ActionSubType')

                            resources.append({
                                'service': 'budgets',
                                'type': 'budget-action',
                                'id': action_id,
                                'arn': f"arn:aws:budgets::{account_id}:budget/{budget_name}/action/{action_id}",
                                'name': f"{budget_name}-{action_id[:8]}",
                                'region': 'global',
                                'details': action_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
