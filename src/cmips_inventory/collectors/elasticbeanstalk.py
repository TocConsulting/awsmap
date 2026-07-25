"""
Elastic Beanstalk resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_elasticbeanstalk_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Elastic Beanstalk resources: applications, environments, application versions.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    eb = session.client('elasticbeanstalk', region_name=region)

    # Applications
    applications = []
    try:
        response = eb.describe_applications()
        for app in response.get('Applications', []):
            applications.append(app)
            app_name = app['ApplicationName']
            app_arn = app.get('ApplicationArn', f"arn:aws:elasticbeanstalk:{region}:{account_id}:application/{app_name}")

            # Get tags
            tags = {}
            try:
                tag_response = eb.list_tags_for_resource(ResourceArn=app_arn)
                for tag in tag_response.get('ResourceTags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            resources.append({
                'service': 'elasticbeanstalk',
                'type': 'application',
                'id': app_name,
                'arn': app_arn,
                'name': app_name,
                'region': region,
                'details': {
                    'description': app.get('Description'),
                    'date_created': str(app.get('DateCreated', '')),
                    'date_updated': str(app.get('DateUpdated', '')),
                    'versions': app.get('Versions', []),
                    'configuration_templates': app.get('ConfigurationTemplates', []),
                    'resource_lifecycle_config': app.get('ResourceLifecycleConfig'),
                },
                'tags': tags
            })
    except Exception:
        pass

    # Environments
    try:
        response = eb.describe_environments(IncludeDeleted=False)
        for env in response.get('Environments', []):
            env_name = env['EnvironmentName']
            env_id = env['EnvironmentId']
            env_arn = env.get('EnvironmentArn', f"arn:aws:elasticbeanstalk:{region}:{account_id}:environment/{env.get('ApplicationName')}/{env_name}")

            # Get tags
            tags = {}
            try:
                tag_response = eb.list_tags_for_resource(ResourceArn=env_arn)
                for tag in tag_response.get('ResourceTags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            resources.append({
                'service': 'elasticbeanstalk',
                'type': 'environment',
                'id': env_id,
                'arn': env_arn,
                'name': env_name,
                'region': region,
                'details': {
                    'application_name': env.get('ApplicationName'),
                    'version_label': env.get('VersionLabel'),
                    'solution_stack_name': env.get('SolutionStackName'),
                    'platform_arn': env.get('PlatformArn'),
                    'template_name': env.get('TemplateName'),
                    'description': env.get('Description'),
                    'endpoint_url': env.get('EndpointURL'),
                    'cname': env.get('CNAME'),
                    'date_created': str(env.get('DateCreated', '')),
                    'date_updated': str(env.get('DateUpdated', '')),
                    'status': env.get('Status'),
                    'abortable_operation_in_progress': env.get('AbortableOperationInProgress'),
                    'health': env.get('Health'),
                    'health_status': env.get('HealthStatus'),
                    'tier_name': env.get('Tier', {}).get('Name'),
                    'tier_type': env.get('Tier', {}).get('Type'),
                    'tier_version': env.get('Tier', {}).get('Version'),
                    'operations_role': env.get('OperationsRole'),
                },
                'tags': tags
            })
    except Exception:
        pass

    # Application Versions (for each application, limit to recent)
    for app in applications:
        app_name = app['ApplicationName']
        try:
            response = eb.describe_application_versions(
                ApplicationName=app_name,
                MaxRecords=20
            )
            for version in response.get('ApplicationVersions', []):
                version_label = version['VersionLabel']
                version_arn = version.get('ApplicationVersionArn', f"arn:aws:elasticbeanstalk:{region}:{account_id}:applicationversion/{app_name}/{version_label}")

                resources.append({
                    'service': 'elasticbeanstalk',
                    'type': 'application-version',
                    'id': f"{app_name}/{version_label}",
                    'arn': version_arn,
                    'name': version_label,
                    'region': region,
                    'details': {
                        'application_name': app_name,
                        'description': version.get('Description'),
                        'source_bundle': version.get('SourceBundle'),
                        'build_arn': version.get('BuildArn'),
                        'date_created': str(version.get('DateCreated', '')),
                        'date_updated': str(version.get('DateUpdated', '')),
                        'status': version.get('Status'),
                    },
                    'tags': {}
                })
        except Exception:
            pass

    return resources
