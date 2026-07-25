"""
CloudFormation resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_cloudformation_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CloudFormation resources: stacks, stack sets.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    cfn = session.client('cloudformation', region_name=region)

    # CloudFormation Stacks
    try:
        paginator = cfn.get_paginator('describe_stacks')
        for page in paginator.paginate():
            for stack in page.get('Stacks', []):
                stack_name = stack['StackName']
                stack_id = stack['StackId']

                # Tags are included in the response
                tags = {}
                for tag in stack.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')

                resources.append({
                    'service': 'cloudformation',
                    'type': 'stack',
                    'id': stack_id,
                    'arn': stack_id,  # StackId is actually the ARN
                    'name': stack_name,
                    'region': region,
                    'details': {
                        'status': stack.get('StackStatus'),
                        'status_reason': stack.get('StackStatusReason'),
                        'description': stack.get('Description'),
                        'creation_time': str(stack.get('CreationTime', '')),
                        'last_updated_time': str(stack.get('LastUpdatedTime', '')),
                        'deletion_time': str(stack.get('DeletionTime', '')) if stack.get('DeletionTime') else None,
                        'enable_termination_protection': stack.get('EnableTerminationProtection'),
                        'drift_status': stack.get('DriftInformation', {}).get('StackDriftStatus'),
                        'root_id': stack.get('RootId'),
                        'parent_id': stack.get('ParentId'),
                        'role_arn': stack.get('RoleARN'),
                        'outputs_count': len(stack.get('Outputs', [])),
                        'parameters_count': len(stack.get('Parameters', [])),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # CloudFormation Stack Sets
    try:
        paginator = cfn.get_paginator('list_stack_sets')
        for page in paginator.paginate(Status='ACTIVE'):
            for ss in page.get('Summaries', []):
                ss_name = ss['StackSetName']
                ss_id = ss['StackSetId']

                try:
                    # Get stack set details
                    ss_response = cfn.describe_stack_set(StackSetName=ss_name)
                    ss_detail = ss_response.get('StackSet', {})

                    # Tags are included in detail response
                    tags = {}
                    for tag in ss_detail.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')

                    resources.append({
                        'service': 'cloudformation',
                        'type': 'stack-set',
                        'id': ss_id,
                        'arn': ss_detail.get('StackSetARN', f"arn:aws:cloudformation:{region}:{account_id}:stackset/{ss_name}:{ss_id}"),
                        'name': ss_name,
                        'region': region,
                        'details': {
                            'status': ss_detail.get('Status'),
                            'description': ss_detail.get('Description'),
                            'permission_model': ss_detail.get('PermissionModel'),
                            'auto_deployment': ss_detail.get('AutoDeployment'),
                            'organizational_unit_ids': ss_detail.get('OrganizationalUnitIds', []),
                            'administration_role_arn': ss_detail.get('AdministrationRoleARN'),
                            'execution_role_name': ss_detail.get('ExecutionRoleName'),
                            'drift_status': ss_detail.get('StackSetDriftDetectionDetails', {}).get('DriftStatus'),
                            'managed_execution': ss_detail.get('ManagedExecution', {}).get('Active'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
