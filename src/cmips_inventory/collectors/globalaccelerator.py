"""
AWS Global Accelerator resource collector.

Note: Global Accelerator is a global service that requires the us-west-2 region
for all API operations.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_globalaccelerator_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Global Accelerator resources: accelerators, listeners, endpoint groups,
    custom routing accelerators, cross-account attachments, and BYOIP CIDRs.

    Note: Global Accelerator APIs must be called from us-west-2 region.

    Args:
        session: boto3.Session to use
        region: AWS region (ignored - always uses us-west-2)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    # Global Accelerator requires us-west-2 for all API calls
    ga = session.client('globalaccelerator', region_name='us-west-2')

    # Standard Accelerators
    try:
        paginator = ga.get_paginator('list_accelerators')
        for page in paginator.paginate():
            for accel in page.get('Accelerators', []):
                accel_arn = accel['AcceleratorArn']
                accel_name = accel.get('Name', accel_arn.split('/')[-1])

                details = {
                    'status': accel.get('Status'),
                    'enabled': accel.get('Enabled'),
                    'ip_address_type': accel.get('IpAddressType'),
                    'ip_sets': accel.get('IpSets', []),
                    'dns_name': accel.get('DnsName'),
                    'dual_stack_dns_name': accel.get('DualStackDnsName'),
                    'created_time': str(accel.get('CreatedTime', '')),
                    'last_modified_time': str(accel.get('LastModifiedTime', '')),
                }

                # Get accelerator attributes
                try:
                    attr_response = ga.describe_accelerator_attributes(AcceleratorArn=accel_arn)
                    attrs = attr_response.get('AcceleratorAttributes', {})
                    details['flow_logs_enabled'] = attrs.get('FlowLogsEnabled')
                    details['flow_logs_s3_bucket'] = attrs.get('FlowLogsS3Bucket')
                    details['flow_logs_s3_prefix'] = attrs.get('FlowLogsS3Prefix')
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = ga.list_tags_for_resource(ResourceArn=accel_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'globalaccelerator',
                    'type': 'accelerator',
                    'id': accel_arn.split('/')[-1],
                    'arn': accel_arn,
                    'name': accel_name,
                    'region': 'global',
                    'details': details,
                    'tags': tags
                })

                # Listeners for this accelerator
                try:
                    listener_paginator = ga.get_paginator('list_listeners')
                    for listener_page in listener_paginator.paginate(AcceleratorArn=accel_arn):
                        for listener in listener_page.get('Listeners', []):
                            listener_arn = listener['ListenerArn']

                            listener_details = {
                                'accelerator_arn': accel_arn,
                                'port_ranges': listener.get('PortRanges', []),
                                'protocol': listener.get('Protocol'),
                                'client_affinity': listener.get('ClientAffinity'),
                            }

                            resources.append({
                                'service': 'globalaccelerator',
                                'type': 'listener',
                                'id': listener_arn.split('/')[-1],
                                'arn': listener_arn,
                                'name': f"{accel_name}-listener-{listener_arn.split('/')[-1][:8]}",
                                'region': 'global',
                                'details': listener_details,
                                'tags': {}
                            })

                            # Endpoint Groups for this listener
                            try:
                                eg_paginator = ga.get_paginator('list_endpoint_groups')
                                for eg_page in eg_paginator.paginate(ListenerArn=listener_arn):
                                    for eg in eg_page.get('EndpointGroups', []):
                                        eg_arn = eg['EndpointGroupArn']
                                        eg_region = eg.get('EndpointGroupRegion', 'unknown')

                                        eg_details = {
                                            'listener_arn': listener_arn,
                                            'endpoint_group_region': eg_region,
                                            'traffic_dial_percentage': eg.get('TrafficDialPercentage'),
                                            'health_check_port': eg.get('HealthCheckPort'),
                                            'health_check_protocol': eg.get('HealthCheckProtocol'),
                                            'health_check_path': eg.get('HealthCheckPath'),
                                            'health_check_interval_seconds': eg.get('HealthCheckIntervalSeconds'),
                                            'threshold_count': eg.get('ThresholdCount'),
                                            'endpoints_count': len(eg.get('EndpointDescriptions', [])),
                                        }

                                        resources.append({
                                            'service': 'globalaccelerator',
                                            'type': 'endpoint-group',
                                            'id': eg_arn.split('/')[-1],
                                            'arn': eg_arn,
                                            'name': f"{accel_name}-{eg_region}",
                                            'region': 'global',
                                            'details': eg_details,
                                            'tags': {}
                                        })
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # Custom Routing Accelerators
    try:
        paginator = ga.get_paginator('list_custom_routing_accelerators')
        for page in paginator.paginate():
            for accel in page.get('Accelerators', []):
                accel_arn = accel['AcceleratorArn']
                accel_name = accel.get('Name', accel_arn.split('/')[-1])

                details = {
                    'status': accel.get('Status'),
                    'enabled': accel.get('Enabled'),
                    'ip_address_type': accel.get('IpAddressType'),
                    'ip_sets': accel.get('IpSets', []),
                    'dns_name': accel.get('DnsName'),
                    'created_time': str(accel.get('CreatedTime', '')),
                    'last_modified_time': str(accel.get('LastModifiedTime', '')),
                }

                # Get accelerator attributes
                try:
                    attr_response = ga.describe_custom_routing_accelerator_attributes(AcceleratorArn=accel_arn)
                    attrs = attr_response.get('AcceleratorAttributes', {})
                    details['flow_logs_enabled'] = attrs.get('FlowLogsEnabled')
                    details['flow_logs_s3_bucket'] = attrs.get('FlowLogsS3Bucket')
                    details['flow_logs_s3_prefix'] = attrs.get('FlowLogsS3Prefix')
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = ga.list_tags_for_resource(ResourceArn=accel_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'globalaccelerator',
                    'type': 'custom-routing-accelerator',
                    'id': accel_arn.split('/')[-1],
                    'arn': accel_arn,
                    'name': accel_name,
                    'region': 'global',
                    'details': details,
                    'tags': tags
                })

                # Custom Routing Listeners
                try:
                    listener_paginator = ga.get_paginator('list_custom_routing_listeners')
                    for listener_page in listener_paginator.paginate(AcceleratorArn=accel_arn):
                        for listener in listener_page.get('Listeners', []):
                            listener_arn = listener['ListenerArn']

                            listener_details = {
                                'accelerator_arn': accel_arn,
                                'port_ranges': listener.get('PortRanges', []),
                            }

                            resources.append({
                                'service': 'globalaccelerator',
                                'type': 'custom-routing-listener',
                                'id': listener_arn.split('/')[-1],
                                'arn': listener_arn,
                                'name': f"{accel_name}-cr-listener-{listener_arn.split('/')[-1][:8]}",
                                'region': 'global',
                                'details': listener_details,
                                'tags': {}
                            })

                            # Custom Routing Endpoint Groups
                            try:
                                eg_paginator = ga.get_paginator('list_custom_routing_endpoint_groups')
                                for eg_page in eg_paginator.paginate(ListenerArn=listener_arn):
                                    for eg in eg_page.get('EndpointGroups', []):
                                        eg_arn = eg['EndpointGroupArn']
                                        eg_region = eg.get('EndpointGroupRegion', 'unknown')

                                        eg_details = {
                                            'listener_arn': listener_arn,
                                            'endpoint_group_region': eg_region,
                                            'destination_descriptions': eg.get('DestinationDescriptions', []),
                                            'endpoints_count': len(eg.get('EndpointDescriptions', [])),
                                        }

                                        resources.append({
                                            'service': 'globalaccelerator',
                                            'type': 'custom-routing-endpoint-group',
                                            'id': eg_arn.split('/')[-1],
                                            'arn': eg_arn,
                                            'name': f"{accel_name}-cr-{eg_region}",
                                            'region': 'global',
                                            'details': eg_details,
                                            'tags': {}
                                        })
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # Cross-Account Attachments
    try:
        paginator = ga.get_paginator('list_cross_account_attachments')
        for page in paginator.paginate():
            for attachment in page.get('CrossAccountAttachments', []):
                attachment_arn = attachment['AttachmentArn']
                attachment_name = attachment.get('Name', attachment_arn.split('/')[-1])

                details = {
                    'principals': attachment.get('Principals', []),
                    'resources': attachment.get('Resources', []),
                    'last_modified_time': str(attachment.get('LastModifiedTime', '')),
                    'created_time': str(attachment.get('CreatedTime', '')),
                }

                # Get tags
                tags = {}
                try:
                    tag_response = ga.list_tags_for_resource(ResourceArn=attachment_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'globalaccelerator',
                    'type': 'cross-account-attachment',
                    'id': attachment_arn.split('/')[-1],
                    'arn': attachment_arn,
                    'name': attachment_name,
                    'region': 'global',
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # BYOIP CIDRs
    try:
        paginator = ga.get_paginator('list_byoip_cidrs')
        for page in paginator.paginate():
            for cidr in page.get('ByoipCidrs', []):
                cidr_block = cidr['Cidr']

                details = {
                    'state': cidr.get('State'),
                    'events': cidr.get('Events', []),
                }

                resources.append({
                    'service': 'globalaccelerator',
                    'type': 'byoip-cidr',
                    'id': cidr_block,
                    'arn': f"arn:aws:globalaccelerator::{account_id}:byoipcidr/{cidr_block}",
                    'name': cidr_block,
                    'region': 'global',
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
