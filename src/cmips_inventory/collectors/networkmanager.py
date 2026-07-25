"""
AWS Network Manager resource collector.

Note: Network Manager is a global service.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_networkmanager_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Network Manager resources: global networks, sites, devices, links, and connections.

    Note: Network Manager is a global service, called from us-west-2.

    Args:
        session: boto3.Session to use
        region: AWS region (ignored - global service)
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    nm = session.client('networkmanager', region_name='us-west-2')

    # Global Networks
    try:
        paginator = nm.get_paginator('describe_global_networks')
        for page in paginator.paginate():
            for network in page.get('GlobalNetworks', []):
                network_id = network['GlobalNetworkId']
                network_arn = network.get('GlobalNetworkArn', '')

                details = {
                    'description': network.get('Description'),
                    'state': network.get('State'),
                    'created_at': str(network.get('CreatedAt', '')),
                }

                tags = {t['Key']: t['Value'] for t in network.get('Tags', [])}

                resources.append({
                    'service': 'networkmanager',
                    'type': 'global-network',
                    'id': network_id,
                    'arn': network_arn,
                    'name': network.get('Description', network_id),
                    'region': 'global',
                    'details': details,
                    'tags': tags
                })

                # Sites for this global network
                try:
                    site_paginator = nm.get_paginator('get_sites')
                    for site_page in site_paginator.paginate(GlobalNetworkId=network_id):
                        for site in site_page.get('Sites', []):
                            site_id = site['SiteId']
                            site_arn = site.get('SiteArn', '')

                            site_details = {
                                'global_network_id': network_id,
                                'description': site.get('Description'),
                                'state': site.get('State'),
                                'created_at': str(site.get('CreatedAt', '')),
                            }

                            location = site.get('Location', {})
                            if location:
                                site_details['address'] = location.get('Address')
                                site_details['latitude'] = location.get('Latitude')
                                site_details['longitude'] = location.get('Longitude')

                            site_tags = {t['Key']: t['Value'] for t in site.get('Tags', [])}

                            resources.append({
                                'service': 'networkmanager',
                                'type': 'site',
                                'id': site_id,
                                'arn': site_arn,
                                'name': site.get('Description', site_id),
                                'region': 'global',
                                'details': site_details,
                                'tags': site_tags
                            })
                except Exception:
                    pass

                # Devices for this global network
                try:
                    device_paginator = nm.get_paginator('get_devices')
                    for device_page in device_paginator.paginate(GlobalNetworkId=network_id):
                        for device in device_page.get('Devices', []):
                            device_id = device['DeviceId']
                            device_arn = device.get('DeviceArn', '')

                            device_details = {
                                'global_network_id': network_id,
                                'site_id': device.get('SiteId'),
                                'description': device.get('Description'),
                                'type': device.get('Type'),
                                'vendor': device.get('Vendor'),
                                'model': device.get('Model'),
                                'serial_number': device.get('SerialNumber'),
                                'state': device.get('State'),
                                'created_at': str(device.get('CreatedAt', '')),
                            }

                            device_tags = {t['Key']: t['Value'] for t in device.get('Tags', [])}

                            resources.append({
                                'service': 'networkmanager',
                                'type': 'device',
                                'id': device_id,
                                'arn': device_arn,
                                'name': device.get('Description', device_id),
                                'region': 'global',
                                'details': device_details,
                                'tags': device_tags
                            })
                except Exception:
                    pass

                # Links for this global network
                try:
                    link_paginator = nm.get_paginator('get_links')
                    for link_page in link_paginator.paginate(GlobalNetworkId=network_id):
                        for link in link_page.get('Links', []):
                            link_id = link['LinkId']
                            link_arn = link.get('LinkArn', '')

                            link_details = {
                                'global_network_id': network_id,
                                'site_id': link.get('SiteId'),
                                'description': link.get('Description'),
                                'type': link.get('Type'),
                                'provider': link.get('Provider'),
                                'state': link.get('State'),
                                'created_at': str(link.get('CreatedAt', '')),
                            }

                            bandwidth = link.get('Bandwidth', {})
                            if bandwidth:
                                link_details['upload_speed_mbps'] = bandwidth.get('UploadSpeed')
                                link_details['download_speed_mbps'] = bandwidth.get('DownloadSpeed')

                            link_tags = {t['Key']: t['Value'] for t in link.get('Tags', [])}

                            resources.append({
                                'service': 'networkmanager',
                                'type': 'link',
                                'id': link_id,
                                'arn': link_arn,
                                'name': link.get('Description', link_id),
                                'region': 'global',
                                'details': link_details,
                                'tags': link_tags
                            })
                except Exception:
                    pass

                # Connections for this global network
                try:
                    conn_paginator = nm.get_paginator('get_connections')
                    for conn_page in conn_paginator.paginate(GlobalNetworkId=network_id):
                        for conn in conn_page.get('Connections', []):
                            conn_id = conn['ConnectionId']
                            conn_arn = conn.get('ConnectionArn', '')

                            conn_details = {
                                'global_network_id': network_id,
                                'device_id': conn.get('DeviceId'),
                                'connected_device_id': conn.get('ConnectedDeviceId'),
                                'link_id': conn.get('LinkId'),
                                'connected_link_id': conn.get('ConnectedLinkId'),
                                'description': conn.get('Description'),
                                'state': conn.get('State'),
                                'created_at': str(conn.get('CreatedAt', '')),
                            }

                            conn_tags = {t['Key']: t['Value'] for t in conn.get('Tags', [])}

                            resources.append({
                                'service': 'networkmanager',
                                'type': 'connection',
                                'id': conn_id,
                                'arn': conn_arn,
                                'name': conn.get('Description', conn_id),
                                'region': 'global',
                                'details': conn_details,
                                'tags': conn_tags
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
