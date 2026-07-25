"""
AWS VPC Lattice resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_vpc_lattice_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS VPC Lattice resources: service networks, services, listeners,
    rules, target groups, associations, and access log subscriptions.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    lattice = session.client('vpc-lattice', region_name=region)

    # Service Networks
    try:
        paginator = lattice.get_paginator('list_service_networks')
        for page in paginator.paginate():
            for sn in page.get('items', []):
                sn_id = sn['id']
                sn_arn = sn['arn']
                sn_name = sn.get('name', sn_id)

                details = {
                    'status': sn.get('status'),
                    'number_of_associated_services': sn.get('numberOfAssociatedServices'),
                    'number_of_associated_vpcs': sn.get('numberOfAssociatedVPCs'),
                    'created_at': str(sn.get('createdAt', '')),
                    'last_updated_at': str(sn.get('lastUpdatedAt', '')),
                }

                # Get full details
                try:
                    sn_detail = lattice.get_service_network(serviceNetworkIdentifier=sn_id)
                    details['auth_type'] = sn_detail.get('authType')
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = lattice.list_tags_for_resource(resourceArn=sn_arn)
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'vpc-lattice',
                    'type': 'service-network',
                    'id': sn_id,
                    'arn': sn_arn,
                    'name': sn_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })

                # VPC Associations for this service network
                try:
                    vpc_paginator = lattice.get_paginator('list_service_network_vpc_associations')
                    for vpc_page in vpc_paginator.paginate(serviceNetworkIdentifier=sn_id):
                        for assoc in vpc_page.get('items', []):
                            assoc_id = assoc['id']
                            assoc_arn = assoc['arn']

                            assoc_details = {
                                'service_network_id': sn_id,
                                'service_network_name': sn_name,
                                'vpc_id': assoc.get('vpcId'),
                                'status': assoc.get('status'),
                                'created_at': str(assoc.get('createdAt', '')),
                                'last_updated_at': str(assoc.get('lastUpdatedAt', '')),
                            }

                            assoc_tags = {}
                            try:
                                assoc_tag_response = lattice.list_tags_for_resource(resourceArn=assoc_arn)
                                assoc_tags = assoc_tag_response.get('tags', {})
                            except Exception:
                                pass

                            resources.append({
                                'service': 'vpc-lattice',
                                'type': 'service-network-vpc-association',
                                'id': assoc_id,
                                'arn': assoc_arn,
                                'name': f"{sn_name}-{assoc.get('vpcId', assoc_id)[:12]}",
                                'region': region,
                                'details': assoc_details,
                                'tags': assoc_tags
                            })
                except Exception:
                    pass

                # Service Associations for this service network
                try:
                    svc_paginator = lattice.get_paginator('list_service_network_service_associations')
                    for svc_page in svc_paginator.paginate(serviceNetworkIdentifier=sn_id):
                        for assoc in svc_page.get('items', []):
                            assoc_id = assoc['id']
                            assoc_arn = assoc['arn']

                            assoc_details = {
                                'service_network_id': sn_id,
                                'service_network_name': sn_name,
                                'service_id': assoc.get('serviceId'),
                                'service_name': assoc.get('serviceName'),
                                'service_arn': assoc.get('serviceArn'),
                                'status': assoc.get('status'),
                                'dns_name': assoc.get('dnsEntry', {}).get('domainName'),
                                'hosted_zone_id': assoc.get('dnsEntry', {}).get('hostedZoneId'),
                                'created_at': str(assoc.get('createdAt', '')),
                            }

                            assoc_tags = {}
                            try:
                                assoc_tag_response = lattice.list_tags_for_resource(resourceArn=assoc_arn)
                                assoc_tags = assoc_tag_response.get('tags', {})
                            except Exception:
                                pass

                            resources.append({
                                'service': 'vpc-lattice',
                                'type': 'service-network-service-association',
                                'id': assoc_id,
                                'arn': assoc_arn,
                                'name': f"{sn_name}-{assoc.get('serviceName', assoc_id)[:20]}",
                                'region': region,
                                'details': assoc_details,
                                'tags': assoc_tags
                            })
                except Exception:
                    pass
    except Exception:
        pass

    # Services
    try:
        paginator = lattice.get_paginator('list_services')
        for page in paginator.paginate():
            for svc in page.get('items', []):
                svc_id = svc['id']
                svc_arn = svc['arn']
                svc_name = svc.get('name', svc_id)

                details = {
                    'status': svc.get('status'),
                    'dns_name': svc.get('dnsEntry', {}).get('domainName'),
                    'hosted_zone_id': svc.get('dnsEntry', {}).get('hostedZoneId'),
                    'custom_domain_name': svc.get('customDomainName'),
                    'created_at': str(svc.get('createdAt', '')),
                    'last_updated_at': str(svc.get('lastUpdatedAt', '')),
                }

                # Get full details
                try:
                    svc_detail = lattice.get_service(serviceIdentifier=svc_id)
                    details['auth_type'] = svc_detail.get('authType')
                    details['certificate_arn'] = svc_detail.get('certificateArn')
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = lattice.list_tags_for_resource(resourceArn=svc_arn)
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'vpc-lattice',
                    'type': 'service',
                    'id': svc_id,
                    'arn': svc_arn,
                    'name': svc_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })

                # Listeners for this service
                try:
                    listener_paginator = lattice.get_paginator('list_listeners')
                    for listener_page in listener_paginator.paginate(serviceIdentifier=svc_id):
                        for listener in listener_page.get('items', []):
                            listener_id = listener['id']
                            listener_arn = listener['arn']
                            listener_name = listener.get('name', listener_id)

                            listener_details = {
                                'service_id': svc_id,
                                'service_name': svc_name,
                                'protocol': listener.get('protocol'),
                                'port': listener.get('port'),
                                'created_at': str(listener.get('createdAt', '')),
                                'last_updated_at': str(listener.get('lastUpdatedAt', '')),
                            }

                            listener_tags = {}
                            try:
                                listener_tag_response = lattice.list_tags_for_resource(resourceArn=listener_arn)
                                listener_tags = listener_tag_response.get('tags', {})
                            except Exception:
                                pass

                            resources.append({
                                'service': 'vpc-lattice',
                                'type': 'listener',
                                'id': listener_id,
                                'arn': listener_arn,
                                'name': listener_name,
                                'region': region,
                                'details': listener_details,
                                'tags': listener_tags
                            })

                            # Rules for this listener
                            try:
                                rule_paginator = lattice.get_paginator('list_rules')
                                for rule_page in rule_paginator.paginate(
                                    serviceIdentifier=svc_id,
                                    listenerIdentifier=listener_id
                                ):
                                    for rule in rule_page.get('items', []):
                                        rule_id = rule['id']
                                        rule_arn = rule['arn']
                                        rule_name = rule.get('name', rule_id)

                                        rule_details = {
                                            'service_id': svc_id,
                                            'service_name': svc_name,
                                            'listener_id': listener_id,
                                            'listener_name': listener_name,
                                            'priority': rule.get('priority'),
                                            'is_default': rule.get('isDefault'),
                                            'created_at': str(rule.get('createdAt', '')),
                                            'last_updated_at': str(rule.get('lastUpdatedAt', '')),
                                        }

                                        rule_tags = {}
                                        try:
                                            rule_tag_response = lattice.list_tags_for_resource(resourceArn=rule_arn)
                                            rule_tags = rule_tag_response.get('tags', {})
                                        except Exception:
                                            pass

                                        resources.append({
                                            'service': 'vpc-lattice',
                                            'type': 'rule',
                                            'id': rule_id,
                                            'arn': rule_arn,
                                            'name': rule_name,
                                            'region': region,
                                            'details': rule_details,
                                            'tags': rule_tags
                                        })
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # Target Groups
    try:
        paginator = lattice.get_paginator('list_target_groups')
        for page in paginator.paginate():
            for tg in page.get('items', []):
                tg_id = tg['id']
                tg_arn = tg['arn']
                tg_name = tg.get('name', tg_id)

                details = {
                    'status': tg.get('status'),
                    'type': tg.get('type'),
                    'ip_address_type': tg.get('ipAddressType'),
                    'protocol': tg.get('protocol'),
                    'port': tg.get('port'),
                    'vpc_id': tg.get('vpcIdentifier'),
                    'lambda_event_structure_version': tg.get('lambdaEventStructureVersion'),
                    'created_at': str(tg.get('createdAt', '')),
                    'last_updated_at': str(tg.get('lastUpdatedAt', '')),
                    'service_arns': tg.get('serviceArns', []),
                }

                # Get full details including health check
                try:
                    tg_detail = lattice.get_target_group(targetGroupIdentifier=tg_id)
                    config = tg_detail.get('config', {})
                    details['protocol_version'] = config.get('protocolVersion')
                    details['lambda_event_structure_version'] = config.get('lambdaEventStructureVersion')

                    hc = config.get('healthCheck', {})
                    if hc:
                        details['health_check_enabled'] = hc.get('enabled')
                        details['health_check_protocol'] = hc.get('protocol')
                        details['health_check_port'] = hc.get('port')
                        details['health_check_path'] = hc.get('path')
                        details['health_check_interval'] = hc.get('healthCheckIntervalSeconds')
                        details['health_check_timeout'] = hc.get('healthCheckTimeoutSeconds')
                        details['healthy_threshold'] = hc.get('healthyThresholdCount')
                        details['unhealthy_threshold'] = hc.get('unhealthyThresholdCount')
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = lattice.list_tags_for_resource(resourceArn=tg_arn)
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'vpc-lattice',
                    'type': 'target-group',
                    'id': tg_id,
                    'arn': tg_arn,
                    'name': tg_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Access Log Subscriptions
    try:
        paginator = lattice.get_paginator('list_access_log_subscriptions')
        for page in paginator.paginate():
            for sub in page.get('items', []):
                sub_id = sub['id']
                sub_arn = sub['arn']

                details = {
                    'resource_id': sub.get('resourceId'),
                    'resource_arn': sub.get('resourceArn'),
                    'destination_arn': sub.get('destinationArn'),
                    'created_at': str(sub.get('createdAt', '')),
                    'last_updated_at': str(sub.get('lastUpdatedAt', '')),
                }

                # Get tags
                tags = {}
                try:
                    tag_response = lattice.list_tags_for_resource(resourceArn=sub_arn)
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'vpc-lattice',
                    'type': 'access-log-subscription',
                    'id': sub_id,
                    'arn': sub_arn,
                    'name': sub_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
