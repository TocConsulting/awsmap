"""
Direct Connect resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_directconnect_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Direct Connect resources: connections, virtual interfaces, gateways, LAGs.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    dx = session.client('directconnect', region_name=region)

    # Direct Connect Connections
    try:
        response = dx.describe_connections()
        for conn in response.get('connections', []):
            conn_id = conn['connectionId']

            # Get tags
            tags = {}
            try:
                tag_response = dx.describe_tags(resourceArns=[conn_id])
                for tag_res in tag_response.get('resourceTags', []):
                    for tag in tag_res.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
            except Exception:
                pass

            resources.append({
                'service': 'directconnect',
                'type': 'connection',
                'id': conn_id,
                'arn': f"arn:aws:directconnect:{region}:{account_id}:dxcon/{conn_id}",
                'name': conn.get('connectionName', conn_id),
                'region': region,
                'details': {
                    'connection_state': conn.get('connectionState'),
                    'location': conn.get('location'),
                    'bandwidth': conn.get('bandwidth'),
                    'vlan': conn.get('vlan'),
                    'partner_name': conn.get('partnerName'),
                    'loa_issue_time': str(conn.get('loaIssueTime', '')),
                    'lag_id': conn.get('lagId'),
                    'aws_device': conn.get('awsDevice'),
                    'aws_device_v2': conn.get('awsDeviceV2'),
                    'aws_logical_device_id': conn.get('awsLogicalDeviceId'),
                    'has_logical_redundancy': conn.get('hasLogicalRedundancy'),
                    'jumbo_frame_capable': conn.get('jumboFrameCapable'),
                    'port_encryption_status': conn.get('portEncryptionStatus'),
                    'mac_sec_capable': conn.get('macSecCapable'),
                    'encryption_mode': conn.get('encryptionMode'),
                    'provider_name': conn.get('providerName'),
                },
                'tags': tags
            })
    except Exception:
        pass

    # Direct Connect Virtual Interfaces
    try:
        response = dx.describe_virtual_interfaces()
        for vif in response.get('virtualInterfaces', []):
            vif_id = vif['virtualInterfaceId']

            # Get tags
            tags = {}
            try:
                tag_response = dx.describe_tags(resourceArns=[vif_id])
                for tag_res in tag_response.get('resourceTags', []):
                    for tag in tag_res.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
            except Exception:
                pass

            resources.append({
                'service': 'directconnect',
                'type': f"virtual-interface-{vif.get('virtualInterfaceType', 'private').lower()}",
                'id': vif_id,
                'arn': f"arn:aws:directconnect:{region}:{account_id}:dxvif/{vif_id}",
                'name': vif.get('virtualInterfaceName', vif_id),
                'region': region,
                'details': {
                    'virtual_interface_state': vif.get('virtualInterfaceState'),
                    'virtual_interface_type': vif.get('virtualInterfaceType'),
                    'connection_id': vif.get('connectionId'),
                    'vlan': vif.get('vlan'),
                    'asn': vif.get('asn'),
                    'amazon_side_asn': vif.get('amazonSideAsn'),
                    'auth_key': vif.get('authKey'),
                    'amazon_address': vif.get('amazonAddress'),
                    'customer_address': vif.get('customerAddress'),
                    'address_family': vif.get('addressFamily'),
                    'virtual_gateway_id': vif.get('virtualGatewayId'),
                    'direct_connect_gateway_id': vif.get('directConnectGatewayId'),
                    'route_filter_prefixes': vif.get('routeFilterPrefixes', []),
                    'bgp_peers': len(vif.get('bgpPeers', [])),
                    'mtu': vif.get('mtu'),
                    'jumbo_frame_capable': vif.get('jumboFrameCapable'),
                    'site_link_enabled': vif.get('siteLinkEnabled'),
                },
                'tags': tags
            })
    except Exception:
        pass

    # Direct Connect Gateways
    try:
        response = dx.describe_direct_connect_gateways()
        for gw in response.get('directConnectGateways', []):
            gw_id = gw['directConnectGatewayId']

            resources.append({
                'service': 'directconnect',
                'type': 'gateway',
                'id': gw_id,
                'arn': f"arn:aws:directconnect::{account_id}:dx-gateway/{gw_id}",
                'name': gw.get('directConnectGatewayName', gw_id),
                'region': 'global',
                'details': {
                    'state': gw.get('directConnectGatewayState'),
                    'amazon_side_asn': gw.get('amazonSideAsn'),
                    'owner_account': gw.get('ownerAccount'),
                    'state_change_error': gw.get('stateChangeError'),
                },
                'tags': {}
            })
    except Exception:
        pass

    # LAGs (Link Aggregation Groups)
    try:
        response = dx.describe_lags()
        for lag in response.get('lags', []):
            lag_id = lag['lagId']

            # Get tags
            tags = {}
            try:
                tag_response = dx.describe_tags(resourceArns=[lag_id])
                for tag_res in tag_response.get('resourceTags', []):
                    for tag in tag_res.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
            except Exception:
                pass

            resources.append({
                'service': 'directconnect',
                'type': 'lag',
                'id': lag_id,
                'arn': f"arn:aws:directconnect:{region}:{account_id}:dxlag/{lag_id}",
                'name': lag.get('lagName', lag_id),
                'region': region,
                'details': {
                    'lag_state': lag.get('lagState'),
                    'location': lag.get('location'),
                    'minimum_links': lag.get('minimumLinks'),
                    'number_of_connections': lag.get('numberOfConnections'),
                    'connections_bandwidth': lag.get('connectionsBandwidth'),
                    'aws_device': lag.get('awsDevice'),
                    'aws_device_v2': lag.get('awsDeviceV2'),
                    'aws_logical_device_id': lag.get('awsLogicalDeviceId'),
                    'has_logical_redundancy': lag.get('hasLogicalRedundancy'),
                    'jumbo_frame_capable': lag.get('jumboFrameCapable'),
                    'allows_hosted_connections': lag.get('allowsHostedConnections'),
                    'encryption_mode': lag.get('encryptionMode'),
                    'mac_sec_capable': lag.get('macSecCapable'),
                    'provider_name': lag.get('providerName'),
                },
                'tags': tags
            })
    except Exception:
        pass

    return resources
