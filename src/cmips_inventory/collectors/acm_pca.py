"""
AWS Private Certificate Authority (ACM-PCA) resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_acm_pca_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Private Certificate Authority resources: certificate authorities and permissions.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    acm_pca = session.client('acm-pca', region_name=region)

    # Certificate Authorities
    try:
        paginator = acm_pca.get_paginator('list_certificate_authorities')
        for page in paginator.paginate():
            for ca in page.get('CertificateAuthorities', []):
                ca_arn = ca['Arn']
                ca_id = ca_arn.split('/')[-1]

                # Get CA config
                ca_config = ca.get('CertificateAuthorityConfiguration', {})
                subject = ca_config.get('Subject', {})

                details = {
                    'type': ca.get('Type'),
                    'status': ca.get('Status'),
                    'key_algorithm': ca_config.get('KeyAlgorithm'),
                    'signing_algorithm': ca_config.get('SigningAlgorithm'),
                    'subject_common_name': subject.get('CommonName'),
                    'subject_organization': subject.get('Organization'),
                    'subject_country': subject.get('Country'),
                    'subject_state': subject.get('State'),
                    'subject_locality': subject.get('Locality'),
                    'created_at': str(ca.get('CreatedAt', '')),
                    'last_state_change_at': str(ca.get('LastStateChangeAt', '')),
                    'not_before': str(ca.get('NotBefore', '')),
                    'not_after': str(ca.get('NotAfter', '')),
                    'failure_reason': ca.get('FailureReason'),
                    'serial': ca.get('Serial'),
                    'key_storage_security_standard': ca.get('KeyStorageSecurityStandard'),
                    'usage_mode': ca.get('UsageMode'),
                }

                # Revocation config
                revocation_config = ca.get('RevocationConfiguration', {})
                crl_config = revocation_config.get('CrlConfiguration', {})
                if crl_config:
                    details['crl_enabled'] = crl_config.get('Enabled')
                    details['crl_s3_bucket'] = crl_config.get('S3BucketName')
                    details['crl_expiration_days'] = crl_config.get('ExpirationInDays')

                ocsp_config = revocation_config.get('OcspConfiguration', {})
                if ocsp_config:
                    details['ocsp_enabled'] = ocsp_config.get('Enabled')
                    details['ocsp_custom_cname'] = ocsp_config.get('OcspCustomCname')

                # Get tags
                tags = {}
                try:
                    tag_paginator = acm_pca.get_paginator('list_tags')
                    for tag_page in tag_paginator.paginate(CertificateAuthorityArn=ca_arn):
                        for tag in tag_page.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'acm-pca',
                    'type': 'certificate-authority',
                    'id': ca_id,
                    'arn': ca_arn,
                    'name': subject.get('CommonName', ca_id),
                    'region': region,
                    'details': details,
                    'tags': tags
                })

                # Permissions for this CA
                try:
                    perm_paginator = acm_pca.get_paginator('list_permissions')
                    for perm_page in perm_paginator.paginate(CertificateAuthorityArn=ca_arn):
                        for perm in perm_page.get('Permissions', []):
                            perm_principal = perm.get('Principal', '')
                            perm_source_account = perm.get('SourceAccount', '')

                            perm_details = {
                                'certificate_authority_arn': ca_arn,
                                'principal': perm_principal,
                                'source_account': perm_source_account,
                                'actions': perm.get('Actions', []),
                                'policy': perm.get('Policy'),
                                'created_at': str(perm.get('CreatedAt', '')),
                            }

                            resources.append({
                                'service': 'acm-pca',
                                'type': 'permission',
                                'id': f"{ca_id}-{perm_principal}",
                                'arn': f"{ca_arn}/permission/{perm_source_account}",
                                'name': f"{subject.get('CommonName', ca_id)}-{perm_principal[:20]}",
                                'region': region,
                                'details': perm_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
