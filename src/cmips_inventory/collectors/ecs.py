"""
ECS resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_ecs_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect ECS resources: clusters, services, task definitions, capacity providers.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ecs = session.client('ecs', region_name=region)

    # ECS Clusters
    cluster_arns = []
    try:
        paginator = ecs.get_paginator('list_clusters')
        for page in paginator.paginate():
            cluster_arns.extend(page.get('clusterArns', []))
    except Exception:
        pass

    if cluster_arns:
        try:
            # Describe clusters in batches of 100
            for i in range(0, len(cluster_arns), 100):
                batch = cluster_arns[i:i+100]
                response = ecs.describe_clusters(
                    clusters=batch,
                    include=['TAGS', 'SETTINGS', 'STATISTICS']
                )

                for cluster in response.get('clusters', []):
                    cluster_name = cluster['clusterName']
                    cluster_arn = cluster['clusterArn']

                    # Get tags from response
                    tags = {}
                    for tag in cluster.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')

                    resources.append({
                        'service': 'ecs',
                        'type': 'cluster',
                        'id': cluster_name,
                        'arn': cluster_arn,
                        'name': cluster_name,
                        'region': region,
                        'details': {
                            'status': cluster.get('status'),
                            'running_tasks_count': cluster.get('runningTasksCount'),
                            'pending_tasks_count': cluster.get('pendingTasksCount'),
                            'active_services_count': cluster.get('activeServicesCount'),
                            'registered_container_instances_count': cluster.get('registeredContainerInstancesCount'),
                            'capacity_providers': cluster.get('capacityProviders', []),
                        },
                        'tags': tags
                    })

                    # ECS Services for this cluster
                    try:
                        service_arns = []
                        svc_paginator = ecs.get_paginator('list_services')
                        for svc_page in svc_paginator.paginate(cluster=cluster_arn):
                            service_arns.extend(svc_page.get('serviceArns', []))

                        if service_arns:
                            # Describe services in batches of 10
                            for j in range(0, len(service_arns), 10):
                                svc_batch = service_arns[j:j+10]
                                svc_response = ecs.describe_services(
                                    cluster=cluster_arn,
                                    services=svc_batch,
                                    include=['TAGS']
                                )

                                for svc in svc_response.get('services', []):
                                    svc_name = svc['serviceName']

                                    svc_tags = {}
                                    for tag in svc.get('tags', []):
                                        svc_tags[tag.get('key', '')] = tag.get('value', '')

                                    resources.append({
                                        'service': 'ecs',
                                        'type': 'service',
                                        'id': svc_name,
                                        'arn': svc['serviceArn'],
                                        'name': svc_name,
                                        'region': region,
                                        'details': {
                                            'cluster': cluster_name,
                                            'status': svc.get('status'),
                                            'desired_count': svc.get('desiredCount'),
                                            'running_count': svc.get('runningCount'),
                                            'pending_count': svc.get('pendingCount'),
                                            'launch_type': svc.get('launchType'),
                                            'task_definition': svc.get('taskDefinition'),
                                            'deployment_controller': svc.get('deploymentController', {}).get('type'),
                                            'scheduling_strategy': svc.get('schedulingStrategy'),
                                        },
                                        'tags': svc_tags
                                    })
                    except Exception:
                        pass
        except Exception:
            pass

    # ECS Task Definitions (only latest revisions, active)
    try:
        paginator = ecs.get_paginator('list_task_definition_families')
        for page in paginator.paginate(status='ACTIVE'):
            for family in page.get('families', []):
                try:
                    # Get latest revision
                    td_response = ecs.describe_task_definition(
                        taskDefinition=family,
                        include=['TAGS']
                    )

                    td = td_response.get('taskDefinition', {})
                    td_arn = td['taskDefinitionArn']

                    td_tags = {}
                    for tag in td_response.get('tags', []):
                        td_tags[tag.get('key', '')] = tag.get('value', '')

                    resources.append({
                        'service': 'ecs',
                        'type': 'task-definition',
                        'id': f"{family}:{td.get('revision')}",
                        'arn': td_arn,
                        'name': family,
                        'region': region,
                        'details': {
                            'family': family,
                            'revision': td.get('revision'),
                            'status': td.get('status'),
                            'requires_compatibilities': td.get('requiresCompatibilities', []),
                            'cpu': td.get('cpu'),
                            'memory': td.get('memory'),
                            'network_mode': td.get('networkMode'),
                            'container_count': len(td.get('containerDefinitions', [])),
                            'execution_role_arn': td.get('executionRoleArn'),
                            'task_role_arn': td.get('taskRoleArn'),
                        },
                        'tags': td_tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # ECS Capacity Providers (non-default)
    try:
        paginator = ecs.get_paginator('describe_capacity_providers')
        for page in paginator.paginate():
            for cp in page.get('capacityProviders', []):
                cp_name = cp['capacityProviderArn'].split('/')[-1]

                # Skip AWS-managed capacity providers
                if cp_name in ['FARGATE', 'FARGATE_SPOT']:
                    continue

                cp_tags = {}
                for tag in cp.get('tags', []):
                    cp_tags[tag.get('key', '')] = tag.get('value', '')

                resources.append({
                    'service': 'ecs',
                    'type': 'capacity-provider',
                    'id': cp_name,
                    'arn': cp['capacityProviderArn'],
                    'name': cp_name,
                    'region': region,
                    'details': {
                        'status': cp.get('status'),
                        'auto_scaling_group_arn': cp.get('autoScalingGroupProvider', {}).get('autoScalingGroupArn'),
                        'managed_scaling': cp.get('autoScalingGroupProvider', {}).get('managedScaling', {}).get('status'),
                        'managed_termination_protection': cp.get('autoScalingGroupProvider', {}).get('managedTerminationProtection'),
                    },
                    'tags': cp_tags
                })
    except Exception:
        pass

    return resources
