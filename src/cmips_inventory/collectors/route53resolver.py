"""
AWS Route 53 Resolver resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_route53resolver_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Route 53 Resolver resources: endpoints, rules, query log configs, firewall rule groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    resolver = session.client('route53resolver', region_name=region)

    # Resolver Endpoints
    try:
        paginator = resolver.get_paginator('list_resolver_endpoints')
        for page in paginator.paginate():
            for endpoint in page.get('ResolverEndpoints', []):
                endpoint_id = endpoint.get('Id', '')
                endpoint_arn = endpoint.get('Arn', '')
                endpoint_name = endpoint.get('Name', endpoint_id)

                details = {
                    'direction': endpoint.get('Direction'),
                    'status': endpoint.get('Status'),
                    'host_vpc_id': endpoint.get('HostVPCId'),
                    'ip_address_count': endpoint.get('IpAddressCount'),
                    'resolver_endpoint_type': endpoint.get('ResolverEndpointType'),
                }

                resources.append({
                    'service': 'route53resolver',
                    'type': 'resolver-endpoint',
                    'id': endpoint_id,
                    'arn': endpoint_arn,
                    'name': endpoint_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Resolver Rules
    try:
        paginator = resolver.get_paginator('list_resolver_rules')
        for page in paginator.paginate():
            for rule in page.get('ResolverRules', []):
                # Skip system rules
                if rule.get('OwnerId') == 'Route 53 Resolver':
                    continue

                rule_id = rule.get('Id', '')
                rule_arn = rule.get('Arn', '')
                rule_name = rule.get('Name', rule_id)

                details = {
                    'domain_name': rule.get('DomainName'),
                    'rule_type': rule.get('RuleType'),
                    'status': rule.get('Status'),
                    'resolver_endpoint_id': rule.get('ResolverEndpointId'),
                }

                resources.append({
                    'service': 'route53resolver',
                    'type': 'resolver-rule',
                    'id': rule_id,
                    'arn': rule_arn,
                    'name': rule_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Query Log Configs
    try:
        paginator = resolver.get_paginator('list_resolver_query_log_configs')
        for page in paginator.paginate():
            for config in page.get('ResolverQueryLogConfigs', []):
                config_id = config.get('Id', '')
                config_arn = config.get('Arn', '')
                config_name = config.get('Name', config_id)

                details = {
                    'status': config.get('Status'),
                    'destination_arn': config.get('DestinationArn'),
                    'association_count': config.get('AssociationCount'),
                }

                resources.append({
                    'service': 'route53resolver',
                    'type': 'query-log-config',
                    'id': config_id,
                    'arn': config_arn,
                    'name': config_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Firewall Rule Groups
    try:
        paginator = resolver.get_paginator('list_firewall_rule_groups')
        for page in paginator.paginate():
            for group in page.get('FirewallRuleGroups', []):
                # Skip shared rule groups we don't own
                if group.get('OwnerId') != account_id:
                    continue

                group_id = group.get('Id', '')
                group_arn = group.get('Arn', '')
                group_name = group.get('Name', group_id)

                details = {
                    'share_status': group.get('ShareStatus'),
                }

                resources.append({
                    'service': 'route53resolver',
                    'type': 'firewall-rule-group',
                    'id': group_id,
                    'arn': group_arn,
                    'name': group_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Firewall Domain Lists (skip AWS managed domain lists)
    try:
        paginator = resolver.get_paginator('list_firewall_domain_lists')
        for page in paginator.paginate():
            for domain_list in page.get('FirewallDomainLists', []):
                list_name = domain_list.get('Name', '')

                # Skip AWS managed domain lists (AWSManagedDomainsMalwareDomainList, etc.)
                if list_name.startswith('AWSManagedDomains'):
                    continue

                list_id = domain_list.get('Id', '')
                list_arn = domain_list.get('Arn', '')

                details = {
                    'managed_owner_name': domain_list.get('ManagedOwnerName'),
                }

                resources.append({
                    'service': 'route53resolver',
                    'type': 'firewall-domain-list',
                    'id': list_id,
                    'arn': list_arn,
                    'name': list_name or list_id,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
