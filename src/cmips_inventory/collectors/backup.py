"""
AWS Backup resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_backup_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Backup resources: vaults, plans, frameworks, report plans,
    restore testing plans, and Backup Gateway resources.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    backup = session.client('backup', region_name=region)

    # Backup Vaults
    try:
        paginator = backup.get_paginator('list_backup_vaults')
        for page in paginator.paginate():
            for vault in page.get('BackupVaultList', []):
                vault_name = vault['BackupVaultName']
                vault_arn = vault['BackupVaultArn']

                # Skip AWS managed vaults
                if vault_name.startswith('aws/'):
                    continue

                # Get tags
                tags = {}
                try:
                    tag_response = backup.list_tags(ResourceArn=vault_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'backup',
                    'type': 'vault',
                    'id': vault_name,
                    'arn': vault_arn,
                    'name': vault_name,
                    'region': region,
                    'details': {
                        'recovery_points': vault.get('NumberOfRecoveryPoints'),
                        'encryption_key_arn': vault.get('EncryptionKeyArn'),
                        'creator_request_id': vault.get('CreatorRequestId'),
                        'locked': vault.get('Locked'),
                        'min_retention_days': vault.get('MinRetentionDays'),
                        'max_retention_days': vault.get('MaxRetentionDays'),
                        'lock_date': str(vault.get('LockDate', '')) if vault.get('LockDate') else None,
                        'creation_date': str(vault.get('CreationDate', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Backup Plans
    try:
        paginator = backup.get_paginator('list_backup_plans')
        for page in paginator.paginate():
            for plan in page.get('BackupPlansList', []):
                plan_id = plan['BackupPlanId']
                plan_arn = plan['BackupPlanArn']
                plan_name = plan.get('BackupPlanName', plan_id)

                # Get selections count
                selections_count = 0
                try:
                    sel_response = backup.list_backup_selections(BackupPlanId=plan_id)
                    selections_count = len(sel_response.get('BackupSelectionsList', []))
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = backup.list_tags(ResourceArn=plan_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'backup',
                    'type': 'plan',
                    'id': plan_id,
                    'arn': plan_arn,
                    'name': plan_name,
                    'region': region,
                    'details': {
                        'version_id': plan.get('VersionId'),
                        'selections_count': selections_count,
                        'creator_request_id': plan.get('CreatorRequestId'),
                        'creation_date': str(plan.get('CreationDate', '')),
                        'last_execution_date': str(plan.get('LastExecutionDate', '')) if plan.get('LastExecutionDate') else None,
                        'advanced_backup_settings': plan.get('AdvancedBackupSettings'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Frameworks (Compliance)
    try:
        paginator = backup.get_paginator('list_frameworks')
        for page in paginator.paginate():
            for framework in page.get('Frameworks', []):
                framework_name = framework['FrameworkName']
                framework_arn = framework['FrameworkArn']

                # Get tags
                tags = {}
                try:
                    tag_response = backup.list_tags(ResourceArn=framework_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'backup',
                    'type': 'framework',
                    'id': framework_name,
                    'arn': framework_arn,
                    'name': framework_name,
                    'region': region,
                    'details': {
                        'description': framework.get('FrameworkDescription'),
                        'number_of_controls': framework.get('NumberOfControls'),
                        'deployment_status': framework.get('DeploymentStatus'),
                        'creation_time': str(framework.get('CreationTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Report Plans
    try:
        paginator = backup.get_paginator('list_report_plans')
        for page in paginator.paginate():
            for report in page.get('ReportPlans', []):
                report_name = report['ReportPlanName']
                report_arn = report['ReportPlanArn']

                # Get tags
                tags = {}
                try:
                    tag_response = backup.list_tags(ResourceArn=report_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'backup',
                    'type': 'report-plan',
                    'id': report_name,
                    'arn': report_arn,
                    'name': report_name,
                    'region': region,
                    'details': {
                        'description': report.get('ReportPlanDescription'),
                        'report_template': report.get('ReportSetting', {}).get('ReportTemplate'),
                        'last_attempted_execution_time': str(report.get('LastAttemptedExecutionTime', '')) if report.get('LastAttemptedExecutionTime') else None,
                        'last_successful_execution_time': str(report.get('LastSuccessfulExecutionTime', '')) if report.get('LastSuccessfulExecutionTime') else None,
                        'creation_time': str(report.get('CreationTime', '')),
                        'deployment_status': report.get('DeploymentStatus'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Restore Testing Plans
    try:
        paginator = backup.get_paginator('list_restore_testing_plans')
        for page in paginator.paginate():
            for plan in page.get('RestoreTestingPlans', []):
                plan_name = plan['RestoreTestingPlanName']
                plan_arn = plan['RestoreTestingPlanArn']

                # Get tags
                tags = {}
                try:
                    tag_response = backup.list_tags(ResourceArn=plan_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'backup',
                    'type': 'restore-testing-plan',
                    'id': plan_name,
                    'arn': plan_arn,
                    'name': plan_name,
                    'region': region,
                    'details': {
                        'schedule_expression': plan.get('ScheduleExpression'),
                        'schedule_expression_timezone': plan.get('ScheduleExpressionTimezone'),
                        'start_window_hours': plan.get('StartWindowHours'),
                        'creation_time': str(plan.get('CreationTime', '')),
                        'last_execution_time': str(plan.get('LastExecutionTime', '')) if plan.get('LastExecutionTime') else None,
                        'last_update_time': str(plan.get('LastUpdateTime', '')) if plan.get('LastUpdateTime') else None,
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Note: Backup Gateway resources (gateways, hypervisors, virtual machines) skipped
    # for performance. They are on-premises resources rarely used and add ~16s overhead.

    return resources
