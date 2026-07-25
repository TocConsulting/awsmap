"""
AWS Simple Email Service v2 (SESv2) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_sesv2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS SESv2 resources: email identities, configuration sets, contact lists, templates, and IP pools.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ses = session.client('sesv2', region_name=region)

    # Email Identities
    try:
        paginator = ses.get_paginator('list_email_identities')
        for page in paginator.paginate():
            for identity in page.get('EmailIdentities', []):
                identity_name = identity['IdentityName']
                identity_type = identity.get('IdentityType', 'UNKNOWN')

                details = {
                    'identity_type': identity_type,
                    'sending_enabled': identity.get('SendingEnabled'),
                    'verification_status': identity.get('VerificationStatus'),
                }

                # Get additional details
                try:
                    identity_info = ses.get_email_identity(EmailIdentity=identity_name)
                    details['dkim_attributes'] = {
                        'signing_enabled': identity_info.get('DkimAttributes', {}).get('SigningEnabled'),
                        'status': identity_info.get('DkimAttributes', {}).get('Status'),
                        'signing_attributes_origin': identity_info.get('DkimAttributes', {}).get('SigningAttributesOrigin'),
                    }
                    details['mail_from_attributes'] = {
                        'mail_from_domain': identity_info.get('MailFromAttributes', {}).get('MailFromDomain'),
                        'mail_from_domain_status': identity_info.get('MailFromAttributes', {}).get('MailFromDomainStatus'),
                    }
                    details['policies'] = list(identity_info.get('Policies', {}).keys())
                    details['configuration_set_name'] = identity_info.get('ConfigurationSetName')
                    tags = {t['Key']: t['Value'] for t in identity_info.get('Tags', [])}
                except Exception:
                    tags = {}

                resources.append({
                    'service': 'sesv2',
                    'type': 'email-identity',
                    'id': identity_name,
                    'arn': f"arn:aws:ses:{region}:{account_id}:identity/{identity_name}",
                    'name': identity_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Configuration Sets
    try:
        paginator = ses.get_paginator('list_configuration_sets')
        for page in paginator.paginate():
            for config_set in page.get('ConfigurationSets', []):
                config_set_name = config_set

                details = {}

                # Get additional details
                try:
                    cs_info = ses.get_configuration_set(ConfigurationSetName=config_set_name)
                    details['tracking_options'] = cs_info.get('TrackingOptions', {}).get('CustomRedirectDomain')
                    details['delivery_options'] = {
                        'tls_policy': cs_info.get('DeliveryOptions', {}).get('TlsPolicy'),
                        'sending_pool_name': cs_info.get('DeliveryOptions', {}).get('SendingPoolName'),
                    }
                    details['reputation_options'] = {
                        'reputation_metrics_enabled': cs_info.get('ReputationOptions', {}).get('ReputationMetricsEnabled'),
                        'last_fresh_start': str(cs_info.get('ReputationOptions', {}).get('LastFreshStart', '')),
                    }
                    details['sending_options'] = {
                        'sending_enabled': cs_info.get('SendingOptions', {}).get('SendingEnabled'),
                    }
                    details['suppression_options'] = cs_info.get('SuppressionOptions', {}).get('SuppressedReasons', [])
                    tags = {t['Key']: t['Value'] for t in cs_info.get('Tags', [])}
                except Exception:
                    tags = {}

                resources.append({
                    'service': 'sesv2',
                    'type': 'configuration-set',
                    'id': config_set_name,
                    'arn': f"arn:aws:ses:{region}:{account_id}:configuration-set/{config_set_name}",
                    'name': config_set_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Contact Lists
    try:
        paginator = ses.get_paginator('list_contact_lists')
        for page in paginator.paginate():
            for contact_list in page.get('ContactLists', []):
                list_name = contact_list['ContactListName']

                details = {
                    'last_updated_timestamp': str(contact_list.get('LastUpdatedTimestamp', '')),
                }

                # Get additional details
                try:
                    cl_info = ses.get_contact_list(ContactListName=list_name)
                    details['description'] = cl_info.get('Description')
                    details['topics'] = [t.get('TopicName') for t in cl_info.get('Topics', [])]
                    details['created_timestamp'] = str(cl_info.get('CreatedTimestamp', ''))
                    tags = {t['Key']: t['Value'] for t in cl_info.get('Tags', [])}
                except Exception:
                    tags = {}

                resources.append({
                    'service': 'sesv2',
                    'type': 'contact-list',
                    'id': list_name,
                    'arn': f"arn:aws:ses:{region}:{account_id}:contact-list/{list_name}",
                    'name': list_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Email Templates
    try:
        paginator = ses.get_paginator('list_email_templates')
        for page in paginator.paginate():
            for template in page.get('TemplatesMetadata', []):
                template_name = template['TemplateName']

                details = {
                    'created_timestamp': str(template.get('CreatedTimestamp', '')),
                }

                resources.append({
                    'service': 'sesv2',
                    'type': 'email-template',
                    'id': template_name,
                    'arn': f"arn:aws:ses:{region}:{account_id}:template/{template_name}",
                    'name': template_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Dedicated IP Pools
    try:
        paginator = ses.get_paginator('list_dedicated_ip_pools')
        for page in paginator.paginate():
            for pool_name in page.get('DedicatedIpPools', []):
                details = {}

                # Get pool details
                try:
                    pool_info = ses.get_dedicated_ip_pool(PoolName=pool_name)
                    pool_data = pool_info.get('DedicatedIpPool', {})
                    details['scaling_mode'] = pool_data.get('ScalingMode')
                except Exception:
                    pass

                resources.append({
                    'service': 'sesv2',
                    'type': 'dedicated-ip-pool',
                    'id': pool_name,
                    'arn': f"arn:aws:ses:{region}:{account_id}:dedicated-ip-pool/{pool_name}",
                    'name': pool_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
