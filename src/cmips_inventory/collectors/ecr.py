"""
ECR resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_ecr_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect ECR resources: repositories.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ecr = session.client('ecr', region_name=region)

    # ECR Repositories
    try:
        paginator = ecr.get_paginator('describe_repositories')
        for page in paginator.paginate():
            for repo in page.get('repositories', []):
                repo_name = repo['repositoryName']
                repo_arn = repo['repositoryArn']

                # Get tags
                tags = {}
                try:
                    tag_response = ecr.list_tags_for_resource(resourceArn=repo_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                # Get image count
                image_count = 0
                try:
                    img_paginator = ecr.get_paginator('list_images')
                    for img_page in img_paginator.paginate(repositoryName=repo_name):
                        image_count += len(img_page.get('imageIds', []))
                except Exception:
                    pass

                # Get lifecycle policy
                has_lifecycle_policy = False
                try:
                    ecr.get_lifecycle_policy(repositoryName=repo_name)
                    has_lifecycle_policy = True
                except ecr.exceptions.LifecyclePolicyNotFoundException:
                    pass
                except Exception:
                    pass

                # Get scanning configuration
                scan_on_push = repo.get('imageScanningConfiguration', {}).get('scanOnPush', False)

                resources.append({
                    'service': 'ecr',
                    'type': 'repository',
                    'id': repo_name,
                    'arn': repo_arn,
                    'name': repo_name,
                    'region': region,
                    'details': {
                        'repository_uri': repo.get('repositoryUri'),
                        'created_at': str(repo.get('createdAt', '')),
                        'image_tag_mutability': repo.get('imageTagMutability'),
                        'scan_on_push': scan_on_push,
                        'encryption_type': repo.get('encryptionConfiguration', {}).get('encryptionType'),
                        'image_count': image_count,
                        'has_lifecycle_policy': has_lifecycle_policy,
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
