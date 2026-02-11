"""
VPC resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

from aws_inventory.collector import tags_to_dict, get_tag_value


def collect_vpc_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect VPC resources: VPCs, subnets, route tables, internet gateways,
    NAT gateways, VPC endpoints, VPC peering, transit gateways.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ec2 = session.client('ec2', region_name=region)

    # VPCs
    try:
        paginator = ec2.get_paginator('describe_vpcs')
        for page in paginator.paginate():
            for vpc in page.get('Vpcs', []):
                tags = vpc.get('Tags', [])
                resources.append({
                    'service': 'vpc',
                    'type': 'vpc',
                    'id': vpc['VpcId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:vpc/{vpc['VpcId']}",
                    'name': get_tag_value(tags, 'Name') or vpc['VpcId'],
                    'region': region,
                    'is_default': vpc.get('IsDefault', False),
                    'details': {
                        'cidr_block': vpc.get('CidrBlock'),
                        'state': vpc.get('State'),
                        'is_default': vpc.get('IsDefault'),
                        'dhcp_options_id': vpc.get('DhcpOptionsId'),
                        'instance_tenancy': vpc.get('InstanceTenancy'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # Build set of default VPC IDs and their DHCP options for marking child resources
    default_vpc_ids = {r['id'] for r in resources if r.get('is_default')}
    default_dhcp_ids = {r['details']['dhcp_options_id'] for r in resources if r.get('is_default') and r['details'].get('dhcp_options_id')}

    # Subnets
    try:
        paginator = ec2.get_paginator('describe_subnets')
        for page in paginator.paginate():
            for subnet in page.get('Subnets', []):
                tags = subnet.get('Tags', [])
                resources.append({
                    'service': 'vpc',
                    'type': 'subnet',
                    'id': subnet['SubnetId'],
                    'arn': subnet.get('SubnetArn', f"arn:aws:ec2:{region}:{account_id}:subnet/{subnet['SubnetId']}"),
                    'name': get_tag_value(tags, 'Name') or subnet['SubnetId'],
                    'region': region,
                    'is_default': subnet.get('DefaultForAz', False),
                    'details': {
                        'vpc_id': subnet.get('VpcId'),
                        'cidr_block': subnet.get('CidrBlock'),
                        'availability_zone': subnet.get('AvailabilityZone'),
                        'state': subnet.get('State'),
                        'available_ip_count': subnet.get('AvailableIpAddressCount'),
                        'map_public_ip_on_launch': subnet.get('MapPublicIpOnLaunch'),
                        'default_for_az': subnet.get('DefaultForAz'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # Route Tables
    try:
        paginator = ec2.get_paginator('describe_route_tables')
        for page in paginator.paginate():
            for rt in page.get('RouteTables', []):
                tags = rt.get('Tags', [])
                is_main = any(a.get('Main') for a in rt.get('Associations', []))
                resources.append({
                    'service': 'vpc',
                    'type': 'route-table',
                    'id': rt['RouteTableId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:route-table/{rt['RouteTableId']}",
                    'name': get_tag_value(tags, 'Name') or rt['RouteTableId'],
                    'region': region,
                    'is_default': rt.get('VpcId') in default_vpc_ids and is_main,
                    'details': {
                        'vpc_id': rt.get('VpcId'),
                        'routes_count': len(rt.get('Routes', [])),
                        'associations_count': len(rt.get('Associations', [])),
                        'main': is_main,
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # Internet Gateways
    try:
        paginator = ec2.get_paginator('describe_internet_gateways')
        for page in paginator.paginate():
            for igw in page.get('InternetGateways', []):
                tags = igw.get('Tags', [])
                attachments = igw.get('Attachments', [])
                resources.append({
                    'service': 'vpc',
                    'type': 'internet-gateway',
                    'id': igw['InternetGatewayId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:internet-gateway/{igw['InternetGatewayId']}",
                    'name': get_tag_value(tags, 'Name') or igw['InternetGatewayId'],
                    'region': region,
                    'is_default': (attachments[0].get('VpcId') in default_vpc_ids) if attachments else False,
                    'details': {
                        'vpc_id': attachments[0].get('VpcId') if attachments else None,
                        'state': attachments[0].get('State') if attachments else 'detached',
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # NAT Gateways
    try:
        paginator = ec2.get_paginator('describe_nat_gateways')
        for page in paginator.paginate():
            for nat in page.get('NatGateways', []):
                tags = nat.get('Tags', [])

                # Skip deleted NAT gateways
                if nat.get('State') == 'deleted':
                    continue

                resources.append({
                    'service': 'vpc',
                    'type': 'nat-gateway',
                    'id': nat['NatGatewayId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:natgateway/{nat['NatGatewayId']}",
                    'name': get_tag_value(tags, 'Name') or nat['NatGatewayId'],
                    'region': region,
                    'details': {
                        'vpc_id': nat.get('VpcId'),
                        'subnet_id': nat.get('SubnetId'),
                        'state': nat.get('State'),
                        'connectivity_type': nat.get('ConnectivityType'),
                        'public_ip': nat.get('NatGatewayAddresses', [{}])[0].get('PublicIp') if nat.get('NatGatewayAddresses') else None,
                        'private_ip': nat.get('NatGatewayAddresses', [{}])[0].get('PrivateIp') if nat.get('NatGatewayAddresses') else None,
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # VPC Endpoints
    try:
        paginator = ec2.get_paginator('describe_vpc_endpoints')
        for page in paginator.paginate():
            for endpoint in page.get('VpcEndpoints', []):
                tags = endpoint.get('Tags', [])
                resources.append({
                    'service': 'vpc',
                    'type': 'vpc-endpoint',
                    'id': endpoint['VpcEndpointId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:vpc-endpoint/{endpoint['VpcEndpointId']}",
                    'name': get_tag_value(tags, 'Name') or endpoint['VpcEndpointId'],
                    'region': region,
                    'details': {
                        'vpc_id': endpoint.get('VpcId'),
                        'service_name': endpoint.get('ServiceName'),
                        'endpoint_type': endpoint.get('VpcEndpointType'),
                        'state': endpoint.get('State'),
                        'private_dns_enabled': endpoint.get('PrivateDnsEnabled'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # VPC Peering Connections
    try:
        paginator = ec2.get_paginator('describe_vpc_peering_connections')
        for page in paginator.paginate():
            for pcx in page.get('VpcPeeringConnections', []):
                tags = pcx.get('Tags', [])

                # Skip deleted peering connections
                status = pcx.get('Status', {}).get('Code', '')
                if status in ['deleted', 'rejected', 'failed']:
                    continue

                resources.append({
                    'service': 'vpc',
                    'type': 'vpc-peering',
                    'id': pcx['VpcPeeringConnectionId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:vpc-peering-connection/{pcx['VpcPeeringConnectionId']}",
                    'name': get_tag_value(tags, 'Name') or pcx['VpcPeeringConnectionId'],
                    'region': region,
                    'details': {
                        'status': status,
                        'requester_vpc_id': pcx.get('RequesterVpcInfo', {}).get('VpcId'),
                        'requester_cidr': pcx.get('RequesterVpcInfo', {}).get('CidrBlock'),
                        'accepter_vpc_id': pcx.get('AccepterVpcInfo', {}).get('VpcId'),
                        'accepter_cidr': pcx.get('AccepterVpcInfo', {}).get('CidrBlock'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # Transit Gateways (owned by this account)
    try:
        paginator = ec2.get_paginator('describe_transit_gateways')
        for page in paginator.paginate():
            for tgw in page.get('TransitGateways', []):
                # Only include transit gateways owned by this account
                if tgw.get('OwnerId') != account_id:
                    continue

                tags = tgw.get('Tags', [])
                resources.append({
                    'service': 'vpc',
                    'type': 'transit-gateway',
                    'id': tgw['TransitGatewayId'],
                    'arn': tgw.get('TransitGatewayArn', f"arn:aws:ec2:{region}:{account_id}:transit-gateway/{tgw['TransitGatewayId']}"),
                    'name': get_tag_value(tags, 'Name') or tgw['TransitGatewayId'],
                    'region': region,
                    'details': {
                        'state': tgw.get('State'),
                        'description': tgw.get('Description'),
                        'amazon_side_asn': tgw.get('Options', {}).get('AmazonSideAsn'),
                        'auto_accept_shared_attachments': tgw.get('Options', {}).get('AutoAcceptSharedAttachments'),
                        'default_route_table_association': tgw.get('Options', {}).get('DefaultRouteTableAssociation'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # Transit Gateway Attachments
    try:
        paginator = ec2.get_paginator('describe_transit_gateway_attachments')
        for page in paginator.paginate():
            for attach in page.get('TransitGatewayAttachments', []):
                tags = attach.get('Tags', [])

                # Skip deleted attachments
                if attach.get('State') == 'deleted':
                    continue

                resources.append({
                    'service': 'vpc',
                    'type': 'transit-gateway-attachment',
                    'id': attach['TransitGatewayAttachmentId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:transit-gateway-attachment/{attach['TransitGatewayAttachmentId']}",
                    'name': get_tag_value(tags, 'Name') or attach['TransitGatewayAttachmentId'],
                    'region': region,
                    'details': {
                        'transit_gateway_id': attach.get('TransitGatewayId'),
                        'resource_type': attach.get('ResourceType'),
                        'resource_id': attach.get('ResourceId'),
                        'state': attach.get('State'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # DHCP Options Sets
    try:
        response = ec2.describe_dhcp_options()
        for dhcp in response.get('DhcpOptions', []):
            tags = dhcp.get('Tags', [])
            resources.append({
                'service': 'vpc',
                'type': 'dhcp-options',
                'id': dhcp['DhcpOptionsId'],
                'arn': f"arn:aws:ec2:{region}:{account_id}:dhcp-options/{dhcp['DhcpOptionsId']}",
                'name': get_tag_value(tags, 'Name') or dhcp['DhcpOptionsId'],
                'region': region,
                'is_default': dhcp['DhcpOptionsId'] in default_dhcp_ids,
                'details': {
                    'configurations': {cfg['Key']: cfg.get('Values', []) for cfg in dhcp.get('DhcpConfigurations', [])},
                },
                'tags': tags_to_dict(tags)
            })
    except Exception:
        pass

    # Network ACLs
    try:
        paginator = ec2.get_paginator('describe_network_acls')
        for page in paginator.paginate():
            for nacl in page.get('NetworkAcls', []):
                tags = nacl.get('Tags', [])
                resources.append({
                    'service': 'vpc',
                    'type': 'network-acl',
                    'id': nacl['NetworkAclId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:network-acl/{nacl['NetworkAclId']}",
                    'name': get_tag_value(tags, 'Name') or nacl['NetworkAclId'],
                    'region': region,
                    'is_default': nacl.get('IsDefault', False),
                    'details': {
                        'vpc_id': nacl.get('VpcId'),
                        'is_default': nacl.get('IsDefault'),
                        'entries_count': len(nacl.get('Entries', [])),
                        'associations_count': len(nacl.get('Associations', [])),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    return resources
