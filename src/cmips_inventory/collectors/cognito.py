"""
Cognito resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_cognito_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Cognito resources: user pools, identity pools.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []

    # Cognito User Pools
    cognito_idp = session.client('cognito-idp', region_name=region)
    try:
        paginator = cognito_idp.get_paginator('list_user_pools')
        for page in paginator.paginate(MaxResults=60):
            for pool in page.get('UserPools', []):
                pool_id = pool['Id']
                pool_name = pool['Name']

                try:
                    # Get pool details
                    pool_response = cognito_idp.describe_user_pool(UserPoolId=pool_id)
                    pool_detail = pool_response.get('UserPool', {})

                    # Tags are in the detail response
                    tags = pool_detail.get('UserPoolTags', {})

                    resources.append({
                        'service': 'cognito',
                        'type': 'user-pool',
                        'id': pool_id,
                        'arn': pool_detail.get('Arn', f"arn:aws:cognito-idp:{region}:{account_id}:userpool/{pool_id}"),
                        'name': pool_name,
                        'region': region,
                        'details': {
                            'status': pool_detail.get('Status'),
                            'creation_date': str(pool_detail.get('CreationDate', '')),
                            'last_modified_date': str(pool_detail.get('LastModifiedDate', '')),
                            'mfa_configuration': pool_detail.get('MfaConfiguration'),
                            'estimated_number_of_users': pool_detail.get('EstimatedNumberOfUsers'),
                            'email_configuration_set': pool_detail.get('EmailConfiguration', {}).get('EmailSendingAccount'),
                            'sms_configuration': bool(pool_detail.get('SmsConfiguration')),
                            'user_pool_add_ons': pool_detail.get('UserPoolAddOns'),
                            'domain': pool_detail.get('Domain'),
                            'custom_domain': pool_detail.get('CustomDomain'),
                        },
                        'tags': tags
                    })

                    # User Pool Clients
                    try:
                        client_paginator = cognito_idp.get_paginator('list_user_pool_clients')
                        for client_page in client_paginator.paginate(UserPoolId=pool_id, MaxResults=60):
                            for client in client_page.get('UserPoolClients', []):
                                client_id = client['ClientId']
                                client_name = client['ClientName']

                                resources.append({
                                    'service': 'cognito',
                                    'type': 'user-pool-client',
                                    'id': client_id,
                                    'arn': f"arn:aws:cognito-idp:{region}:{account_id}:userpool/{pool_id}/client/{client_id}",
                                    'name': client_name,
                                    'region': region,
                                    'details': {
                                        'user_pool_id': pool_id,
                                        'user_pool_name': pool_name,
                                    },
                                    'tags': {}
                                })
                    except Exception:
                        pass

                except Exception:
                    pass
    except Exception:
        pass

    # Cognito Identity Pools
    cognito_identity = session.client('cognito-identity', region_name=region)
    try:
        paginator = cognito_identity.get_paginator('list_identity_pools')
        for page in paginator.paginate(MaxResults=60):
            for pool in page.get('IdentityPools', []):
                pool_id = pool['IdentityPoolId']
                pool_name = pool['IdentityPoolName']

                try:
                    # Get pool details
                    pool_response = cognito_identity.describe_identity_pool(IdentityPoolId=pool_id)

                    # Get tags
                    tags = {}
                    try:
                        tag_response = cognito_identity.list_tags_for_resource(
                            ResourceArn=f"arn:aws:cognito-identity:{region}:{account_id}:identitypool/{pool_id}"
                        )
                        tags = tag_response.get('Tags', {})
                    except Exception:
                        pass

                    resources.append({
                        'service': 'cognito',
                        'type': 'identity-pool',
                        'id': pool_id,
                        'arn': f"arn:aws:cognito-identity:{region}:{account_id}:identitypool/{pool_id}",
                        'name': pool_name,
                        'region': region,
                        'details': {
                            'allow_unauthenticated_identities': pool_response.get('AllowUnauthenticatedIdentities'),
                            'allow_classic_flow': pool_response.get('AllowClassicFlow'),
                            'developer_provider_name': pool_response.get('DeveloperProviderName'),
                            'cognito_identity_providers': [
                                p.get('ProviderName') for p in pool_response.get('CognitoIdentityProviders', [])
                            ],
                            'supported_login_providers': list(pool_response.get('SupportedLoginProviders', {}).keys()),
                            'saml_provider_arns': pool_response.get('SamlProviderARNs', []),
                            'open_id_connect_provider_arns': pool_response.get('OpenIdConnectProviderARNs', []),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
