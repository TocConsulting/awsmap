"""
AWS Organizations resource collector.

Note: This collector only returns data when run from the management account.
Member accounts will return empty results (AccessDeniedException is silently handled).
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_organizations_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Organizations resources: organization, accounts, OUs, policies,
    and delegated administrators.

    Args:
        session: boto3.Session to use
        region: AWS region (not used - Organizations is global)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    organizations = session.client('organizations', region_name='us-east-1')

    # First, get organization info to verify we have access
    org_id = None
    try:
        org_response = organizations.describe_organization()
        org = org_response.get('Organization', {})
        org_id = org.get('Id')
        org_arn = org.get('Arn', f"arn:aws:organizations::{account_id}:organization/{org_id}")

        resources.append({
            'service': 'organizations',
            'type': 'organization',
            'id': org_id,
            'arn': org_arn,
            'name': org_id,
            'region': 'global',
            'details': {
                'master_account_id': org.get('MasterAccountId'),
                'master_account_arn': org.get('MasterAccountArn'),
                'master_account_email': org.get('MasterAccountEmail'),
                'feature_set': org.get('FeatureSet'),
                'available_policy_types': [p.get('Type') for p in org.get('AvailablePolicyTypes', [])],
            },
            'tags': {}
        })
    except Exception:
        # Not management account or no organization - return empty
        return []

    # Roots
    root_ids = []
    try:
        paginator = organizations.get_paginator('list_roots')
        for page in paginator.paginate():
            for root in page.get('Roots', []):
                root_id = root['Id']
                root_ids.append(root_id)
                root_arn = root.get('Arn', f"arn:aws:organizations::{account_id}:root/{org_id}/{root_id}")

                resources.append({
                    'service': 'organizations',
                    'type': 'root',
                    'id': root_id,
                    'arn': root_arn,
                    'name': root.get('Name', root_id),
                    'region': 'global',
                    'details': {
                        'policy_types': [p.get('Type') for p in root.get('PolicyTypes', [])],
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Organizational Units (recursive from roots)
    def collect_ous(parent_id):
        ous = []
        try:
            paginator = organizations.get_paginator('list_organizational_units_for_parent')
            for page in paginator.paginate(ParentId=parent_id):
                for ou in page.get('OrganizationalUnits', []):
                    ou_id = ou['Id']
                    ou_arn = ou.get('Arn', f"arn:aws:organizations::{account_id}:ou/{org_id}/{ou_id}")

                    # Get tags
                    tags = {}
                    try:
                        tag_response = organizations.list_tags_for_resource(ResourceId=ou_id)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    ous.append({
                        'service': 'organizations',
                        'type': 'organizational-unit',
                        'id': ou_id,
                        'arn': ou_arn,
                        'name': ou.get('Name', ou_id),
                        'region': 'global',
                        'details': {
                            'parent_id': parent_id,
                        },
                        'tags': tags
                    })

                    # Recurse into child OUs
                    ous.extend(collect_ous(ou_id))
        except Exception:
            pass
        return ous

    for root_id in root_ids:
        resources.extend(collect_ous(root_id))

    # Accounts
    try:
        paginator = organizations.get_paginator('list_accounts')
        for page in paginator.paginate():
            for acct in page.get('Accounts', []):
                acct_id = acct['Id']
                acct_arn = acct.get('Arn', f"arn:aws:organizations::{account_id}:account/{org_id}/{acct_id}")

                # Get tags
                tags = {}
                try:
                    tag_response = organizations.list_tags_for_resource(ResourceId=acct_id)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'organizations',
                    'type': 'account',
                    'id': acct_id,
                    'arn': acct_arn,
                    'name': acct.get('Name', acct_id),
                    'region': 'global',
                    'details': {
                        'email': acct.get('Email'),
                        'status': acct.get('Status'),
                        'joined_method': acct.get('JoinedMethod'),
                        'joined_timestamp': str(acct.get('JoinedTimestamp', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Policies (all types)
    policy_types = ['SERVICE_CONTROL_POLICY', 'TAG_POLICY', 'BACKUP_POLICY', 'AISERVICES_OPT_OUT_POLICY']
    for policy_type in policy_types:
        try:
            paginator = organizations.get_paginator('list_policies')
            for page in paginator.paginate(Filter=policy_type):
                for policy in page.get('Policies', []):
                    policy_id = policy['Id']
                    policy_arn = policy.get('Arn', f"arn:aws:organizations::{account_id}:policy/{org_id}/{policy_type.lower()}/{policy_id}")

                    # Skip AWS managed policies
                    if policy.get('AwsManaged', False):
                        continue

                    # Get policy details
                    details = {
                        'type': policy.get('Type'),
                        'aws_managed': policy.get('AwsManaged'),
                        'description': policy.get('Description'),
                    }

                    try:
                        policy_response = organizations.describe_policy(PolicyId=policy_id)
                        policy_detail = policy_response.get('Policy', {}).get('PolicySummary', {})
                        details['description'] = policy_detail.get('Description')
                    except Exception:
                        pass

                    # Get targets
                    try:
                        targets_response = organizations.list_targets_for_policy(PolicyId=policy_id)
                        targets = targets_response.get('Targets', [])
                        details['targets_count'] = len(targets)
                        details['target_types'] = list(set(t.get('Type') for t in targets))
                    except Exception:
                        pass

                    resources.append({
                        'service': 'organizations',
                        'type': 'policy',
                        'id': policy_id,
                        'arn': policy_arn,
                        'name': policy.get('Name', policy_id),
                        'region': 'global',
                        'details': details,
                        'tags': {}
                    })
        except Exception:
            pass

    # Delegated Administrators
    try:
        paginator = organizations.get_paginator('list_delegated_administrators')
        for page in paginator.paginate():
            for admin in page.get('DelegatedAdministrators', []):
                admin_id = admin['Id']

                # Get delegated services
                services = []
                try:
                    svc_response = organizations.list_delegated_services_for_account(AccountId=admin_id)
                    services = [s.get('ServicePrincipal') for s in svc_response.get('DelegatedServices', [])]
                except Exception:
                    pass

                resources.append({
                    'service': 'organizations',
                    'type': 'delegated-administrator',
                    'id': admin_id,
                    'arn': admin.get('Arn', f"arn:aws:organizations::{account_id}:account/{org_id}/{admin_id}"),
                    'name': admin.get('Name', admin_id),
                    'region': 'global',
                    'details': {
                        'email': admin.get('Email'),
                        'status': admin.get('Status'),
                        'joined_method': admin.get('JoinedMethod'),
                        'joined_timestamp': str(admin.get('JoinedTimestamp', '')),
                        'delegation_enabled_date': str(admin.get('DelegationEnabledDate', '')),
                        'delegated_services': services,
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
