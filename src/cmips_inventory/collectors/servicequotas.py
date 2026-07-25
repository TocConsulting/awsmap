"""
AWS Service Quotas resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_servicequotas_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Service Quotas resources: quota increase requests.

    Note: Only collects quota increase requests history, not all quotas
    (which would be thousands of resources).

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sq = session.client('service-quotas', region_name=region)

    # Quota Increase Requests History
    try:
        paginator = sq.get_paginator('list_requested_service_quota_change_history')
        for page in paginator.paginate():
            for request in page.get('RequestedQuotas', []):
                request_id = request.get('Id', '')
                quota_code = request.get('QuotaCode', '')
                service_code = request.get('ServiceCode', '')

                details = {
                    'service_code': service_code,
                    'service_name': request.get('ServiceName'),
                    'quota_code': quota_code,
                    'quota_name': request.get('QuotaName'),
                    'status': request.get('Status'),
                    'desired_value': request.get('DesiredValue'),
                    'case_id': request.get('CaseId'),
                    'created': str(request.get('Created', '')),
                    'last_updated': str(request.get('LastUpdated', '')),
                    'requester': request.get('Requester'),
                    'quota_arn': request.get('QuotaArn'),
                    'global_quota': request.get('GlobalQuota'),
                    'unit': request.get('Unit'),
                }

                resources.append({
                    'service': 'service-quotas',
                    'type': 'quota-request',
                    'id': request_id,
                    'arn': request.get('QuotaArn', f"arn:aws:servicequotas:{region}:{account_id}:request/{request_id}"),
                    'name': f"{service_code}/{quota_code}",
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
