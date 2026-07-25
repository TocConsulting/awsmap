"""
CloudWatch resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_cloudwatch_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CloudWatch resources: alarms, dashboards, metric streams.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    cloudwatch = session.client('cloudwatch', region_name=region)

    # CloudWatch Alarms
    try:
        paginator = cloudwatch.get_paginator('describe_alarms')
        for page in paginator.paginate():
            # Metric Alarms
            for alarm in page.get('MetricAlarms', []):
                alarm_name = alarm['AlarmName']
                alarm_arn = alarm['AlarmArn']

                # Get tags
                tags = {}
                try:
                    tag_response = cloudwatch.list_tags_for_resource(ResourceARN=alarm_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'cloudwatch',
                    'type': 'metric-alarm',
                    'id': alarm_name,
                    'arn': alarm_arn,
                    'name': alarm_name,
                    'region': region,
                    'details': {
                        'state_value': alarm.get('StateValue'),
                        'state_reason': alarm.get('StateReason'),
                        'metric_name': alarm.get('MetricName'),
                        'namespace': alarm.get('Namespace'),
                        'statistic': alarm.get('Statistic'),
                        'period': alarm.get('Period'),
                        'evaluation_periods': alarm.get('EvaluationPeriods'),
                        'threshold': alarm.get('Threshold'),
                        'comparison_operator': alarm.get('ComparisonOperator'),
                        'alarm_actions': alarm.get('AlarmActions', []),
                        'ok_actions': alarm.get('OKActions', []),
                        'insufficient_data_actions': alarm.get('InsufficientDataActions', []),
                        'actions_enabled': alarm.get('ActionsEnabled'),
                    },
                    'tags': tags
                })

            # Composite Alarms
            for alarm in page.get('CompositeAlarms', []):
                alarm_name = alarm['AlarmName']
                alarm_arn = alarm['AlarmArn']

                # Get tags
                tags = {}
                try:
                    tag_response = cloudwatch.list_tags_for_resource(ResourceARN=alarm_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'cloudwatch',
                    'type': 'composite-alarm',
                    'id': alarm_name,
                    'arn': alarm_arn,
                    'name': alarm_name,
                    'region': region,
                    'details': {
                        'state_value': alarm.get('StateValue'),
                        'state_reason': alarm.get('StateReason'),
                        'alarm_rule': alarm.get('AlarmRule'),
                        'alarm_actions': alarm.get('AlarmActions', []),
                        'ok_actions': alarm.get('OKActions', []),
                        'insufficient_data_actions': alarm.get('InsufficientDataActions', []),
                        'actions_enabled': alarm.get('ActionsEnabled'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # CloudWatch Dashboards
    try:
        paginator = cloudwatch.get_paginator('list_dashboards')
        for page in paginator.paginate():
            for dashboard in page.get('DashboardEntries', []):
                dashboard_name = dashboard['DashboardName']
                dashboard_arn = dashboard['DashboardArn']

                resources.append({
                    'service': 'cloudwatch',
                    'type': 'dashboard',
                    'id': dashboard_name,
                    'arn': dashboard_arn,
                    'name': dashboard_name,
                    'region': region,
                    'details': {
                        'size': dashboard.get('Size'),
                        'last_modified': str(dashboard.get('LastModified', '')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Metric Streams
    try:
        paginator = cloudwatch.get_paginator('list_metric_streams')
        for page in paginator.paginate():
            for stream in page.get('Entries', []):
                stream_name = stream['Name']
                stream_arn = stream['Arn']

                resources.append({
                    'service': 'cloudwatch',
                    'type': 'metric-stream',
                    'id': stream_name,
                    'arn': stream_arn,
                    'name': stream_name,
                    'region': region,
                    'details': {
                        'state': stream.get('State'),
                        'firehose_arn': stream.get('FirehoseArn'),
                        'output_format': stream.get('OutputFormat'),
                        'creation_date': str(stream.get('CreationDate', '')),
                        'last_update_date': str(stream.get('LastUpdateDate', '')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
