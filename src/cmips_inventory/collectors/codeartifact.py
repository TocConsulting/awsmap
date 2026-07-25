"""
AWS CodeArtifact resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


# CodeArtifact supported regions (not available in all regions)
CODEARTIFACT_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'eu-south-1',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
}


def collect_codeartifact_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS CodeArtifact resources: domains, repositories, and package groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions to avoid connection timeouts
    if region not in CODEARTIFACT_REGIONS:
        return []

    resources = []
    codeartifact = session.client('codeartifact', region_name=region)

    # Domains
    domain_names = []
    try:
        paginator = codeartifact.get_paginator('list_domains')
        for page in paginator.paginate():
            for domain in page.get('domains', []):
                domain_name = domain['name']
                domain_names.append(domain_name)
                domain_arn = domain.get('arn', f"arn:aws:codeartifact:{region}:{account_id}:domain/{domain_name}")

                details = {
                    'owner': domain.get('owner'),
                    'status': domain.get('status'),
                    'created_time': str(domain.get('createdTime', '')),
                    'encryption_key': domain.get('encryptionKey'),
                }

                # Get detailed domain info
                try:
                    desc_response = codeartifact.describe_domain(domain=domain_name)
                    domain_desc = desc_response.get('domain', {})
                    details.update({
                        'repository_count': domain_desc.get('repositoryCount'),
                        'asset_size_bytes': domain_desc.get('assetSizeBytes'),
                        's3_bucket_arn': domain_desc.get('s3BucketArn'),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = codeartifact.list_tags_for_resource(resourceArn=domain_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'codeartifact',
                    'type': 'domain',
                    'id': domain_name,
                    'arn': domain_arn,
                    'name': domain_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Repositories
    try:
        paginator = codeartifact.get_paginator('list_repositories')
        for page in paginator.paginate():
            for repo in page.get('repositories', []):
                repo_name = repo['name']
                domain_name = repo.get('domainName', '')
                repo_arn = repo.get('arn', f"arn:aws:codeartifact:{region}:{account_id}:repository/{domain_name}/{repo_name}")

                details = {
                    'domain_name': domain_name,
                    'domain_owner': repo.get('domainOwner'),
                    'description': repo.get('description'),
                    'administrator_account': repo.get('administratorAccount'),
                    'created_time': str(repo.get('createdTime', '')),
                }

                # Get detailed repository info
                try:
                    desc_response = codeartifact.describe_repository(
                        domain=domain_name,
                        repository=repo_name
                    )
                    repo_desc = desc_response.get('repository', {})
                    details.update({
                        'description': repo_desc.get('description'),
                        'upstreams': [u.get('repositoryName') for u in repo_desc.get('upstreams', [])],
                        'external_connections': [e.get('externalConnectionName') for e in repo_desc.get('externalConnections', [])],
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = codeartifact.list_tags_for_resource(resourceArn=repo_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'codeartifact',
                    'type': 'repository',
                    'id': f"{domain_name}/{repo_name}",
                    'arn': repo_arn,
                    'name': repo_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Package Groups (per domain)
    for domain_name in domain_names:
        try:
            paginator = codeartifact.get_paginator('list_package_groups')
            for page in paginator.paginate(domain=domain_name):
                for group in page.get('packageGroups', []):
                    group_pattern = group['pattern']
                    group_arn = group.get('arn', f"arn:aws:codeartifact:{region}:{account_id}:package-group/{domain_name}/{group_pattern}")

                    details = {
                        'domain_name': domain_name,
                        'domain_owner': group.get('domainOwner'),
                        'description': group.get('description'),
                        'origin_configuration': group.get('originConfiguration'),
                        'parent': group.get('parent'),
                        'contact_info': group.get('contactInfo'),
                        'created_time': str(group.get('createdTime', '')),
                    }

                    # Get tags
                    tags = {}
                    try:
                        tag_response = codeartifact.list_tags_for_resource(resourceArn=group_arn)
                        for tag in tag_response.get('tags', []):
                            tags[tag.get('key', '')] = tag.get('value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'codeartifact',
                        'type': 'package-group',
                        'id': f"{domain_name}/{group_pattern}",
                        'arn': group_arn,
                        'name': group_pattern,
                        'region': region,
                        'details': details,
                        'tags': tags
                    })
        except Exception:
            pass

    return resources
