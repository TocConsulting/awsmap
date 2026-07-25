"""
AWS Outposts resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_outposts_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Outposts resources: outposts and sites.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    outposts = session.client('outposts', region_name=region)

    # Outposts
    try:
        paginator = outposts.get_paginator('list_outposts')
        for page in paginator.paginate():
            for outpost in page.get('Outposts', []):
                outpost_id = outpost['OutpostId']
                outpost_arn = outpost.get('OutpostArn', f"arn:aws:outposts:{region}:{account_id}:outpost/{outpost_id}")
                outpost_name = outpost.get('Name', outpost_id)

                details = {
                    'description': outpost.get('Description'),
                    'life_cycle_status': outpost.get('LifeCycleStatus'),
                    'availability_zone': outpost.get('AvailabilityZone'),
                    'availability_zone_id': outpost.get('AvailabilityZoneId'),
                    'site_id': outpost.get('SiteId'),
                    'supported_hardware_type': outpost.get('SupportedHardwareType'),
                }

                tags = outpost.get('Tags', {})

                resources.append({
                    'service': 'outposts',
                    'type': 'outpost',
                    'id': outpost_id,
                    'arn': outpost_arn,
                    'name': outpost_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Sites
    try:
        paginator = outposts.get_paginator('list_sites')
        for page in paginator.paginate():
            for site in page.get('Sites', []):
                site_id = site['SiteId']
                site_arn = site.get('SiteArn', f"arn:aws:outposts:{region}:{account_id}:site/{site_id}")
                site_name = site.get('Name', site_id)

                details = {
                    'description': site.get('Description'),
                    'notes': site.get('Notes'),
                    'country_code': site.get('OperatingAddressCountryCode'),
                    'state_or_region': site.get('OperatingAddressStateOrRegion'),
                    'city': site.get('OperatingAddressCity'),
                }

                tags = site.get('Tags', {})

                resources.append({
                    'service': 'outposts',
                    'type': 'site',
                    'id': site_id,
                    'arn': site_arn,
                    'name': site_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
