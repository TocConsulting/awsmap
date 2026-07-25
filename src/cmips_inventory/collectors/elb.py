"""
Classic ELB resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_elb_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Classic ELB resources.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    elb = session.client('elb', region_name=region)

    try:
        paginator = elb.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            for lb in page.get('LoadBalancerDescriptions', []):
                lb_name = lb['LoadBalancerName']

                # Get tags
                tags = {}
                try:
                    tag_response = elb.describe_tags(LoadBalancerNames=[lb_name])
                    for tag_desc in tag_response.get('TagDescriptions', []):
                        for tag in tag_desc.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'elb',
                    'type': 'classic-load-balancer',
                    'id': lb_name,
                    'arn': f"arn:aws:elasticloadbalancing:{region}:{account_id}:loadbalancer/{lb_name}",
                    'name': lb_name,
                    'region': region,
                    'details': {
                        'dns_name': lb.get('DNSName'),
                        'scheme': lb.get('Scheme'),
                        'vpc_id': lb.get('VPCId'),
                        'availability_zones': lb.get('AvailabilityZones', []),
                        'subnets': lb.get('Subnets', []),
                        'security_groups': lb.get('SecurityGroups', []),
                        'instances': [i.get('InstanceId') for i in lb.get('Instances', [])],
                        'listeners': [
                            {
                                'protocol': l.get('Protocol'),
                                'lb_port': l.get('LoadBalancerPort'),
                                'instance_protocol': l.get('InstanceProtocol'),
                                'instance_port': l.get('InstancePort'),
                            }
                            for l in lb.get('ListenerDescriptions', [])
                            for l in [l.get('Listener', {})]
                        ],
                        'created_time': str(lb.get('CreatedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
