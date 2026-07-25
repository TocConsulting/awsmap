"""
AWS Compute Optimizer resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_computeoptimizer_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Compute Optimizer recommendations: EC2, Auto Scaling, Lambda, EBS, ECS.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    co = session.client('compute-optimizer', region_name=region)

    # Check enrollment status
    try:
        status = co.get_enrollment_status()
        if status.get('status') != 'Active':
            return []
    except Exception:
        return []

    # EC2 Instance Recommendations
    try:
        response = co.get_ec2_instance_recommendations()
        for rec in response.get('instanceRecommendations', []):
            instance_arn = rec.get('instanceArn', '')
            instance_name = rec.get('instanceName', instance_arn.split('/')[-1])

            details = {
                'finding': rec.get('finding'),
                'finding_reason_codes': rec.get('findingReasonCodes', []),
                'current_instance_type': rec.get('currentInstanceType'),
                'look_back_period_in_days': rec.get('lookBackPeriodInDays'),
                'last_refresh_timestamp': str(rec.get('lastRefreshTimestamp', '')),
                'current_performance_risk': rec.get('currentPerformanceRisk'),
                'effective_recommendation_preferences': rec.get('effectiveRecommendationPreferences', {}),
                'inference_accelerator_state': rec.get('inferenceAcceleratorState'),
                'idle': rec.get('idle'),
            }

            # Recommendation options count
            options = rec.get('recommendationOptions', [])
            details['recommendation_options_count'] = len(options)
            if options:
                top_option = options[0]
                details['top_recommendation_instance_type'] = top_option.get('instanceType')
                details['top_recommendation_performance_risk'] = top_option.get('performanceRisk')

            resources.append({
                'service': 'compute-optimizer',
                'type': 'ec2-recommendation',
                'id': instance_arn.split('/')[-1] if instance_arn else instance_name,
                'arn': instance_arn,
                'name': instance_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Auto Scaling Group Recommendations
    try:
        response = co.get_auto_scaling_group_recommendations()
        for rec in response.get('autoScalingGroupRecommendations', []):
            asg_arn = rec.get('autoScalingGroupArn', '')
            asg_name = rec.get('autoScalingGroupName', asg_arn.split('/')[-1])

            details = {
                'finding': rec.get('finding'),
                'current_instance_type': rec.get('currentConfiguration', {}).get('instanceType'),
                'current_desired_capacity': rec.get('currentConfiguration', {}).get('desiredCapacity'),
                'current_min_size': rec.get('currentConfiguration', {}).get('minSize'),
                'current_max_size': rec.get('currentConfiguration', {}).get('maxSize'),
                'look_back_period_in_days': rec.get('lookBackPeriodInDays'),
                'last_refresh_timestamp': str(rec.get('lastRefreshTimestamp', '')),
                'current_performance_risk': rec.get('currentPerformanceRisk'),
            }

            options = rec.get('recommendationOptions', [])
            details['recommendation_options_count'] = len(options)

            resources.append({
                'service': 'compute-optimizer',
                'type': 'asg-recommendation',
                'id': asg_name,
                'arn': asg_arn,
                'name': asg_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Lambda Function Recommendations
    try:
        paginator = co.get_paginator('get_lambda_function_recommendations')
        for page in paginator.paginate():
            for rec in page.get('lambdaFunctionRecommendations', []):
                func_arn = rec.get('functionArn', '')
                func_version = rec.get('functionVersion', '$LATEST')

                details = {
                    'finding': rec.get('finding'),
                    'finding_reason_codes': rec.get('findingReasonCodes', []),
                    'current_memory_size': rec.get('currentMemorySize'),
                    'number_of_invocations': rec.get('numberOfInvocations'),
                    'look_back_period_in_days': rec.get('lookBackPeriodInDays'),
                    'last_refresh_timestamp': str(rec.get('lastRefreshTimestamp', '')),
                    'current_performance_risk': rec.get('currentPerformanceRisk'),
                }

                options = rec.get('memorySizeRecommendationOptions', [])
                details['recommendation_options_count'] = len(options)
                if options:
                    details['top_recommendation_memory_size'] = options[0].get('memorySize')

                resources.append({
                    'service': 'compute-optimizer',
                    'type': 'lambda-recommendation',
                    'id': f"{func_arn.split(':')[-1]}:{func_version}",
                    'arn': func_arn,
                    'name': func_arn.split(':')[-1] if func_arn else 'unknown',
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # EBS Volume Recommendations
    try:
        response = co.get_ebs_volume_recommendations()
        for rec in response.get('volumeRecommendations', []):
            volume_arn = rec.get('volumeArn', '')

            current_config = rec.get('currentConfiguration', {})
            details = {
                'finding': rec.get('finding'),
                'current_volume_type': current_config.get('volumeType'),
                'current_volume_size': current_config.get('volumeSize'),
                'current_iops': current_config.get('volumeBaselineIOPS'),
                'current_throughput': current_config.get('volumeBaselineThroughput'),
                'look_back_period_in_days': rec.get('lookBackPeriodInDays'),
                'last_refresh_timestamp': str(rec.get('lastRefreshTimestamp', '')),
                'current_performance_risk': rec.get('currentPerformanceRisk'),
            }

            options = rec.get('volumeRecommendationOptions', [])
            details['recommendation_options_count'] = len(options)

            resources.append({
                'service': 'compute-optimizer',
                'type': 'ebs-recommendation',
                'id': volume_arn.split('/')[-1] if volume_arn else 'unknown',
                'arn': volume_arn,
                'name': volume_arn.split('/')[-1] if volume_arn else 'unknown',
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    return resources
