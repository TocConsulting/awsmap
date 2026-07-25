"""
AWS ECR Public resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_ecr_public_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS ECR Public resources: public repositories.

    Note: ECR Public is only available in us-east-1 region.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # ECR Public is only available in us-east-1
    if region != 'us-east-1':
        return []

    resources = []
    ecr_public = session.client('ecr-public', region_name='us-east-1')

    # Public Repositories
    try:
        paginator = ecr_public.get_paginator('describe_repositories')
        for page in paginator.paginate():
            for repo in page.get('repositories', []):
                repo_name = repo['repositoryName']
                repo_arn = repo.get('repositoryArn', f"arn:aws:ecr-public::{account_id}:repository/{repo_name}")
                repo_uri = repo.get('repositoryUri', '')

                details = {
                    'registry_id': repo.get('registryId'),
                    'repository_uri': repo_uri,
                    'created_at': str(repo.get('createdAt', '')),
                }

                # Get repository catalog data
                try:
                    catalog_response = ecr_public.get_repository_catalog_data(repositoryName=repo_name)
                    catalog = catalog_response.get('catalogData', {})
                    details.update({
                        'description': catalog.get('description'),
                        'about_text': catalog.get('aboutText')[:200] if catalog.get('aboutText') else None,
                        'usage_text': catalog.get('usageText')[:200] if catalog.get('usageText') else None,
                        'architectures': catalog.get('architectures', []),
                        'operating_systems': catalog.get('operatingSystems', []),
                        'logo_url': catalog.get('logoUrl'),
                        'marketplace_certified': catalog.get('marketplaceCertified'),
                    })
                except Exception:
                    pass

                # Get repository policy
                try:
                    policy_response = ecr_public.get_repository_policy(repositoryName=repo_name)
                    details['has_policy'] = True
                except Exception:
                    details['has_policy'] = False

                # Get tags
                tags = {}
                try:
                    tag_response = ecr_public.list_tags_for_resource(resourceArn=repo_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'ecr-public',
                    'type': 'repository',
                    'id': repo_name,
                    'arn': repo_arn,
                    'name': repo_name,
                    'region': 'us-east-1',
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
