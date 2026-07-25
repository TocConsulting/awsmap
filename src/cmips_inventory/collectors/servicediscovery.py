"""
AWS Cloud Map (Service Discovery) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_servicediscovery_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Cloud Map resources: namespaces, services, and instances.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sd = session.client('servicediscovery', region_name=region)

    # Namespaces
    try:
        paginator = sd.get_paginator('list_namespaces')
        for page in paginator.paginate():
            for ns in page.get('Namespaces', []):
                ns_id = ns['Id']
                ns_arn = ns['Arn']
                ns_name = ns.get('Name', ns_id)

                details = {
                    'type': ns.get('Type'),
                    'description': ns.get('Description'),
                    'service_count': ns.get('ServiceCount'),
                    'create_date': str(ns.get('CreateDate', '')),
                }

                # Get additional namespace details
                try:
                    ns_detail = sd.get_namespace(Id=ns_id)
                    ns_info = ns_detail.get('Namespace', {})
                    props = ns_info.get('Properties', {})

                    dns_props = props.get('DnsProperties', {})
                    if dns_props:
                        details['hosted_zone_id'] = dns_props.get('HostedZoneId')
                        details['soa_ttl'] = dns_props.get('SOA', {}).get('TTL')

                    http_props = props.get('HttpProperties', {})
                    if http_props:
                        details['http_name'] = http_props.get('HttpName')
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = sd.list_tags_for_resource(ResourceARN=ns_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'servicediscovery',
                    'type': 'namespace',
                    'id': ns_id,
                    'arn': ns_arn,
                    'name': ns_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })

                # Services in this namespace
                try:
                    svc_paginator = sd.get_paginator('list_services')
                    for svc_page in svc_paginator.paginate(
                        Filters=[{'Name': 'NAMESPACE_ID', 'Values': [ns_id], 'Condition': 'EQ'}]
                    ):
                        for svc in svc_page.get('Services', []):
                            svc_id = svc['Id']
                            svc_arn = svc['Arn']
                            svc_name = svc.get('Name', svc_id)

                            svc_details = {
                                'namespace_id': ns_id,
                                'namespace_name': ns_name,
                                'description': svc.get('Description'),
                                'instance_count': svc.get('InstanceCount'),
                                'create_date': str(svc.get('CreateDate', '')),
                                'type': svc.get('Type'),
                            }

                            # DNS config
                            dns_config = svc.get('DnsConfig', {})
                            if dns_config:
                                svc_details['routing_policy'] = dns_config.get('RoutingPolicy')
                                svc_details['dns_records'] = dns_config.get('DnsRecords', [])

                            # Health check config
                            hc_config = svc.get('HealthCheckConfig', {})
                            if hc_config:
                                svc_details['health_check_type'] = hc_config.get('Type')
                                svc_details['health_check_path'] = hc_config.get('ResourcePath')
                                svc_details['health_check_failure_threshold'] = hc_config.get('FailureThreshold')

                            hc_custom = svc.get('HealthCheckCustomConfig', {})
                            if hc_custom:
                                svc_details['custom_health_check_failure_threshold'] = hc_custom.get('FailureThreshold')

                            # Get service tags
                            svc_tags = {}
                            try:
                                svc_tag_response = sd.list_tags_for_resource(ResourceARN=svc_arn)
                                for tag in svc_tag_response.get('Tags', []):
                                    svc_tags[tag.get('Key', '')] = tag.get('Value', '')
                            except Exception:
                                pass

                            resources.append({
                                'service': 'servicediscovery',
                                'type': 'service',
                                'id': svc_id,
                                'arn': svc_arn,
                                'name': svc_name,
                                'region': region,
                                'details': svc_details,
                                'tags': svc_tags
                            })

                            # Instances for this service
                            try:
                                inst_paginator = sd.get_paginator('list_instances')
                                for inst_page in inst_paginator.paginate(ServiceId=svc_id):
                                    for inst in inst_page.get('Instances', []):
                                        inst_id = inst['Id']
                                        inst_attrs = inst.get('Attributes', {})

                                        inst_details = {
                                            'service_id': svc_id,
                                            'service_name': svc_name,
                                            'namespace_id': ns_id,
                                            'namespace_name': ns_name,
                                            'aws_instance_ipv4': inst_attrs.get('AWS_INSTANCE_IPV4'),
                                            'aws_instance_ipv6': inst_attrs.get('AWS_INSTANCE_IPV6'),
                                            'aws_instance_port': inst_attrs.get('AWS_INSTANCE_PORT'),
                                            'aws_alias_dns_name': inst_attrs.get('AWS_ALIAS_DNS_NAME'),
                                            'aws_init_health_status': inst_attrs.get('AWS_INIT_HEALTH_STATUS'),
                                        }

                                        # Add any custom attributes
                                        custom_attrs = {k: v for k, v in inst_attrs.items()
                                                       if not k.startswith('AWS_')}
                                        if custom_attrs:
                                            inst_details['custom_attributes'] = custom_attrs

                                        resources.append({
                                            'service': 'servicediscovery',
                                            'type': 'instance',
                                            'id': inst_id,
                                            'arn': f"arn:aws:servicediscovery:{region}:{account_id}:service/{svc_id}/instance/{inst_id}",
                                            'name': inst_id,
                                            'region': region,
                                            'details': inst_details,
                                            'tags': {}
                                        })
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    return resources
