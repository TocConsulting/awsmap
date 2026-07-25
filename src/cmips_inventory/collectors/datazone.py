"""
DataZone resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_datazone_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect DataZone resources: domains, projects, environments.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    datazone = session.client('datazone', region_name=region)

    # Domains
    try:
        paginator = datazone.get_paginator('list_domains')
        for page in paginator.paginate():
            for domain in page.get('items', []):
                domain_id = domain['id']
                domain_arn = domain.get('arn', '')
                domain_name = domain.get('name', domain_id)

                # Get tags
                tags = {}
                if domain_arn:
                    try:
                        tag_response = datazone.list_tags_for_resource(resourceArn=domain_arn)
                        tags = tag_response.get('tags', {})
                    except Exception:
                        pass

                resources.append({
                    'service': 'datazone',
                    'type': 'domain',
                    'id': domain_id,
                    'arn': domain_arn,
                    'name': domain_name,
                    'region': region,
                    'details': {
                        'status': domain.get('status'),
                        'description': domain.get('description'),
                        'portal_url': domain.get('portalUrl'),
                        'managed_account_id': domain.get('managedAccountId'),
                        'domain_version': domain.get('domainVersion'),
                        'created_at': str(domain.get('createdAt', '')) if domain.get('createdAt') else None,
                        'last_updated_at': str(domain.get('lastUpdatedAt', '')) if domain.get('lastUpdatedAt') else None,
                    },
                    'tags': tags
                })

                # Projects per domain
                try:
                    project_paginator = datazone.get_paginator('list_projects')
                    for project_page in project_paginator.paginate(domainIdentifier=domain_id):
                        for project in project_page.get('items', []):
                            project_id = project['id']
                            project_name = project.get('name', project_id)

                            resources.append({
                                'service': 'datazone',
                                'type': 'project',
                                'id': project_id,
                                'arn': f"arn:aws:datazone:{region}:{account_id}:project/{domain_id}/{project_id}",
                                'name': project_name,
                                'region': region,
                                'details': {
                                    'domain_id': project.get('domainId'),
                                    'status': project.get('projectStatus'),
                                    'description': project.get('description'),
                                    'created_by': project.get('createdBy'),
                                    'domain_unit_id': project.get('domainUnitId'),
                                    'created_at': str(project.get('createdAt', '')) if project.get('createdAt') else None,
                                    'updated_at': str(project.get('updatedAt', '')) if project.get('updatedAt') else None,
                                },
                                'tags': {}
                            })

                            # Environments per domain + project
                            try:
                                env_paginator = datazone.get_paginator('list_environments')
                                for env_page in env_paginator.paginate(
                                    domainIdentifier=domain_id,
                                    projectIdentifier=project_id
                                ):
                                    for env in env_page.get('items', []):
                                        env_id = env['id']
                                        env_name = env.get('name', env_id)

                                        resources.append({
                                            'service': 'datazone',
                                            'type': 'environment',
                                            'id': env_id,
                                            'arn': f"arn:aws:datazone:{region}:{account_id}:environment/{domain_id}/{env_id}",
                                            'name': env_name,
                                            'region': region,
                                            'details': {
                                                'domain_id': env.get('domainId'),
                                                'project_id': env.get('projectId'),
                                                'status': env.get('status'),
                                                'description': env.get('description'),
                                                'provider': env.get('provider'),
                                                'environment_profile_id': env.get('environmentProfileId'),
                                                'aws_account_id': env.get('awsAccountId'),
                                                'aws_account_region': env.get('awsAccountRegion'),
                                                'created_by': env.get('createdBy'),
                                                'created_at': str(env.get('createdAt', '')) if env.get('createdAt') else None,
                                                'updated_at': str(env.get('updatedAt', '')) if env.get('updatedAt') else None,
                                            },
                                            'tags': {}
                                        })
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    return resources
