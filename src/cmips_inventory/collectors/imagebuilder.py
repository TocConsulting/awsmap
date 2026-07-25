"""
AWS EC2 Image Builder resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_imagebuilder_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS EC2 Image Builder resources: pipelines, recipes, components,
    distribution configs, infrastructure configs, lifecycle policies, and workflows.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    imagebuilder = session.client('imagebuilder', region_name=region)

    # Image Pipelines
    try:
        paginator = imagebuilder.get_paginator('list_image_pipelines')
        for page in paginator.paginate():
            for pipeline in page.get('imagePipelineList', []):
                pipeline_arn = pipeline['arn']
                pipeline_name = pipeline.get('name', pipeline_arn.split('/')[-1])

                details = {
                    'description': pipeline.get('description'),
                    'platform': pipeline.get('platform'),
                    'image_recipe_arn': pipeline.get('imageRecipeArn'),
                    'container_recipe_arn': pipeline.get('containerRecipeArn'),
                    'infrastructure_configuration_arn': pipeline.get('infrastructureConfigurationArn'),
                    'distribution_configuration_arn': pipeline.get('distributionConfigurationArn'),
                    'enhanced_image_metadata_enabled': pipeline.get('enhancedImageMetadataEnabled'),
                    'status': pipeline.get('status'),
                    'schedule_expression': pipeline.get('schedule', {}).get('scheduleExpression'),
                    'schedule_timezone': pipeline.get('schedule', {}).get('timezone'),
                    'pipeline_execution_start_condition': pipeline.get('schedule', {}).get('pipelineExecutionStartCondition'),
                    'date_created': pipeline.get('dateCreated'),
                    'date_updated': pipeline.get('dateUpdated'),
                    'date_last_run': pipeline.get('dateLastRun'),
                    'date_next_run': pipeline.get('dateNextRun'),
                }

                tags = pipeline.get('tags', {})

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'pipeline',
                    'id': pipeline_name,
                    'arn': pipeline_arn,
                    'name': pipeline_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Image Recipes
    try:
        paginator = imagebuilder.get_paginator('list_image_recipes')
        for page in paginator.paginate(owner='Self'):
            for recipe in page.get('imageRecipeSummaryList', []):
                recipe_arn = recipe['arn']
                recipe_name = recipe.get('name', recipe_arn.split('/')[-1])

                details = {
                    'platform': recipe.get('platform'),
                    'owner': recipe.get('owner'),
                    'parent_image': recipe.get('parentImage'),
                    'date_created': recipe.get('dateCreated'),
                }

                tags = recipe.get('tags', {})

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'image-recipe',
                    'id': recipe_name,
                    'arn': recipe_arn,
                    'name': recipe_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Container Recipes
    try:
        paginator = imagebuilder.get_paginator('list_container_recipes')
        for page in paginator.paginate(owner='Self'):
            for recipe in page.get('containerRecipeSummaryList', []):
                recipe_arn = recipe['arn']
                recipe_name = recipe.get('name', recipe_arn.split('/')[-1])

                details = {
                    'platform': recipe.get('platform'),
                    'owner': recipe.get('owner'),
                    'container_type': recipe.get('containerType'),
                    'parent_image': recipe.get('parentImage'),
                    'date_created': recipe.get('dateCreated'),
                }

                tags = recipe.get('tags', {})

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'container-recipe',
                    'id': recipe_name,
                    'arn': recipe_arn,
                    'name': recipe_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Components (only self-owned, skip AWS-managed)
    try:
        paginator = imagebuilder.get_paginator('list_components')
        for page in paginator.paginate(owner='Self'):
            for component in page.get('componentVersionList', []):
                component_arn = component['arn']
                component_name = component.get('name', component_arn.split('/')[-1])

                details = {
                    'version': component.get('version'),
                    'platform': component.get('platform'),
                    'type': component.get('type'),
                    'owner': component.get('owner'),
                    'description': component.get('description'),
                    'date_created': component.get('dateCreated'),
                }

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'component',
                    'id': component_name,
                    'arn': component_arn,
                    'name': component_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Distribution Configurations
    try:
        paginator = imagebuilder.get_paginator('list_distribution_configurations')
        for page in paginator.paginate():
            for dist in page.get('distributionConfigurationSummaryList', []):
                dist_arn = dist['arn']
                dist_name = dist.get('name', dist_arn.split('/')[-1])

                details = {
                    'description': dist.get('description'),
                    'regions': dist.get('regions', []),
                    'date_created': dist.get('dateCreated'),
                    'date_updated': dist.get('dateUpdated'),
                }

                tags = dist.get('tags', {})

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'distribution-configuration',
                    'id': dist_name,
                    'arn': dist_arn,
                    'name': dist_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Infrastructure Configurations
    try:
        paginator = imagebuilder.get_paginator('list_infrastructure_configurations')
        for page in paginator.paginate():
            for infra in page.get('infrastructureConfigurationSummaryList', []):
                infra_arn = infra['arn']
                infra_name = infra.get('name', infra_arn.split('/')[-1])

                details = {
                    'description': infra.get('description'),
                    'instance_types': infra.get('instanceTypes', []),
                    'instance_profile_name': infra.get('instanceProfileName'),
                    'resource_tags': infra.get('resourceTags', {}),
                    'date_created': infra.get('dateCreated'),
                    'date_updated': infra.get('dateUpdated'),
                }

                tags = infra.get('tags', {})

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'infrastructure-configuration',
                    'id': infra_name,
                    'arn': infra_arn,
                    'name': infra_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Lifecycle Policies
    try:
        paginator = imagebuilder.get_paginator('list_lifecycle_policies')
        for page in paginator.paginate():
            for policy in page.get('lifecyclePolicySummaryList', []):
                policy_arn = policy['arn']
                policy_name = policy.get('name', policy_arn.split('/')[-1])

                details = {
                    'description': policy.get('description'),
                    'status': policy.get('status'),
                    'execution_role': policy.get('executionRole'),
                    'resource_type': policy.get('resourceType'),
                    'date_created': policy.get('dateCreated'),
                    'date_updated': policy.get('dateUpdated'),
                    'date_last_run': policy.get('dateLastRun'),
                }

                tags = policy.get('tags', {})

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'lifecycle-policy',
                    'id': policy_name,
                    'arn': policy_arn,
                    'name': policy_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Workflows (only self-owned)
    try:
        paginator = imagebuilder.get_paginator('list_workflows')
        for page in paginator.paginate(owner='Self'):
            for workflow in page.get('workflowVersionList', []):
                workflow_arn = workflow['arn']
                workflow_name = workflow.get('name', workflow_arn.split('/')[-1])

                details = {
                    'version': workflow.get('version'),
                    'type': workflow.get('type'),
                    'owner': workflow.get('owner'),
                    'description': workflow.get('description'),
                    'date_created': workflow.get('dateCreated'),
                }

                resources.append({
                    'service': 'imagebuilder',
                    'type': 'workflow',
                    'id': workflow_name,
                    'arn': workflow_arn,
                    'name': workflow_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
