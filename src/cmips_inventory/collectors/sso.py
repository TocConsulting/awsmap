"""
IAM Identity Center (SSO) resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_sso_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect IAM Identity Center resources: instances, permission sets, users, groups.

    Note: IAM Identity Center is regional but only ONE instance can be active
    per AWS Organization. This collector only runs in the region where the
    instance is deployed.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sso_admin = session.client('sso-admin', region_name=region)

    # List Identity Center instances
    instances = []
    try:
        paginator = sso_admin.get_paginator('list_instances')
        for page in paginator.paginate():
            instances.extend(page.get('Instances', []))
    except Exception:
        pass

    for instance in instances:
        instance_arn = instance['InstanceArn']
        identity_store_id = instance.get('IdentityStoreId')

        # Get instance details
        resources.append({
            'service': 'sso',
            'type': 'instance',
            'id': instance_arn.split('/')[-1],
            'arn': instance_arn,
            'name': instance.get('Name') or f"sso-instance-{instance_arn.split('/')[-1][:8]}",
            'region': region,
            'details': {
                'identity_store_id': identity_store_id,
                'owner_account_id': instance.get('OwnerAccountId'),
                'status': instance.get('Status'),
                'created_date': str(instance.get('CreatedDate', '')),
            },
            'tags': {}
        })

        # Permission Sets for this instance
        try:
            ps_paginator = sso_admin.get_paginator('list_permission_sets')
            for ps_page in ps_paginator.paginate(InstanceArn=instance_arn):
                for ps_arn in ps_page.get('PermissionSets', []):
                    try:
                        ps_response = sso_admin.describe_permission_set(
                            InstanceArn=instance_arn,
                            PermissionSetArn=ps_arn
                        )
                        ps = ps_response.get('PermissionSet', {})

                        # Get tags
                        tags = {}
                        try:
                            tag_response = sso_admin.list_tags_for_resource(
                                InstanceArn=instance_arn,
                                ResourceArn=ps_arn
                            )
                            for tag in tag_response.get('Tags', []):
                                tags[tag.get('Key', '')] = tag.get('Value', '')
                        except Exception:
                            pass

                        resources.append({
                            'service': 'sso',
                            'type': 'permission-set',
                            'id': ps_arn.split('/')[-1],
                            'arn': ps_arn,
                            'name': ps.get('Name', ps_arn.split('/')[-1]),
                            'region': region,
                            'details': {
                                'instance_arn': instance_arn,
                                'description': ps.get('Description'),
                                'session_duration': ps.get('SessionDuration'),
                                'relay_state': ps.get('RelayState'),
                                'created_date': str(ps.get('CreatedDate', '')),
                            },
                            'tags': tags
                        })
                    except Exception:
                        pass
        except Exception:
            pass

        # Users and Groups from Identity Store
        if identity_store_id:
            identitystore = session.client('identitystore', region_name=region)

            # Users
            try:
                user_paginator = identitystore.get_paginator('list_users')
                for user_page in user_paginator.paginate(IdentityStoreId=identity_store_id):
                    for user in user_page.get('Users', []):
                        user_id = user['UserId']
                        user_name = user.get('UserName', user_id)

                        # Build display name
                        display_name = user.get('DisplayName')
                        if not display_name:
                            name_obj = user.get('Name', {})
                            if name_obj:
                                display_name = f"{name_obj.get('GivenName', '')} {name_obj.get('FamilyName', '')}".strip()

                        # Get primary email
                        emails = user.get('Emails', [])
                        primary_email = None
                        for email in emails:
                            if email.get('Primary'):
                                primary_email = email.get('Value')
                                break
                        if not primary_email and emails:
                            primary_email = emails[0].get('Value')

                        resources.append({
                            'service': 'sso',
                            'type': 'user',
                            'id': user_id,
                            'arn': f"arn:aws:identitystore::{account_id}:identitystore/{identity_store_id}/user/{user_id}",
                            'name': user_name,
                            'region': region,
                            'details': {
                                'identity_store_id': identity_store_id,
                                'display_name': display_name,
                                'email': primary_email,
                                'external_id': user.get('ExternalIds', [{}])[0].get('Id') if user.get('ExternalIds') else None,
                                'identity_provider': user.get('ExternalIds', [{}])[0].get('Issuer') if user.get('ExternalIds') else None,
                            },
                            'tags': {}
                        })
            except Exception:
                pass

            # Groups
            try:
                group_paginator = identitystore.get_paginator('list_groups')
                for group_page in group_paginator.paginate(IdentityStoreId=identity_store_id):
                    for group in group_page.get('Groups', []):
                        group_id = group['GroupId']
                        group_name = group.get('DisplayName', group_id)

                        resources.append({
                            'service': 'sso',
                            'type': 'group',
                            'id': group_id,
                            'arn': f"arn:aws:identitystore::{account_id}:identitystore/{identity_store_id}/group/{group_id}",
                            'name': group_name,
                            'region': region,
                            'details': {
                                'identity_store_id': identity_store_id,
                                'description': group.get('Description'),
                                'external_id': group.get('ExternalIds', [{}])[0].get('Id') if group.get('ExternalIds') else None,
                                'identity_provider': group.get('ExternalIds', [{}])[0].get('Issuer') if group.get('ExternalIds') else None,
                            },
                            'tags': {}
                        })
            except Exception:
                pass

    return resources
