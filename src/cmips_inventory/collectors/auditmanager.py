"""
AWS Audit Manager resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Audit Manager supported regions (from https://docs.aws.amazon.com/general/latest/gr/audit-manager.html)
AUDITMANAGER_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2',
}


def collect_auditmanager_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Audit Manager resources: assessments and custom frameworks.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in AUDITMANAGER_REGIONS:
        return []

    resources = []
    auditmanager = session.client('auditmanager', region_name=region)

    # Assessments
    try:
        paginator = auditmanager.get_paginator('list_assessments')
        for page in paginator.paginate():
            for assessment in page.get('assessmentMetadata', []):
                assessment_id = assessment.get('id', '')
                assessment_name = assessment.get('name', assessment_id)
                assessment_arn = f"arn:aws:auditmanager:{region}:{account_id}:assessment/{assessment_id}"

                details = {
                    'status': assessment.get('status'),
                    'compliance_type': assessment.get('complianceType'),
                    'roles': [r.get('roleName') for r in assessment.get('roles', [])],
                }

                resources.append({
                    'service': 'auditmanager',
                    'type': 'assessment',
                    'id': assessment_id,
                    'arn': assessment_arn,
                    'name': assessment_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Custom Frameworks only
    try:
        paginator = auditmanager.get_paginator('list_assessment_frameworks')
        for page in paginator.paginate(frameworkType='Custom'):
            for framework in page.get('frameworkMetadataList', []):
                framework_id = framework.get('id', '')
                framework_name = framework.get('name', framework_id)
                framework_arn = framework.get('arn', f"arn:aws:auditmanager:{region}:{account_id}:assessmentFramework/{framework_id}")

                details = {
                    'description': framework.get('description'),
                    'compliance_type': framework.get('complianceType'),
                    'controls_count': framework.get('controlsCount'),
                    'control_sets_count': framework.get('controlSetsCount'),
                }

                resources.append({
                    'service': 'auditmanager',
                    'type': 'framework',
                    'id': framework_id,
                    'arn': framework_arn,
                    'name': framework_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
