"""
AWS Location Service resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Location Service supported regions (from https://docs.aws.amazon.com/location/latest/developerguide/location-regions.html)
LOCATION_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-north-1',
    'sa-east-1',
}


def collect_location_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Location Service resources: maps, place indexes, route calculators,
    geofence collections, and trackers.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in LOCATION_REGIONS:
        return []

    resources = []
    location = session.client('location', region_name=region)

    # Maps
    try:
        paginator = location.get_paginator('list_maps')
        for page in paginator.paginate():
            for map_entry in page.get('Entries', []):
                map_name = map_entry['MapName']
                map_arn = f"arn:aws:geo:{region}:{account_id}:map/{map_name}"

                details = {
                    'description': map_entry.get('Description'),
                    'data_source': map_entry.get('DataSource'),
                    'pricing_plan': map_entry.get('PricingPlan'),
                }

                resources.append({
                    'service': 'location',
                    'type': 'map',
                    'id': map_name,
                    'arn': map_arn,
                    'name': map_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Place Indexes
    try:
        paginator = location.get_paginator('list_place_indexes')
        for page in paginator.paginate():
            for index in page.get('Entries', []):
                index_name = index['IndexName']
                index_arn = f"arn:aws:geo:{region}:{account_id}:place-index/{index_name}"

                details = {
                    'description': index.get('Description'),
                    'data_source': index.get('DataSource'),
                    'pricing_plan': index.get('PricingPlan'),
                }

                resources.append({
                    'service': 'location',
                    'type': 'place-index',
                    'id': index_name,
                    'arn': index_arn,
                    'name': index_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Route Calculators
    try:
        paginator = location.get_paginator('list_route_calculators')
        for page in paginator.paginate():
            for calc in page.get('Entries', []):
                calc_name = calc['CalculatorName']
                calc_arn = f"arn:aws:geo:{region}:{account_id}:route-calculator/{calc_name}"

                details = {
                    'description': calc.get('Description'),
                    'data_source': calc.get('DataSource'),
                    'pricing_plan': calc.get('PricingPlan'),
                }

                resources.append({
                    'service': 'location',
                    'type': 'route-calculator',
                    'id': calc_name,
                    'arn': calc_arn,
                    'name': calc_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Geofence Collections
    try:
        paginator = location.get_paginator('list_geofence_collections')
        for page in paginator.paginate():
            for collection in page.get('Entries', []):
                coll_name = collection['CollectionName']
                coll_arn = f"arn:aws:geo:{region}:{account_id}:geofence-collection/{coll_name}"

                details = {
                    'description': collection.get('Description'),
                    'pricing_plan': collection.get('PricingPlan'),
                }

                resources.append({
                    'service': 'location',
                    'type': 'geofence-collection',
                    'id': coll_name,
                    'arn': coll_arn,
                    'name': coll_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Trackers
    try:
        paginator = location.get_paginator('list_trackers')
        for page in paginator.paginate():
            for tracker in page.get('Entries', []):
                tracker_name = tracker['TrackerName']
                tracker_arn = f"arn:aws:geo:{region}:{account_id}:tracker/{tracker_name}"

                details = {
                    'description': tracker.get('Description'),
                    'pricing_plan': tracker.get('PricingPlan'),
                }

                resources.append({
                    'service': 'location',
                    'type': 'tracker',
                    'id': tracker_name,
                    'arn': tracker_arn,
                    'name': tracker_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
