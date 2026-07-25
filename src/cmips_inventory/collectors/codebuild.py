"""
CodeBuild resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_codebuild_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CodeBuild resources: projects, report groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    codebuild = session.client('codebuild', region_name=region)

    # CodeBuild Projects
    project_names = []
    try:
        paginator = codebuild.get_paginator('list_projects')
        for page in paginator.paginate():
            project_names.extend(page.get('projects', []))
    except Exception:
        pass

    # Batch get project details (max 100 at a time)
    for i in range(0, len(project_names), 100):
        batch = project_names[i:i+100]
        try:
            response = codebuild.batch_get_projects(names=batch)
            for project in response.get('projects', []):
                project_name = project['name']
                project_arn = project['arn']

                # Tags are included in the response
                tags = {}
                for tag in project.get('tags', []):
                    tags[tag.get('key', '')] = tag.get('value', '')

                resources.append({
                    'service': 'codebuild',
                    'type': 'project',
                    'id': project_name,
                    'arn': project_arn,
                    'name': project_name,
                    'region': region,
                    'details': {
                        'description': project.get('description'),
                        'source_type': project.get('source', {}).get('type'),
                        'source_location': project.get('source', {}).get('location'),
                        'environment_type': project.get('environment', {}).get('type'),
                        'environment_compute_type': project.get('environment', {}).get('computeType'),
                        'environment_image': project.get('environment', {}).get('image'),
                        'service_role': project.get('serviceRole'),
                        'timeout_in_minutes': project.get('timeoutInMinutes'),
                        'badge_enabled': project.get('badge', {}).get('badgeEnabled'),
                        'concurrent_build_limit': project.get('concurrentBuildLimit'),
                        'build_batch_config': bool(project.get('buildBatchConfig')),
                        'created': str(project.get('created', '')),
                        'last_modified': str(project.get('lastModified', '')),
                    },
                    'tags': tags
                })
        except Exception:
            pass

    # Report Groups
    report_group_arns = []
    try:
        paginator = codebuild.get_paginator('list_report_groups')
        for page in paginator.paginate():
            report_group_arns.extend(page.get('reportGroups', []))
    except Exception:
        pass

    # Batch get report group details (max 100 at a time)
    for i in range(0, len(report_group_arns), 100):
        batch = report_group_arns[i:i+100]
        try:
            response = codebuild.batch_get_report_groups(reportGroupArns=batch)
            for rg in response.get('reportGroups', []):
                rg_name = rg['name']
                rg_arn = rg['arn']

                # Tags are included in the response
                tags = {}
                for tag in rg.get('tags', []):
                    tags[tag.get('key', '')] = tag.get('value', '')

                resources.append({
                    'service': 'codebuild',
                    'type': 'report-group',
                    'id': rg_name,
                    'arn': rg_arn,
                    'name': rg_name,
                    'region': region,
                    'details': {
                        'type': rg.get('type'),
                        'export_config_type': rg.get('exportConfig', {}).get('exportConfigType'),
                        'status': rg.get('status'),
                        'created': str(rg.get('created', '')),
                        'last_modified': str(rg.get('lastModified', '')),
                    },
                    'tags': tags
                })
        except Exception:
            pass

    return resources
