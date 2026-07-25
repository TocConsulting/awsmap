"""
IAM resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_iam_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect IAM resources: users, groups, roles, policies, instance profiles.

    Args:
        session: boto3.Session to use
        region: Not used for IAM (global service)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    iam = session.client('iam')

    # IAM Users
    try:
        paginator = iam.get_paginator('list_users')
        for page in paginator.paginate():
            for user in page.get('Users', []):
                user_name = user['UserName']

                # Get user tags
                tags = {}
                try:
                    tag_response = iam.list_user_tags(UserName=user_name)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                # Get MFA devices
                mfa_enabled = False
                try:
                    mfa_response = iam.list_mfa_devices(UserName=user_name)
                    mfa_enabled = len(mfa_response.get('MFADevices', [])) > 0
                except Exception:
                    pass

                # Get access keys
                access_keys = []
                try:
                    ak_response = iam.list_access_keys(UserName=user_name)
                    for key in ak_response.get('AccessKeyMetadata', []):
                        access_keys.append({
                            'id': key.get('AccessKeyId'),
                            'status': key.get('Status'),
                            'create_date': str(key.get('CreateDate', ''))
                        })
                except Exception:
                    pass

                # Get attached policies
                attached_policies = []
                try:
                    ap_paginator = iam.get_paginator('list_attached_user_policies')
                    for ap_page in ap_paginator.paginate(UserName=user_name):
                        for pol in ap_page.get('AttachedPolicies', []):
                            attached_policies.append(pol['PolicyArn'])
                except Exception:
                    pass

                # Get group memberships
                groups = []
                try:
                    grp_paginator = iam.get_paginator('list_groups_for_user')
                    for grp_page in grp_paginator.paginate(UserName=user_name):
                        for grp in grp_page.get('Groups', []):
                            groups.append(grp['GroupName'])
                except Exception:
                    pass

                resources.append({
                    'service': 'iam',
                    'type': 'user',
                    'id': user.get('UserId'),
                    'arn': user['Arn'],
                    'name': user_name,
                    'region': 'global',
                    'details': {
                        'path': user.get('Path'),
                        'create_date': str(user.get('CreateDate', '')),
                        'password_last_used': str(user.get('PasswordLastUsed', '')),
                        'mfa_enabled': mfa_enabled,
                        'access_keys_count': len(access_keys),
                        'attached_policies': attached_policies,
                        'groups': groups,
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # IAM Groups
    try:
        paginator = iam.get_paginator('list_groups')
        for page in paginator.paginate():
            for group in page.get('Groups', []):
                group_name = group['GroupName']

                # Get attached policies
                attached_policies = []
                try:
                    ap_paginator = iam.get_paginator('list_attached_group_policies')
                    for ap_page in ap_paginator.paginate(GroupName=group_name):
                        for pol in ap_page.get('AttachedPolicies', []):
                            attached_policies.append(pol['PolicyArn'])
                except Exception:
                    pass

                resources.append({
                    'service': 'iam',
                    'type': 'group',
                    'id': group.get('GroupId'),
                    'arn': group['Arn'],
                    'name': group_name,
                    'region': 'global',
                    'details': {
                        'path': group.get('Path'),
                        'create_date': str(group.get('CreateDate', '')),
                        'attached_policies': attached_policies,
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # IAM Roles
    try:
        paginator = iam.get_paginator('list_roles')
        for page in paginator.paginate():
            for role in page.get('Roles', []):
                role_name = role['RoleName']

                # Get role tags
                tags = {}
                try:
                    tag_response = iam.list_role_tags(RoleName=role_name)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                # Get attached policies
                attached_policies = []
                try:
                    ap_paginator = iam.get_paginator('list_attached_role_policies')
                    for ap_page in ap_paginator.paginate(RoleName=role_name):
                        for pol in ap_page.get('AttachedPolicies', []):
                            attached_policies.append(pol['PolicyArn'])
                except Exception:
                    pass

                # Trust policy (AssumeRolePolicyDocument) is returned by list_roles
                trust_policy = role.get('AssumeRolePolicyDocument', {})

                resources.append({
                    'service': 'iam',
                    'type': 'role',
                    'id': role.get('RoleId'),
                    'arn': role['Arn'],
                    'name': role_name,
                    'region': 'global',
                    'details': {
                        'path': role.get('Path'),
                        'create_date': str(role.get('CreateDate', '')),
                        'max_session_duration': role.get('MaxSessionDuration'),
                        'description': role.get('Description'),
                        'attached_policies': attached_policies,
                        'trust_policy': trust_policy,
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # IAM Policies (customer managed only)
    try:
        paginator = iam.get_paginator('list_policies')
        for page in paginator.paginate(Scope='Local'):
            for policy in page.get('Policies', []):
                policy_arn = policy['Arn']

                # Get policy tags
                tags = {}
                try:
                    tag_response = iam.list_policy_tags(PolicyArn=policy_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'iam',
                    'type': 'policy',
                    'id': policy.get('PolicyId'),
                    'arn': policy_arn,
                    'name': policy['PolicyName'],
                    'region': 'global',
                    'details': {
                        'path': policy.get('Path'),
                        'create_date': str(policy.get('CreateDate', '')),
                        'update_date': str(policy.get('UpdateDate', '')),
                        'attachment_count': policy.get('AttachmentCount'),
                        'default_version': policy.get('DefaultVersionId'),
                        'is_attachable': policy.get('IsAttachable'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Instance Profiles
    try:
        paginator = iam.get_paginator('list_instance_profiles')
        for page in paginator.paginate():
            for profile in page.get('InstanceProfiles', []):
                profile_name = profile['InstanceProfileName']

                # Get instance profile tags
                tags = {}
                try:
                    tag_response = iam.list_instance_profile_tags(InstanceProfileName=profile_name)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                roles = [r['RoleName'] for r in profile.get('Roles', [])]

                resources.append({
                    'service': 'iam',
                    'type': 'instance-profile',
                    'id': profile.get('InstanceProfileId'),
                    'arn': profile['Arn'],
                    'name': profile_name,
                    'region': 'global',
                    'details': {
                        'path': profile.get('Path'),
                        'create_date': str(profile.get('CreateDate', '')),
                        'roles': roles,
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # SAML Providers
    try:
        response = iam.list_saml_providers()
        for provider in response.get('SAMLProviderList', []):
            provider_arn = provider['Arn']
            provider_name = provider_arn.split('/')[-1]

            # Get SAML provider tags
            tags = {}
            try:
                tag_response = iam.list_saml_provider_tags(SAMLProviderArn=provider_arn)
                for tag in tag_response.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            resources.append({
                'service': 'iam',
                'type': 'saml-provider',
                'id': provider_arn,
                'arn': provider_arn,
                'name': provider_name,
                'region': 'global',
                'details': {
                    'create_date': str(provider.get('CreateDate', '')),
                    'valid_until': str(provider.get('ValidUntil', '')),
                },
                'tags': tags
            })
    except Exception:
        pass

    # OIDC Providers
    try:
        response = iam.list_open_id_connect_providers()
        for provider in response.get('OpenIDConnectProviderList', []):
            provider_arn = provider['Arn']

            # Get OIDC provider details
            details = {}
            tags = {}
            try:
                oidc_response = iam.get_open_id_connect_provider(OpenIDConnectProviderArn=provider_arn)
                details = {
                    'url': oidc_response.get('Url'),
                    'create_date': str(oidc_response.get('CreateDate', '')),
                    'client_ids': oidc_response.get('ClientIDList', []),
                }
                for tag in oidc_response.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            resources.append({
                'service': 'iam',
                'type': 'oidc-provider',
                'id': provider_arn,
                'arn': provider_arn,
                'name': details.get('url', provider_arn.split('/')[-1]),
                'region': 'global',
                'details': details,
                'tags': tags
            })
    except Exception:
        pass

    return resources
