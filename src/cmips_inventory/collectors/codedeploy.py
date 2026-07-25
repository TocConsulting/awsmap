"""
CodeDeploy resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_codedeploy_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CodeDeploy resources: applications, deployment groups, deployment configs.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    codedeploy = session.client('codedeploy', region_name=region)

    # Applications
    application_names = []
    try:
        paginator = codedeploy.get_paginator('list_applications')
        for page in paginator.paginate():
            application_names.extend(page.get('applications', []))
    except Exception:
        pass

    for app_name in application_names:
        try:
            app_response = codedeploy.get_application(applicationName=app_name)
            app = app_response.get('application', {})

            app_arn = f"arn:aws:codedeploy:{region}:{account_id}:application:{app_name}"

            # Get tags
            tags = {}
            try:
                tag_response = codedeploy.list_tags_for_resource(ResourceArn=app_arn)
                for tag in tag_response.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            resources.append({
                'service': 'codedeploy',
                'type': 'application',
                'id': app_name,
                'arn': app_arn,
                'name': app_name,
                'region': region,
                'details': {
                    'compute_platform': app.get('computePlatform'),
                    'linked_to_github': app.get('linkedToGitHub'),
                    'github_account_name': app.get('gitHubAccountName'),
                    'create_time': str(app.get('createTime', '')),
                },
                'tags': tags
            })

            # Deployment Groups for this application
            try:
                dg_paginator = codedeploy.get_paginator('list_deployment_groups')
                dg_names = []
                for dg_page in dg_paginator.paginate(applicationName=app_name):
                    dg_names.extend(dg_page.get('deploymentGroups', []))

                # Batch get deployment group details
                if dg_names:
                    dg_response = codedeploy.batch_get_deployment_groups(
                        applicationName=app_name,
                        deploymentGroupNames=dg_names
                    )

                    for dg in dg_response.get('deploymentGroupsInfo', []):
                        dg_name = dg['deploymentGroupName']
                        dg_id = dg['deploymentGroupId']
                        dg_arn = f"arn:aws:codedeploy:{region}:{account_id}:deploymentgroup:{app_name}/{dg_name}"

                        # Get tags
                        dg_tags = {}
                        try:
                            dg_tag_response = codedeploy.list_tags_for_resource(ResourceArn=dg_arn)
                            for tag in dg_tag_response.get('Tags', []):
                                dg_tags[tag.get('Key', '')] = tag.get('Value', '')
                        except Exception:
                            pass

                        resources.append({
                            'service': 'codedeploy',
                            'type': 'deployment-group',
                            'id': dg_id,
                            'arn': dg_arn,
                            'name': dg_name,
                            'region': region,
                            'details': {
                                'application_name': app_name,
                                'deployment_config_name': dg.get('deploymentConfigName'),
                                'service_role_arn': dg.get('serviceRoleArn'),
                                'deployment_style': dg.get('deploymentStyle'),
                                'blue_green_deployment_config': bool(dg.get('blueGreenDeploymentConfiguration')),
                                'load_balancer_info': bool(dg.get('loadBalancerInfo')),
                                'ec2_tag_set': bool(dg.get('ec2TagSet')),
                                'ecs_services': len(dg.get('ecsServices', [])),
                                'auto_scaling_groups': len(dg.get('autoScalingGroups', [])),
                                'compute_platform': dg.get('computePlatform'),
                            },
                            'tags': dg_tags
                        })
            except Exception:
                pass
        except Exception:
            pass

    # Custom Deployment Configs (not predefined)
    try:
        paginator = codedeploy.get_paginator('list_deployment_configs')
        for page in paginator.paginate():
            for config_name in page.get('deploymentConfigsList', []):
                # Skip predefined configs
                if config_name.startswith('CodeDeployDefault.'):
                    continue

                try:
                    config_response = codedeploy.get_deployment_config(
                        deploymentConfigName=config_name
                    )
                    config = config_response.get('deploymentConfigInfo', {})

                    config_id = config.get('deploymentConfigId')

                    resources.append({
                        'service': 'codedeploy',
                        'type': 'deployment-config',
                        'id': config_id or config_name,
                        'arn': f"arn:aws:codedeploy:{region}:{account_id}:deploymentconfig:{config_name}",
                        'name': config_name,
                        'region': region,
                        'details': {
                            'compute_platform': config.get('computePlatform'),
                            'minimum_healthy_hosts': config.get('minimumHealthyHosts'),
                            'traffic_routing_config': config.get('trafficRoutingConfig'),
                            'create_time': str(config.get('createTime', '')),
                        },
                        'tags': {}
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
