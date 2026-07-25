"""
Amplify resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_amplify_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Amplify resources: apps, branches.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    amplify = session.client('amplify', region_name=region)

    # Amplify Apps
    try:
        paginator = amplify.get_paginator('list_apps')
        for page in paginator.paginate():
            for app in page.get('apps', []):
                app_id = app['appId']
                app_arn = app['appArn']
                app_name = app['name']

                # Tags are included in the response
                tags = app.get('tags', {})

                resources.append({
                    'service': 'amplify',
                    'type': 'app',
                    'id': app_id,
                    'arn': app_arn,
                    'name': app_name,
                    'region': region,
                    'details': {
                        'description': app.get('description'),
                        'repository': app.get('repository'),
                        'platform': app.get('platform'),
                        'create_time': str(app.get('createTime', '')),
                        'update_time': str(app.get('updateTime', '')),
                        'default_domain': app.get('defaultDomain'),
                        'enable_branch_auto_build': app.get('enableBranchAutoBuild'),
                        'enable_branch_auto_deletion': app.get('enableBranchAutoDeletion'),
                        'enable_basic_auth': app.get('enableBasicAuth'),
                        'production_branch': app.get('productionBranch', {}).get('branchName'),
                        'custom_rules': len(app.get('customRules', [])),
                        'environment_variables': len(app.get('environmentVariables', {})),
                        'iam_service_role_arn': app.get('iamServiceRoleArn'),
                    },
                    'tags': tags
                })

                # Branches for this app
                try:
                    branch_paginator = amplify.get_paginator('list_branches')
                    for branch_page in branch_paginator.paginate(appId=app_id):
                        for branch in branch_page.get('branches', []):
                            branch_name = branch['branchName']
                            branch_arn = branch['branchArn']

                            branch_tags = branch.get('tags', {})

                            resources.append({
                                'service': 'amplify',
                                'type': 'branch',
                                'id': f"{app_id}/{branch_name}",
                                'arn': branch_arn,
                                'name': branch_name,
                                'region': region,
                                'details': {
                                    'app_id': app_id,
                                    'app_name': app_name,
                                    'description': branch.get('description'),
                                    'stage': branch.get('stage'),
                                    'display_name': branch.get('displayName'),
                                    'enable_notification': branch.get('enableNotification'),
                                    'create_time': str(branch.get('createTime', '')),
                                    'update_time': str(branch.get('updateTime', '')),
                                    'enable_auto_build': branch.get('enableAutoBuild'),
                                    'total_number_of_jobs': branch.get('totalNumberOfJobs'),
                                    'enable_basic_auth': branch.get('enableBasicAuth'),
                                    'active_job_id': branch.get('activeJobId'),
                                    'ttl': branch.get('ttl'),
                                    'enable_pull_request_preview': branch.get('enablePullRequestPreview'),
                                    'pull_request_environment_name': branch.get('pullRequestEnvironmentName'),
                                    'backend_environment_arn': branch.get('backendEnvironmentArn'),
                                },
                                'tags': branch_tags
                            })
                except Exception:
                    pass

                # Domain Associations for this app
                try:
                    domain_paginator = amplify.get_paginator('list_domain_associations')
                    for domain_page in domain_paginator.paginate(appId=app_id):
                        for domain in domain_page.get('domainAssociations', []):
                            domain_name = domain['domainName']
                            domain_arn = domain['domainAssociationArn']

                            resources.append({
                                'service': 'amplify',
                                'type': 'domain',
                                'id': f"{app_id}/{domain_name}",
                                'arn': domain_arn,
                                'name': domain_name,
                                'region': region,
                                'details': {
                                    'app_id': app_id,
                                    'app_name': app_name,
                                    'domain_status': domain.get('domainStatus'),
                                    'status_reason': domain.get('statusReason'),
                                    'enable_auto_sub_domain': domain.get('enableAutoSubDomain'),
                                    'auto_sub_domain_creation_patterns': domain.get('autoSubDomainCreationPatterns', []),
                                    'sub_domains': [sd.get('subDomainSetting', {}).get('branchName') for sd in domain.get('subDomains', [])],
                                    'certificate_verification_dns_record': domain.get('certificateVerificationDNSRecord'),
                                },
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
