"""
WAFv2 resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_wafv2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect WAFv2 resources: web ACLs, IP sets, regex pattern sets, rule groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    wafv2 = session.client('wafv2', region_name=region)

    # Determine scope based on region
    # CloudFront WAFs are in us-east-1 with CLOUDFRONT scope
    # Regional WAFs use REGIONAL scope
    scopes = ['REGIONAL']
    if region == 'us-east-1':
        scopes.append('CLOUDFRONT')

    for scope in scopes:
        scope_suffix = 'cloudfront' if scope == 'CLOUDFRONT' else 'regional'

        # Web ACLs
        try:
            response = wafv2.list_web_acls(Scope=scope)
            for acl in response.get('WebACLs', []):
                acl_name = acl['Name']
                acl_id = acl['Id']
                acl_arn = acl['ARN']

                try:
                    # Get ACL details
                    acl_response = wafv2.get_web_acl(
                        Name=acl_name,
                        Scope=scope,
                        Id=acl_id
                    )
                    acl_detail = acl_response.get('WebACL', {})

                    # Get tags
                    tags = {}
                    try:
                        tag_response = wafv2.list_tags_for_resource(ResourceARN=acl_arn)
                        for tag in tag_response.get('TagInfoForResource', {}).get('TagList', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'wafv2',
                        'type': f'web-acl-{scope_suffix}',
                        'id': acl_id,
                        'arn': acl_arn,
                        'name': acl_name,
                        'region': region if scope == 'REGIONAL' else 'global',
                        'details': {
                            'scope': scope,
                            'capacity': acl_detail.get('Capacity'),
                            'rules_count': len(acl_detail.get('Rules', [])),
                            'default_action': 'Allow' if acl_detail.get('DefaultAction', {}).get('Allow') else 'Block',
                            'visibility_config': acl_detail.get('VisibilityConfig'),
                            'managed_by_firewall_manager': acl_detail.get('ManagedByFirewallManager'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
        except Exception:
            pass

        # IP Sets
        try:
            response = wafv2.list_ip_sets(Scope=scope)
            for ip_set in response.get('IPSets', []):
                ip_set_name = ip_set['Name']
                ip_set_id = ip_set['Id']
                ip_set_arn = ip_set['ARN']

                try:
                    # Get IP set details
                    ip_set_response = wafv2.get_ip_set(
                        Name=ip_set_name,
                        Scope=scope,
                        Id=ip_set_id
                    )
                    ip_set_detail = ip_set_response.get('IPSet', {})

                    # Get tags
                    tags = {}
                    try:
                        tag_response = wafv2.list_tags_for_resource(ResourceARN=ip_set_arn)
                        for tag in tag_response.get('TagInfoForResource', {}).get('TagList', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'wafv2',
                        'type': f'ip-set-{scope_suffix}',
                        'id': ip_set_id,
                        'arn': ip_set_arn,
                        'name': ip_set_name,
                        'region': region if scope == 'REGIONAL' else 'global',
                        'details': {
                            'scope': scope,
                            'description': ip_set_detail.get('Description'),
                            'ip_address_version': ip_set_detail.get('IPAddressVersion'),
                            'addresses_count': len(ip_set_detail.get('Addresses', [])),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
        except Exception:
            pass

        # Rule Groups
        try:
            response = wafv2.list_rule_groups(Scope=scope)
            for rg in response.get('RuleGroups', []):
                rg_name = rg['Name']
                rg_id = rg['Id']
                rg_arn = rg['ARN']

                try:
                    # Get rule group details
                    rg_response = wafv2.get_rule_group(
                        Name=rg_name,
                        Scope=scope,
                        Id=rg_id
                    )
                    rg_detail = rg_response.get('RuleGroup', {})

                    # Get tags
                    tags = {}
                    try:
                        tag_response = wafv2.list_tags_for_resource(ResourceARN=rg_arn)
                        for tag in tag_response.get('TagInfoForResource', {}).get('TagList', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'wafv2',
                        'type': f'rule-group-{scope_suffix}',
                        'id': rg_id,
                        'arn': rg_arn,
                        'name': rg_name,
                        'region': region if scope == 'REGIONAL' else 'global',
                        'details': {
                            'scope': scope,
                            'description': rg_detail.get('Description'),
                            'capacity': rg_detail.get('Capacity'),
                            'rules_count': len(rg_detail.get('Rules', [])),
                            'visibility_config': rg_detail.get('VisibilityConfig'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
        except Exception:
            pass

        # Regex Pattern Sets
        try:
            response = wafv2.list_regex_pattern_sets(Scope=scope)
            for rps in response.get('RegexPatternSets', []):
                rps_name = rps['Name']
                rps_id = rps['Id']
                rps_arn = rps['ARN']

                try:
                    # Get regex pattern set details
                    rps_response = wafv2.get_regex_pattern_set(
                        Name=rps_name,
                        Scope=scope,
                        Id=rps_id
                    )
                    rps_detail = rps_response.get('RegexPatternSet', {})

                    # Get tags
                    tags = {}
                    try:
                        tag_response = wafv2.list_tags_for_resource(ResourceARN=rps_arn)
                        for tag in tag_response.get('TagInfoForResource', {}).get('TagList', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'wafv2',
                        'type': f'regex-pattern-set-{scope_suffix}',
                        'id': rps_id,
                        'arn': rps_arn,
                        'name': rps_name,
                        'region': region if scope == 'REGIONAL' else 'global',
                        'details': {
                            'scope': scope,
                            'description': rps_detail.get('Description'),
                            'patterns_count': len(rps_detail.get('RegularExpressionList', [])),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
        except Exception:
            pass

    return resources
