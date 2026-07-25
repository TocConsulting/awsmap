"""
AWS AppConfig resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_appconfig_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS AppConfig resources: applications, deployment strategies, and extensions.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    appconfig = session.client('appconfig', region_name=region)

    # Applications
    try:
        paginator = appconfig.get_paginator('list_applications')
        for page in paginator.paginate():
            for app in page.get('Items', []):
                app_id = app['Id']
                app_name = app.get('Name', app_id)
                app_arn = f"arn:aws:appconfig:{region}:{account_id}:application/{app_id}"

                details = {
                    'description': app.get('Description'),
                }

                resources.append({
                    'service': 'appconfig',
                    'type': 'application',
                    'id': app_id,
                    'arn': app_arn,
                    'name': app_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })

                # Environments for this application
                try:
                    env_paginator = appconfig.get_paginator('list_environments')
                    for env_page in env_paginator.paginate(ApplicationId=app_id):
                        for env in env_page.get('Items', []):
                            env_id = env['Id']
                            env_name = env.get('Name', env_id)
                            env_arn = f"arn:aws:appconfig:{region}:{account_id}:application/{app_id}/environment/{env_id}"

                            env_details = {
                                'description': env.get('Description'),
                                'state': env.get('State'),
                                'application_id': app_id,
                            }

                            resources.append({
                                'service': 'appconfig',
                                'type': 'environment',
                                'id': env_id,
                                'arn': env_arn,
                                'name': env_name,
                                'region': region,
                                'details': env_details,
                                'tags': {}
                            })
                except Exception:
                    pass

                # Configuration Profiles for this application
                try:
                    profile_paginator = appconfig.get_paginator('list_configuration_profiles')
                    for profile_page in profile_paginator.paginate(ApplicationId=app_id):
                        for profile in profile_page.get('Items', []):
                            profile_id = profile['Id']
                            profile_name = profile.get('Name', profile_id)
                            profile_arn = f"arn:aws:appconfig:{region}:{account_id}:application/{app_id}/configurationprofile/{profile_id}"

                            profile_details = {
                                'description': profile.get('Description'),
                                'location_uri': profile.get('LocationUri'),
                                'type': profile.get('Type'),
                                'application_id': app_id,
                            }

                            resources.append({
                                'service': 'appconfig',
                                'type': 'configuration-profile',
                                'id': profile_id,
                                'arn': profile_arn,
                                'name': profile_name,
                                'region': region,
                                'details': profile_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    # Deployment Strategies
    try:
        paginator = appconfig.get_paginator('list_deployment_strategies')
        for page in paginator.paginate():
            for strategy in page.get('Items', []):
                strategy_id = strategy['Id']
                strategy_name = strategy.get('Name', strategy_id)
                strategy_arn = f"arn:aws:appconfig:{region}:{account_id}:deploymentstrategy/{strategy_id}"

                # Skip predefined strategies
                if strategy_id.startswith('AppConfig.'):
                    continue

                details = {
                    'description': strategy.get('Description'),
                    'deployment_duration_in_minutes': strategy.get('DeploymentDurationInMinutes'),
                    'growth_factor': strategy.get('GrowthFactor'),
                    'growth_type': strategy.get('GrowthType'),
                    'final_bake_time_in_minutes': strategy.get('FinalBakeTimeInMinutes'),
                    'replicate_to': strategy.get('ReplicateTo'),
                }

                resources.append({
                    'service': 'appconfig',
                    'type': 'deployment-strategy',
                    'id': strategy_id,
                    'arn': strategy_arn,
                    'name': strategy_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
