"""
EMR resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_emr_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EMR resources: clusters, studios.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    emr = session.client('emr', region_name=region)

    # EMR Clusters (active only - STARTING, BOOTSTRAPPING, RUNNING, WAITING)
    try:
        paginator = emr.get_paginator('list_clusters')
        for page in paginator.paginate(ClusterStates=['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING', 'TERMINATING']):
            for cluster_summary in page.get('Clusters', []):
                cluster_id = cluster_summary['Id']

                try:
                    # Get cluster details
                    cluster_response = emr.describe_cluster(ClusterId=cluster_id)
                    cluster = cluster_response.get('Cluster', {})

                    cluster_arn = cluster.get('ClusterArn', f"arn:aws:elasticmapreduce:{region}:{account_id}:cluster/{cluster_id}")

                    # Get tags
                    tags = {}
                    for tag in cluster.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')

                    resources.append({
                        'service': 'emr',
                        'type': 'cluster',
                        'id': cluster_id,
                        'arn': cluster_arn,
                        'name': cluster.get('Name', cluster_id),
                        'region': region,
                        'details': {
                            'status': cluster.get('Status', {}).get('State'),
                            'status_reason': cluster.get('Status', {}).get('StateChangeReason', {}).get('Message'),
                            'release_label': cluster.get('ReleaseLabel'),
                            'applications': [app.get('Name') for app in cluster.get('Applications', [])],
                            'normalized_instance_hours': cluster.get('NormalizedInstanceHours'),
                            'master_public_dns_name': cluster.get('MasterPublicDnsName'),
                            'log_uri': cluster.get('LogUri'),
                            'auto_terminate': cluster.get('AutoTerminate'),
                            'termination_protected': cluster.get('TerminationProtected'),
                            'visible_to_all_users': cluster.get('VisibleToAllUsers'),
                            'service_role': cluster.get('ServiceRole'),
                            'ec2_instance_attributes': {
                                'key_name': cluster.get('Ec2InstanceAttributes', {}).get('Ec2KeyName'),
                                'subnet_id': cluster.get('Ec2InstanceAttributes', {}).get('Ec2SubnetId'),
                                'availability_zone': cluster.get('Ec2InstanceAttributes', {}).get('Ec2AvailabilityZone'),
                            },
                            'scale_down_behavior': cluster.get('ScaleDownBehavior'),
                            'ebs_root_volume_size': cluster.get('EbsRootVolumeSize'),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # EMR Studios
    try:
        paginator = emr.get_paginator('list_studios')
        for page in paginator.paginate():
            for studio_summary in page.get('Studios', []):
                studio_id = studio_summary['StudioId']

                try:
                    # Get studio details
                    studio_response = emr.describe_studio(StudioId=studio_id)
                    studio = studio_response.get('Studio', {})

                    studio_arn = studio.get('StudioArn', f"arn:aws:elasticmapreduce:{region}:{account_id}:studio/{studio_id}")

                    # Get tags
                    tags = {}
                    for tag in studio.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')

                    resources.append({
                        'service': 'emr',
                        'type': 'studio',
                        'id': studio_id,
                        'arn': studio_arn,
                        'name': studio.get('Name', studio_id),
                        'region': region,
                        'details': {
                            'description': studio.get('Description'),
                            'auth_mode': studio.get('AuthMode'),
                            'vpc_id': studio.get('VpcId'),
                            'subnet_ids': studio.get('SubnetIds', []),
                            'url': studio.get('Url'),
                            'default_s3_location': studio.get('DefaultS3Location'),
                            'service_role': studio.get('ServiceRole'),
                            'user_role': studio.get('UserRole'),
                            'workspace_security_group_id': studio.get('WorkspaceSecurityGroupId'),
                            'engine_security_group_id': studio.get('EngineSecurityGroupId'),
                            'creation_time': str(studio.get('CreationTime', '')),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # EMR Serverless Applications
    try:
        emr_serverless = session.client('emr-serverless', region_name=region)
        paginator = emr_serverless.get_paginator('list_applications')
        for page in paginator.paginate():
            for app in page.get('applications', []):
                app_id = app['id']
                app_arn = app['arn']

                # Get tags
                tags = {}
                try:
                    tag_response = emr_serverless.list_tags_for_resource(resourceArn=app_arn)
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'emr',
                    'type': 'serverless-application',
                    'id': app_id,
                    'arn': app_arn,
                    'name': app.get('name', app_id),
                    'region': region,
                    'details': {
                        'state': app.get('state'),
                        'state_details': app.get('stateDetails'),
                        'type': app.get('type'),
                        'release_label': app.get('releaseLabel'),
                        'architecture': app.get('architecture'),
                        'created_at': str(app.get('createdAt', '')),
                        'updated_at': str(app.get('updatedAt', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
