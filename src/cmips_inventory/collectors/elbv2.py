"""
ELBv2 (Application, Network, Gateway Load Balancers) resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_elbv2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect ELBv2 resources: load balancers, target groups, listeners.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    elbv2 = session.client('elbv2', region_name=region)

    # Load Balancers
    load_balancers = []
    try:
        paginator = elbv2.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            for lb in page.get('LoadBalancers', []):
                load_balancers.append(lb)

                # Get tags
                tags = {}
                try:
                    tag_response = elbv2.describe_tags(ResourceArns=[lb['LoadBalancerArn']])
                    for tag_desc in tag_response.get('TagDescriptions', []):
                        for tag in tag_desc.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                lb_name = lb['LoadBalancerName']
                resources.append({
                    'service': 'elbv2',
                    'type': lb.get('Type', 'application') + '-load-balancer',
                    'id': lb_name,
                    'arn': lb['LoadBalancerArn'],
                    'name': lb_name,
                    'region': region,
                    'details': {
                        'type': lb.get('Type'),
                        'scheme': lb.get('Scheme'),
                        'state': lb.get('State', {}).get('Code'),
                        'dns_name': lb.get('DNSName'),
                        'vpc_id': lb.get('VpcId'),
                        'availability_zones': [az.get('ZoneName') for az in lb.get('AvailabilityZones', [])],
                        'security_groups': lb.get('SecurityGroups', []),
                        'ip_address_type': lb.get('IpAddressType'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Target Groups
    try:
        paginator = elbv2.get_paginator('describe_target_groups')
        for page in paginator.paginate():
            for tg in page.get('TargetGroups', []):
                # Get tags
                tags = {}
                try:
                    tag_response = elbv2.describe_tags(ResourceArns=[tg['TargetGroupArn']])
                    for tag_desc in tag_response.get('TagDescriptions', []):
                        for tag in tag_desc.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                # Get target health
                healthy_count = 0
                unhealthy_count = 0
                try:
                    health_response = elbv2.describe_target_health(TargetGroupArn=tg['TargetGroupArn'])
                    for target in health_response.get('TargetHealthDescriptions', []):
                        state = target.get('TargetHealth', {}).get('State')
                        if state == 'healthy':
                            healthy_count += 1
                        elif state in ['unhealthy', 'draining']:
                            unhealthy_count += 1
                except Exception:
                    pass

                tg_name = tg['TargetGroupName']
                resources.append({
                    'service': 'elbv2',
                    'type': 'target-group',
                    'id': tg_name,
                    'arn': tg['TargetGroupArn'],
                    'name': tg_name,
                    'region': region,
                    'details': {
                        'target_type': tg.get('TargetType'),
                        'protocol': tg.get('Protocol'),
                        'port': tg.get('Port'),
                        'vpc_id': tg.get('VpcId'),
                        'health_check_protocol': tg.get('HealthCheckProtocol'),
                        'health_check_path': tg.get('HealthCheckPath'),
                        'healthy_targets': healthy_count,
                        'unhealthy_targets': unhealthy_count,
                        'load_balancer_arns': tg.get('LoadBalancerArns', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Listeners (for each load balancer)
    for lb in load_balancers:
        try:
            paginator = elbv2.get_paginator('describe_listeners')
            for page in paginator.paginate(LoadBalancerArn=lb['LoadBalancerArn']):
                for listener in page.get('Listeners', []):
                    # Get tags
                    tags = {}
                    try:
                        tag_response = elbv2.describe_tags(ResourceArns=[listener['ListenerArn']])
                        for tag_desc in tag_response.get('TagDescriptions', []):
                            for tag in tag_desc.get('Tags', []):
                                tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    default_actions = listener.get('DefaultActions', [])
                    resources.append({
                        'service': 'elbv2',
                        'type': 'listener',
                        'id': listener['ListenerArn'].split('/')[-1],
                        'arn': listener['ListenerArn'],
                        'name': f"{lb['LoadBalancerName']}:{listener.get('Port')}",
                        'region': region,
                        'details': {
                            'load_balancer_arn': lb['LoadBalancerArn'],
                            'load_balancer_name': lb['LoadBalancerName'],
                            'port': listener.get('Port'),
                            'protocol': listener.get('Protocol'),
                            'ssl_policy': listener.get('SslPolicy'),
                            'certificates': [c.get('CertificateArn') for c in listener.get('Certificates', [])],
                            'default_action_type': default_actions[0].get('Type') if default_actions else None,
                        },
                        'tags': tags
                    })
        except Exception:
            pass

    return resources
