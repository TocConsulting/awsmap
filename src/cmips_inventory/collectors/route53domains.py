"""
AWS Route 53 Domains resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_route53domains_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Route 53 Domains resources: registered domains.

    Note: Route 53 Domains is a global service accessed via us-east-1.

    Args:
        session: boto3.Session to use
        region: AWS region (ignored - always uses us-east-1)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    # Route 53 Domains is only available in us-east-1
    route53domains = session.client('route53domains', region_name='us-east-1')

    # Registered Domains
    try:
        paginator = route53domains.get_paginator('list_domains')
        for page in paginator.paginate():
            for domain in page.get('Domains', []):
                domain_name = domain.get('DomainName', '')

                details = {
                    'auto_renew': domain.get('AutoRenew'),
                    'transfer_lock': domain.get('TransferLock'),
                    'expiry': str(domain.get('Expiry', '')) if domain.get('Expiry') else None,
                }

                # Get tags for the domain
                tags = {}
                try:
                    tag_response = route53domains.list_tags_for_domain(DomainName=domain_name)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'route53domains',
                    'type': 'domain',
                    'id': domain_name,
                    'arn': f"arn:aws:route53domains::{account_id}:domain/{domain_name}",
                    'name': domain_name,
                    'region': 'global',
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
