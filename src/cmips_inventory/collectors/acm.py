"""
ACM resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_acm_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect ACM resources: certificates.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    acm = session.client('acm', region_name=region)

    try:
        paginator = acm.get_paginator('list_certificates')
        for page in paginator.paginate():
            for cert_summary in page.get('CertificateSummaryList', []):
                cert_arn = cert_summary['CertificateArn']

                try:
                    # Get certificate details
                    cert_response = acm.describe_certificate(CertificateArn=cert_arn)
                    cert = cert_response.get('Certificate', {})

                    # Get tags
                    tags = {}
                    try:
                        tag_response = acm.list_tags_for_certificate(CertificateArn=cert_arn)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    domain_name = cert.get('DomainName', '')

                    resources.append({
                        'service': 'acm',
                        'type': 'certificate',
                        'id': cert_arn.split('/')[-1],
                        'arn': cert_arn,
                        'name': tags.get('Name') or domain_name,
                        'region': region,
                        'details': {
                            'domain_name': domain_name,
                            'subject_alternative_names': cert.get('SubjectAlternativeNames', []),
                            'status': cert.get('Status'),
                            'type': cert.get('Type'),
                            'key_algorithm': cert.get('KeyAlgorithm'),
                            'issuer': cert.get('Issuer'),
                            'created_at': str(cert.get('CreatedAt', '')),
                            'issued_at': str(cert.get('IssuedAt', '')) if cert.get('IssuedAt') else None,
                            'not_before': str(cert.get('NotBefore', '')) if cert.get('NotBefore') else None,
                            'not_after': str(cert.get('NotAfter', '')) if cert.get('NotAfter') else None,
                            'in_use_by': cert.get('InUseBy', []),
                            'renewal_eligibility': cert.get('RenewalEligibility'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
