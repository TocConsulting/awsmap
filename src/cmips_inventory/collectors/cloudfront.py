"""
CloudFront resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_cloudfront_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CloudFront resources: distributions, functions, origin access identities.

    Args:
        session: boto3.Session to use
        region: Not used for CloudFront (global service)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    cloudfront = session.client('cloudfront')

    # CloudFront Distributions
    try:
        paginator = cloudfront.get_paginator('list_distributions')
        for page in paginator.paginate():
            dist_list = page.get('DistributionList', {})
            for dist in dist_list.get('Items', []):
                dist_id = dist['Id']
                dist_arn = dist['ARN']

                # Get tags
                tags = {}
                try:
                    tag_response = cloudfront.list_tags_for_resource(Resource=dist_arn)
                    for tag in tag_response.get('Tags', {}).get('Items', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                origins = dist.get('Origins', {}).get('Items', [])
                aliases = dist.get('Aliases', {}).get('Items', [])

                resources.append({
                    'service': 'cloudfront',
                    'type': 'distribution',
                    'id': dist_id,
                    'arn': dist_arn,
                    'name': tags.get('Name') or aliases[0] if aliases else dist_id,
                    'region': 'global',
                    'details': {
                        'domain_name': dist.get('DomainName'),
                        'status': dist.get('Status'),
                        'enabled': dist.get('Enabled'),
                        'aliases': aliases,
                        'origins': [o.get('DomainName') for o in origins],
                        'price_class': dist.get('PriceClass'),
                        'http_version': dist.get('HttpVersion'),
                        'is_ipv6_enabled': dist.get('IsIPV6Enabled'),
                        'default_root_object': dist.get('DefaultRootObject'),
                        'comment': dist.get('Comment'),
                        'web_acl_id': dist.get('WebACLId'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # CloudFront Functions
    try:
        paginator = cloudfront.get_paginator('list_functions')
        for page in paginator.paginate():
            func_list = page.get('FunctionList', {})
            for func in func_list.get('Items', []):
                func_name = func['Name']
                func_arn = func['FunctionMetadata']['FunctionARN']

                resources.append({
                    'service': 'cloudfront',
                    'type': 'function',
                    'id': func_name,
                    'arn': func_arn,
                    'name': func_name,
                    'region': 'global',
                    'details': {
                        'status': func.get('Status'),
                        'stage': func.get('FunctionMetadata', {}).get('Stage'),
                        'created_time': str(func.get('FunctionMetadata', {}).get('CreatedTime', '')),
                        'last_modified_time': str(func.get('FunctionMetadata', {}).get('LastModifiedTime', '')),
                        'comment': func.get('FunctionConfig', {}).get('Comment'),
                        'runtime': func.get('FunctionConfig', {}).get('Runtime'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Origin Access Identities
    try:
        paginator = cloudfront.get_paginator('list_cloud_front_origin_access_identities')
        for page in paginator.paginate():
            oai_list = page.get('CloudFrontOriginAccessIdentityList', {})
            for oai in oai_list.get('Items', []):
                oai_id = oai['Id']

                resources.append({
                    'service': 'cloudfront',
                    'type': 'origin-access-identity',
                    'id': oai_id,
                    'arn': f"arn:aws:cloudfront::{account_id}:origin-access-identity/{oai_id}",
                    'name': oai.get('Comment') or oai_id,
                    'region': 'global',
                    'details': {
                        's3_canonical_user_id': oai.get('S3CanonicalUserId'),
                        'comment': oai.get('Comment'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Origin Access Controls
    try:
        response = cloudfront.list_origin_access_controls()
        oac_list = response.get('OriginAccessControlList', {})
        for oac in oac_list.get('Items', []):
            oac_id = oac['Id']

            resources.append({
                'service': 'cloudfront',
                'type': 'origin-access-control',
                'id': oac_id,
                'arn': f"arn:aws:cloudfront::{account_id}:origin-access-control/{oac_id}",
                'name': oac.get('Name') or oac_id,
                'region': 'global',
                'details': {
                    'description': oac.get('Description'),
                    'origin_access_control_origin_type': oac.get('OriginAccessControlOriginType'),
                    'signing_behavior': oac.get('SigningBehavior'),
                    'signing_protocol': oac.get('SigningProtocol'),
                },
                'tags': {}
            })
    except Exception:
        pass

    # Cache Policies (custom only)
    try:
        response = cloudfront.list_cache_policies(Type='custom')
        policy_list = response.get('CachePolicyList', {})
        for policy in policy_list.get('Items', []):
            cp = policy.get('CachePolicy', {})
            cp_id = cp.get('Id')
            if not cp_id:
                continue

            resources.append({
                'service': 'cloudfront',
                'type': 'cache-policy',
                'id': cp_id,
                'arn': f"arn:aws:cloudfront::{account_id}:cache-policy/{cp_id}",
                'name': cp.get('CachePolicyConfig', {}).get('Name') or cp_id,
                'region': 'global',
                'details': {
                    'comment': cp.get('CachePolicyConfig', {}).get('Comment'),
                    'default_ttl': cp.get('CachePolicyConfig', {}).get('DefaultTTL'),
                    'max_ttl': cp.get('CachePolicyConfig', {}).get('MaxTTL'),
                    'min_ttl': cp.get('CachePolicyConfig', {}).get('MinTTL'),
                },
                'tags': {}
            })
    except Exception:
        pass

    return resources
