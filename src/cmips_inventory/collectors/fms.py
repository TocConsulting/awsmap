"""
AWS Firewall Manager (FMS) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_fms_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Firewall Manager resources: policies, apps lists, protocols lists,
    and resource sets.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    fms = session.client('fms', region_name=region)

    # Check if FMS admin is configured
    try:
        fms.get_admin_account()
    except Exception:
        # Not an FMS admin account or FMS not configured
        return []

    # Policies
    try:
        paginator = fms.get_paginator('list_policies')
        for page in paginator.paginate():
            for policy in page.get('PolicyList', []):
                policy_id = policy['PolicyId']
                policy_name = policy.get('PolicyName', policy_id)
                policy_arn = policy['PolicyArn']

                details = {
                    'resource_type': policy.get('ResourceType'),
                    'security_service_type': policy.get('SecurityServiceType'),
                    'remediation_enabled': policy.get('RemediationEnabled'),
                    'delete_unused_fm_managed_resources': policy.get('DeleteUnusedFMManagedResources'),
                    'policy_status': policy.get('PolicyStatus'),
                }

                # Get full policy details
                try:
                    policy_detail = fms.get_policy(PolicyId=policy_id)
                    pol = policy_detail.get('Policy', {})
                    details['exclude_resource_tags'] = pol.get('ExcludeResourceTags')
                    details['resource_type_list'] = pol.get('ResourceTypeList', [])
                    details['resource_set_ids'] = pol.get('ResourceSetIds', [])

                    security_config = pol.get('SecurityServicePolicyData', {})
                    details['managed_service_data'] = security_config.get('ManagedServiceData')
                    details['policy_option'] = security_config.get('PolicyOption')
                except Exception:
                    pass

                resources.append({
                    'service': 'fms',
                    'type': 'policy',
                    'id': policy_id,
                    'arn': policy_arn,
                    'name': policy_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Apps Lists
    try:
        paginator = fms.get_paginator('list_apps_lists')
        for page in paginator.paginate(DefaultLists=False):
            for apps_list in page.get('AppsLists', []):
                list_id = apps_list['ListId']
                list_name = apps_list.get('ListName', list_id)
                list_arn = apps_list['ListArn']

                details = {
                    'create_time': str(apps_list.get('CreateTime', '')),
                    'last_update_time': str(apps_list.get('LastUpdateTime', '')),
                }

                # Get full list details
                try:
                    list_detail = fms.get_apps_list(ListId=list_id)
                    apps = list_detail.get('AppsList', {})
                    details['apps_count'] = len(apps.get('AppsList', []))
                    details['previous_apps_count'] = len(apps.get('PreviousAppsList', {}))
                except Exception:
                    pass

                resources.append({
                    'service': 'fms',
                    'type': 'apps-list',
                    'id': list_id,
                    'arn': list_arn,
                    'name': list_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Protocols Lists
    try:
        paginator = fms.get_paginator('list_protocols_lists')
        for page in paginator.paginate(DefaultLists=False):
            for protocols_list in page.get('ProtocolsLists', []):
                list_id = protocols_list['ListId']
                list_name = protocols_list.get('ListName', list_id)
                list_arn = protocols_list['ListArn']

                details = {
                    'create_time': str(protocols_list.get('CreateTime', '')),
                    'last_update_time': str(protocols_list.get('LastUpdateTime', '')),
                }

                # Get full list details
                try:
                    list_detail = fms.get_protocols_list(ListId=list_id)
                    protocols = list_detail.get('ProtocolsList', {})
                    details['protocols'] = protocols.get('ProtocolsList', [])
                    details['protocols_count'] = len(protocols.get('ProtocolsList', []))
                except Exception:
                    pass

                resources.append({
                    'service': 'fms',
                    'type': 'protocols-list',
                    'id': list_id,
                    'arn': list_arn,
                    'name': list_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Resource Sets
    try:
        paginator = fms.get_paginator('list_resource_sets')
        for page in paginator.paginate():
            for resource_set in page.get('ResourceSets', []):
                rs_id = resource_set['Id']
                rs_name = resource_set.get('Name', rs_id)

                details = {
                    'description': resource_set.get('Description'),
                    'resource_type_list': resource_set.get('ResourceTypeList', []),
                    'last_update_time': str(resource_set.get('LastUpdateTime', '')),
                }

                # Get full resource set details
                try:
                    rs_detail = fms.get_resource_set(Identifier=rs_id)
                    rs = rs_detail.get('ResourceSet', {})
                    details['update_token'] = rs.get('UpdateToken')
                except Exception:
                    pass

                # Construct ARN
                rs_arn = f"arn:aws:fms:{region}:{account_id}:resource-set/{rs_id}"

                resources.append({
                    'service': 'fms',
                    'type': 'resource-set',
                    'id': rs_id,
                    'arn': rs_arn,
                    'name': rs_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
