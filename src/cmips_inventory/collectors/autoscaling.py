"""
Auto Scaling resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_autoscaling_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Auto Scaling resources: auto scaling groups, launch configurations, scaling policies.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    autoscaling = session.client('autoscaling', region_name=region)

    # Auto Scaling Groups
    try:
        paginator = autoscaling.get_paginator('describe_auto_scaling_groups')
        for page in paginator.paginate():
            for asg in page.get('AutoScalingGroups', []):
                asg_name = asg['AutoScalingGroupName']
                asg_arn = asg['AutoScalingGroupARN']

                # Tags are included in the response
                tags = {}
                for tag in asg.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                resources.append({
                    'service': 'autoscaling',
                    'type': 'auto-scaling-group',
                    'id': asg_name,
                    'arn': asg_arn,
                    'name': asg_name,
                    'region': region,
                    'details': {
                        'min_size': asg.get('MinSize'),
                        'max_size': asg.get('MaxSize'),
                        'desired_capacity': asg.get('DesiredCapacity'),
                        'default_cooldown': asg.get('DefaultCooldown'),
                        'availability_zones': asg.get('AvailabilityZones', []),
                        'load_balancer_names': asg.get('LoadBalancerNames', []),
                        'target_group_arns': asg.get('TargetGroupARNs', []),
                        'health_check_type': asg.get('HealthCheckType'),
                        'health_check_grace_period': asg.get('HealthCheckGracePeriod'),
                        'instances_count': len(asg.get('Instances', [])),
                        'launch_configuration_name': asg.get('LaunchConfigurationName'),
                        'launch_template': asg.get('LaunchTemplate'),
                        'mixed_instances_policy': bool(asg.get('MixedInstancesPolicy')),
                        'vpc_zone_identifier': asg.get('VPCZoneIdentifier'),
                        'service_linked_role_arn': asg.get('ServiceLinkedRoleARN'),
                        'capacity_rebalance': asg.get('CapacityRebalance'),
                        'created_time': str(asg.get('CreatedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Launch Configurations
    try:
        paginator = autoscaling.get_paginator('describe_launch_configurations')
        for page in paginator.paginate():
            for lc in page.get('LaunchConfigurations', []):
                lc_name = lc['LaunchConfigurationName']
                lc_arn = lc['LaunchConfigurationARN']

                resources.append({
                    'service': 'autoscaling',
                    'type': 'launch-configuration',
                    'id': lc_name,
                    'arn': lc_arn,
                    'name': lc_name,
                    'region': region,
                    'details': {
                        'image_id': lc.get('ImageId'),
                        'instance_type': lc.get('InstanceType'),
                        'key_name': lc.get('KeyName'),
                        'security_groups': lc.get('SecurityGroups', []),
                        'instance_monitoring': lc.get('InstanceMonitoring', {}).get('Enabled'),
                        'spot_price': lc.get('SpotPrice'),
                        'iam_instance_profile': lc.get('IamInstanceProfile'),
                        'ebs_optimized': lc.get('EbsOptimized'),
                        'associate_public_ip_address': lc.get('AssociatePublicIpAddress'),
                        'placement_tenancy': lc.get('PlacementTenancy'),
                        'created_time': str(lc.get('CreatedTime', '')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Scaling Policies
    try:
        paginator = autoscaling.get_paginator('describe_policies')
        for page in paginator.paginate():
            for policy in page.get('ScalingPolicies', []):
                policy_name = policy['PolicyName']
                policy_arn = policy['PolicyARN']

                resources.append({
                    'service': 'autoscaling',
                    'type': 'scaling-policy',
                    'id': policy_name,
                    'arn': policy_arn,
                    'name': policy_name,
                    'region': region,
                    'details': {
                        'auto_scaling_group_name': policy.get('AutoScalingGroupName'),
                        'policy_type': policy.get('PolicyType'),
                        'adjustment_type': policy.get('AdjustmentType'),
                        'scaling_adjustment': policy.get('ScalingAdjustment'),
                        'cooldown': policy.get('Cooldown'),
                        'min_adjustment_magnitude': policy.get('MinAdjustmentMagnitude'),
                        'metric_aggregation_type': policy.get('MetricAggregationType'),
                        'estimated_instance_warmup': policy.get('EstimatedInstanceWarmup'),
                        'enabled': policy.get('Enabled'),
                        'target_tracking_configuration': bool(policy.get('TargetTrackingConfiguration')),
                        'predictive_scaling_configuration': bool(policy.get('PredictiveScalingConfiguration')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Scheduled Actions
    try:
        paginator = autoscaling.get_paginator('describe_scheduled_actions')
        for page in paginator.paginate():
            for action in page.get('ScheduledUpdateGroupActions', []):
                action_name = action['ScheduledActionName']
                action_arn = action['ScheduledActionARN']

                resources.append({
                    'service': 'autoscaling',
                    'type': 'scheduled-action',
                    'id': action_name,
                    'arn': action_arn,
                    'name': action_name,
                    'region': region,
                    'details': {
                        'auto_scaling_group_name': action.get('AutoScalingGroupName'),
                        'recurrence': action.get('Recurrence'),
                        'min_size': action.get('MinSize'),
                        'max_size': action.get('MaxSize'),
                        'desired_capacity': action.get('DesiredCapacity'),
                        'start_time': str(action.get('StartTime', '')),
                        'end_time': str(action.get('EndTime', '')),
                        'time_zone': action.get('TimeZone'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
