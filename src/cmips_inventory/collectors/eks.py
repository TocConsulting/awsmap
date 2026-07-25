"""
EKS resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_eks_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EKS resources: clusters, node groups, Fargate profiles, addons.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    eks = session.client('eks', region_name=region)

    # EKS Clusters
    cluster_names = []
    try:
        paginator = eks.get_paginator('list_clusters')
        for page in paginator.paginate():
            cluster_names.extend(page.get('clusters', []))
    except Exception:
        pass

    for cluster_name in cluster_names:
        try:
            response = eks.describe_cluster(name=cluster_name)
            cluster = response.get('cluster', {})

            resources.append({
                'service': 'eks',
                'type': 'cluster',
                'id': cluster_name,
                'arn': cluster['arn'],
                'name': cluster_name,
                'region': region,
                'details': {
                    'status': cluster.get('status'),
                    'version': cluster.get('version'),
                    'platform_version': cluster.get('platformVersion'),
                    'endpoint': cluster.get('endpoint'),
                    'role_arn': cluster.get('roleArn'),
                    'vpc_id': cluster.get('resourcesVpcConfig', {}).get('vpcId'),
                    'subnets': cluster.get('resourcesVpcConfig', {}).get('subnetIds', []),
                    'security_groups': cluster.get('resourcesVpcConfig', {}).get('securityGroupIds', []),
                    'endpoint_public_access': cluster.get('resourcesVpcConfig', {}).get('endpointPublicAccess'),
                    'endpoint_private_access': cluster.get('resourcesVpcConfig', {}).get('endpointPrivateAccess'),
                    'encryption_enabled': len(cluster.get('encryptionConfig', [])) > 0,
                    'logging_types': [
                        lt for lc in cluster.get('logging', {}).get('clusterLogging', [])
                        if lc.get('enabled')
                        for lt in lc.get('types', [])
                    ],
                },
                'tags': cluster.get('tags', {})
            })

            # EKS Node Groups for this cluster
            try:
                ng_paginator = eks.get_paginator('list_nodegroups')
                for ng_page in ng_paginator.paginate(clusterName=cluster_name):
                    for ng_name in ng_page.get('nodegroups', []):
                        try:
                            ng_response = eks.describe_nodegroup(
                                clusterName=cluster_name,
                                nodegroupName=ng_name
                            )
                            ng = ng_response.get('nodegroup', {})

                            resources.append({
                                'service': 'eks',
                                'type': 'nodegroup',
                                'id': ng_name,
                                'arn': ng['nodegroupArn'],
                                'name': ng_name,
                                'region': region,
                                'details': {
                                    'cluster': cluster_name,
                                    'status': ng.get('status'),
                                    'capacity_type': ng.get('capacityType'),
                                    'instance_types': ng.get('instanceTypes', []),
                                    'ami_type': ng.get('amiType'),
                                    'node_role': ng.get('nodeRole'),
                                    'subnets': ng.get('subnets', []),
                                    'scaling_config': ng.get('scalingConfig'),
                                    'disk_size': ng.get('diskSize'),
                                    'release_version': ng.get('releaseVersion'),
                                },
                                'tags': ng.get('tags', {})
                            })
                        except Exception:
                            pass
            except Exception:
                pass

            # EKS Fargate Profiles for this cluster
            try:
                fp_paginator = eks.get_paginator('list_fargate_profiles')
                for fp_page in fp_paginator.paginate(clusterName=cluster_name):
                    for fp_name in fp_page.get('fargateProfileNames', []):
                        try:
                            fp_response = eks.describe_fargate_profile(
                                clusterName=cluster_name,
                                fargateProfileName=fp_name
                            )
                            fp = fp_response.get('fargateProfile', {})

                            resources.append({
                                'service': 'eks',
                                'type': 'fargate-profile',
                                'id': fp_name,
                                'arn': fp['fargateProfileArn'],
                                'name': fp_name,
                                'region': region,
                                'details': {
                                    'cluster': cluster_name,
                                    'status': fp.get('status'),
                                    'pod_execution_role_arn': fp.get('podExecutionRoleArn'),
                                    'subnets': fp.get('subnets', []),
                                    'selectors': fp.get('selectors', []),
                                },
                                'tags': fp.get('tags', {})
                            })
                        except Exception:
                            pass
            except Exception:
                pass

            # EKS Addons for this cluster
            try:
                addon_paginator = eks.get_paginator('list_addons')
                for addon_page in addon_paginator.paginate(clusterName=cluster_name):
                    for addon_name in addon_page.get('addons', []):
                        try:
                            addon_response = eks.describe_addon(
                                clusterName=cluster_name,
                                addonName=addon_name
                            )
                            addon = addon_response.get('addon', {})

                            resources.append({
                                'service': 'eks',
                                'type': 'addon',
                                'id': f"{cluster_name}/{addon_name}",
                                'arn': addon['addonArn'],
                                'name': addon_name,
                                'region': region,
                                'details': {
                                    'cluster': cluster_name,
                                    'status': addon.get('status'),
                                    'addon_version': addon.get('addonVersion'),
                                    'service_account_role_arn': addon.get('serviceAccountRoleArn'),
                                },
                                'tags': addon.get('tags', {})
                            })
                        except Exception:
                            pass
            except Exception:
                pass

        except Exception:
            pass

    return resources
