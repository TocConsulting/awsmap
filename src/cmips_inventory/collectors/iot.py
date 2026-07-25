"""
IoT Core resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

# IoT Core supported regions
# https://docs.aws.amazon.com/general/latest/gr/iot-core.html
IOT_REGIONS = {
    # US
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    # Asia Pacific
    'ap-east-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-south-1',
    'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-5',
    # Canada
    'ca-central-1',
    # Europe
    'eu-central-1', 'eu-north-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-south-2',
    # Middle East
    'me-central-1', 'me-south-1',
    # South America
    'sa-east-1',
}


def collect_iot_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect IoT Core resources: things, thing types, thing groups, policies, certificates.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions to avoid timeouts
    if region and region not in IOT_REGIONS:
        return []

    resources = []
    iot = session.client('iot', region_name=region)

    # IoT Things
    try:
        paginator = iot.get_paginator('list_things')
        for page in paginator.paginate():
            for thing in page.get('things', []):
                thing_name = thing['thingName']
                thing_arn = thing.get('thingArn', f"arn:aws:iot:{region}:{account_id}:thing/{thing_name}")

                # Get tags
                tags = {}
                try:
                    tag_response = iot.list_tags_for_resource(resourceArn=thing_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'iot',
                    'type': 'thing',
                    'id': thing_name,
                    'arn': thing_arn,
                    'name': thing_name,
                    'region': region,
                    'details': {
                        'thing_type_name': thing.get('thingTypeName'),
                        'version': thing.get('version'),
                        'attributes': thing.get('attributes', {}),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # IoT Thing Types
    try:
        paginator = iot.get_paginator('list_thing_types')
        for page in paginator.paginate():
            for thing_type in page.get('thingTypes', []):
                tt_name = thing_type['thingTypeName']
                tt_arn = thing_type.get('thingTypeArn', f"arn:aws:iot:{region}:{account_id}:thingtype/{tt_name}")

                # Get tags
                tags = {}
                try:
                    tag_response = iot.list_tags_for_resource(resourceArn=tt_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'iot',
                    'type': 'thing-type',
                    'id': tt_name,
                    'arn': tt_arn,
                    'name': tt_name,
                    'region': region,
                    'details': {
                        'deprecated': thing_type.get('thingTypeMetadata', {}).get('deprecated'),
                        'deprecation_date': str(thing_type.get('thingTypeMetadata', {}).get('deprecationDate', '')),
                        'creation_date': str(thing_type.get('thingTypeMetadata', {}).get('creationDate', '')),
                        'thing_type_description': thing_type.get('thingTypeProperties', {}).get('thingTypeDescription'),
                        'searchable_attributes': thing_type.get('thingTypeProperties', {}).get('searchableAttributes', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # IoT Thing Groups
    try:
        paginator = iot.get_paginator('list_thing_groups')
        for page in paginator.paginate():
            for group in page.get('thingGroups', []):
                group_name = group['groupName']
                group_arn = group.get('groupArn', f"arn:aws:iot:{region}:{account_id}:thinggroup/{group_name}")

                # Get tags
                tags = {}
                try:
                    tag_response = iot.list_tags_for_resource(resourceArn=group_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'iot',
                    'type': 'thing-group',
                    'id': group_name,
                    'arn': group_arn,
                    'name': group_name,
                    'region': region,
                    'details': {},
                    'tags': tags
                })
    except Exception:
        pass

    # IoT Policies
    try:
        paginator = iot.get_paginator('list_policies')
        for page in paginator.paginate():
            for policy in page.get('policies', []):
                policy_name = policy['policyName']
                policy_arn = policy.get('policyArn', f"arn:aws:iot:{region}:{account_id}:policy/{policy_name}")

                # Get tags
                tags = {}
                try:
                    tag_response = iot.list_tags_for_resource(resourceArn=policy_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'iot',
                    'type': 'policy',
                    'id': policy_name,
                    'arn': policy_arn,
                    'name': policy_name,
                    'region': region,
                    'details': {},
                    'tags': tags
                })
    except Exception:
        pass

    # IoT Certificates (active only)
    try:
        paginator = iot.get_paginator('list_certificates')
        for page in paginator.paginate():
            for cert in page.get('certificates', []):
                cert_id = cert['certificateId']
                cert_arn = cert['certificateArn']

                # Skip inactive certificates
                if cert.get('status') != 'ACTIVE':
                    continue

                resources.append({
                    'service': 'iot',
                    'type': 'certificate',
                    'id': cert_id,
                    'arn': cert_arn,
                    'name': cert_id[:12],
                    'region': region,
                    'details': {
                        'status': cert.get('status'),
                        'creation_date': str(cert.get('creationDate', '')),
                        'certificate_mode': cert.get('certificateMode'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
