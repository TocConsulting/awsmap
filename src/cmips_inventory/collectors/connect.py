"""
AWS Connect resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Connect supported regions (from https://docs.aws.amazon.com/general/latest/gr/connect_region.html)
CONNECT_REGIONS = {
    'us-east-1', 'us-west-2',
    'af-south-1',
    'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-2',
}


def collect_connect_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Connect resources: instances, queues, routing profiles, and contact flows.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in CONNECT_REGIONS:
        return []

    resources = []
    connect = session.client('connect', region_name=region)

    # Instances
    try:
        paginator = connect.get_paginator('list_instances')
        for page in paginator.paginate():
            for instance in page.get('InstanceSummaryList', []):
                instance_id = instance['Id']
                instance_arn = instance.get('Arn', '')
                instance_alias = instance.get('InstanceAlias', instance_id)

                details = {
                    'instance_status': instance.get('InstanceStatus'),
                    'service_role': instance.get('ServiceRole'),
                    'created_time': str(instance.get('CreatedTime', '')),
                    'inbound_calls_enabled': instance.get('InboundCallsEnabled'),
                    'outbound_calls_enabled': instance.get('OutboundCallsEnabled'),
                    'identity_management_type': instance.get('IdentityManagementType'),
                    'instance_access_url': instance.get('InstanceAccessUrl'),
                }

                resources.append({
                    'service': 'connect',
                    'type': 'instance',
                    'id': instance_id,
                    'arn': instance_arn,
                    'name': instance_alias,
                    'region': region,
                    'details': details,
                    'tags': {}
                })

                # Queues for this instance
                try:
                    queue_paginator = connect.get_paginator('list_queues')
                    for queue_page in queue_paginator.paginate(InstanceId=instance_id):
                        for queue in queue_page.get('QueueSummaryList', []):
                            queue_id = queue['Id']
                            queue_arn = queue.get('Arn', '')
                            queue_name = queue.get('Name', queue_id)

                            queue_details = {
                                'instance_id': instance_id,
                                'queue_type': queue.get('QueueType'),
                                'last_modified_time': str(queue.get('LastModifiedTime', '')),
                                'last_modified_region': queue.get('LastModifiedRegion'),
                            }

                            resources.append({
                                'service': 'connect',
                                'type': 'queue',
                                'id': queue_id,
                                'arn': queue_arn,
                                'name': queue_name,
                                'region': region,
                                'details': queue_details,
                                'tags': {}
                            })
                except Exception:
                    pass

                # Routing Profiles for this instance
                try:
                    rp_paginator = connect.get_paginator('list_routing_profiles')
                    for rp_page in rp_paginator.paginate(InstanceId=instance_id):
                        for rp in rp_page.get('RoutingProfileSummaryList', []):
                            rp_id = rp['Id']
                            rp_arn = rp.get('Arn', '')
                            rp_name = rp.get('Name', rp_id)

                            rp_details = {
                                'instance_id': instance_id,
                                'last_modified_time': str(rp.get('LastModifiedTime', '')),
                                'last_modified_region': rp.get('LastModifiedRegion'),
                            }

                            resources.append({
                                'service': 'connect',
                                'type': 'routing-profile',
                                'id': rp_id,
                                'arn': rp_arn,
                                'name': rp_name,
                                'region': region,
                                'details': rp_details,
                                'tags': {}
                            })
                except Exception:
                    pass

                # Contact Flows for this instance
                try:
                    cf_paginator = connect.get_paginator('list_contact_flows')
                    for cf_page in cf_paginator.paginate(InstanceId=instance_id):
                        for cf in cf_page.get('ContactFlowSummaryList', []):
                            cf_id = cf['Id']
                            cf_arn = cf.get('Arn', '')
                            cf_name = cf.get('Name', cf_id)

                            cf_details = {
                                'instance_id': instance_id,
                                'contact_flow_type': cf.get('ContactFlowType'),
                                'contact_flow_state': cf.get('ContactFlowState'),
                                'contact_flow_status': cf.get('ContactFlowStatus'),
                            }

                            resources.append({
                                'service': 'connect',
                                'type': 'contact-flow',
                                'id': cf_id,
                                'arn': cf_arn,
                                'name': cf_name,
                                'region': region,
                                'details': cf_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
