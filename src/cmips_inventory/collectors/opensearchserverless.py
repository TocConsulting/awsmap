"""
Amazon OpenSearch Serverless resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_opensearchserverless_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect OpenSearch Serverless resources: collections, access policies, security policies, VPC endpoints.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    oss = session.client('opensearchserverless', region_name=region)

    # Collections
    try:
        response = oss.list_collections()
        for summary in response.get('collectionSummaries', []):
            collection_id = summary.get('id', '')
            collection_arn = summary.get('arn', '')
            collection_name = summary.get('name', collection_id)

            details = {
                'status': summary.get('status'),
            }

            resources.append({
                'service': 'opensearch-serverless',
                'type': 'collection',
                'id': collection_id,
                'arn': collection_arn,
                'name': collection_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # VPC Endpoints
    try:
        response = oss.list_vpc_endpoints()
        for endpoint in response.get('vpcEndpointSummaries', []):
            endpoint_id = endpoint.get('id', '')
            endpoint_name = endpoint.get('name', endpoint_id)

            details = {
                'status': endpoint.get('status'),
            }

            resources.append({
                'service': 'opensearch-serverless',
                'type': 'vpc-endpoint',
                'id': endpoint_id,
                'arn': f"arn:aws:aoss:{region}:{account_id}:vpcendpoint/{endpoint_id}",
                'name': endpoint_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Access Policies
    try:
        response = oss.list_access_policies(type='data')
        for policy in response.get('accessPolicySummaries', []):
            policy_name = policy.get('name', '')
            policy_version = policy.get('policyVersion', '')

            details = {
                'type': policy.get('type'),
                'policy_version': policy_version,
            }

            resources.append({
                'service': 'opensearch-serverless',
                'type': 'access-policy',
                'id': policy_name,
                'arn': f"arn:aws:aoss:{region}:{account_id}:accesspolicy/{policy_name}",
                'name': policy_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Security Policies (encryption)
    try:
        response = oss.list_security_policies(type='encryption')
        for policy in response.get('securityPolicySummaries', []):
            policy_name = policy.get('name', '')

            details = {
                'type': policy.get('type'),
                'policy_version': policy.get('policyVersion'),
            }

            resources.append({
                'service': 'opensearch-serverless',
                'type': 'security-policy',
                'id': f"encryption-{policy_name}",
                'arn': f"arn:aws:aoss:{region}:{account_id}:securitypolicy/encryption/{policy_name}",
                'name': policy_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Security Policies (network)
    try:
        response = oss.list_security_policies(type='network')
        for policy in response.get('securityPolicySummaries', []):
            policy_name = policy.get('name', '')

            details = {
                'type': policy.get('type'),
                'policy_version': policy.get('policyVersion'),
            }

            resources.append({
                'service': 'opensearch-serverless',
                'type': 'security-policy',
                'id': f"network-{policy_name}",
                'arn': f"arn:aws:aoss:{region}:{account_id}:securitypolicy/network/{policy_name}",
                'name': policy_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    return resources
