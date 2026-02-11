"""
EC2 resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

from aws_inventory.collector import tags_to_dict, get_tag_value


def collect_ec2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect EC2 resources: instances, volumes, snapshots, AMIs, security groups,
    key pairs, elastic IPs, network interfaces, placement groups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ec2 = session.client('ec2', region_name=region)

    # EC2 Instances
    try:
        paginator = ec2.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    tags = instance.get('Tags', [])
                    resources.append({
                        'service': 'ec2',
                        'type': 'instance',
                        'id': instance['InstanceId'],
                        'arn': f"arn:aws:ec2:{region}:{account_id}:instance/{instance['InstanceId']}",
                        'name': get_tag_value(tags, 'Name') or instance['InstanceId'],
                        'region': region,
                        'details': {
                            'instance_type': instance.get('InstanceType'),
                            'state': instance.get('State', {}).get('Name'),
                            'private_ip': instance.get('PrivateIpAddress'),
                            'public_ip': instance.get('PublicIpAddress'),
                            'vpc_id': instance.get('VpcId'),
                            'subnet_id': instance.get('SubnetId'),
                            'launch_time': str(instance.get('LaunchTime', '')),
                            'platform': instance.get('Platform', 'linux'),
                            'architecture': instance.get('Architecture'),
                        },
                        'tags': tags_to_dict(tags)
                    })
    except Exception:
        pass

    # EBS Volumes
    try:
        paginator = ec2.get_paginator('describe_volumes')
        for page in paginator.paginate():
            for volume in page.get('Volumes', []):
                tags = volume.get('Tags', [])
                resources.append({
                    'service': 'ec2',
                    'type': 'volume',
                    'id': volume['VolumeId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:volume/{volume['VolumeId']}",
                    'name': get_tag_value(tags, 'Name') or volume['VolumeId'],
                    'region': region,
                    'details': {
                        'size_gb': volume.get('Size'),
                        'volume_type': volume.get('VolumeType'),
                        'state': volume.get('State'),
                        'iops': volume.get('Iops'),
                        'encrypted': volume.get('Encrypted'),
                        'availability_zone': volume.get('AvailabilityZone'),
                        'attachments': [a.get('InstanceId') for a in volume.get('Attachments', [])],
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # EBS Snapshots (owned by this account)
    try:
        paginator = ec2.get_paginator('describe_snapshots')
        for page in paginator.paginate(OwnerIds=[account_id]):
            for snapshot in page.get('Snapshots', []):
                tags = snapshot.get('Tags', [])
                resources.append({
                    'service': 'ec2',
                    'type': 'snapshot',
                    'id': snapshot['SnapshotId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:snapshot/{snapshot['SnapshotId']}",
                    'name': get_tag_value(tags, 'Name') or snapshot['SnapshotId'],
                    'region': region,
                    'details': {
                        'volume_id': snapshot.get('VolumeId'),
                        'size_gb': snapshot.get('VolumeSize'),
                        'state': snapshot.get('State'),
                        'encrypted': snapshot.get('Encrypted'),
                        'start_time': str(snapshot.get('StartTime', '')),
                        'description': snapshot.get('Description'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # AMIs (owned by this account)
    try:
        response = ec2.describe_images(Owners=[account_id])
        for image in response.get('Images', []):
            tags = image.get('Tags', [])
            resources.append({
                'service': 'ec2',
                'type': 'ami',
                'id': image['ImageId'],
                'arn': f"arn:aws:ec2:{region}:{account_id}:image/{image['ImageId']}",
                'name': image.get('Name') or get_tag_value(tags, 'Name') or image['ImageId'],
                'region': region,
                'details': {
                    'state': image.get('State'),
                    'architecture': image.get('Architecture'),
                    'platform': image.get('Platform', 'linux'),
                    'virtualization_type': image.get('VirtualizationType'),
                    'root_device_type': image.get('RootDeviceType'),
                    'public': image.get('Public'),
                    'creation_date': image.get('CreationDate'),
                },
                'tags': tags_to_dict(tags)
            })
    except Exception:
        pass

    # Security Groups
    try:
        paginator = ec2.get_paginator('describe_security_groups')
        for page in paginator.paginate():
            for sg in page.get('SecurityGroups', []):
                tags = sg.get('Tags', [])
                resources.append({
                    'service': 'ec2',
                    'type': 'security-group',
                    'id': sg['GroupId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:security-group/{sg['GroupId']}",
                    'name': sg.get('GroupName') or sg['GroupId'],
                    'region': region,
                    'is_default': sg.get('GroupName') == 'default',
                    'details': {
                        'vpc_id': sg.get('VpcId'),
                        'description': sg.get('Description'),
                        'ingress_rules': len(sg.get('IpPermissions', [])),
                        'egress_rules': len(sg.get('IpPermissionsEgress', [])),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # Key Pairs
    try:
        response = ec2.describe_key_pairs()
        for kp in response.get('KeyPairs', []):
            tags = kp.get('Tags', [])
            resources.append({
                'service': 'ec2',
                'type': 'key-pair',
                'id': kp.get('KeyPairId', kp['KeyName']),
                'arn': f"arn:aws:ec2:{region}:{account_id}:key-pair/{kp.get('KeyPairId', kp['KeyName'])}",
                'name': kp['KeyName'],
                'region': region,
                'details': {
                    'key_type': kp.get('KeyType'),
                    'fingerprint': kp.get('KeyFingerprint'),
                    'create_time': str(kp.get('CreateTime', '')),
                },
                'tags': tags_to_dict(tags)
            })
    except Exception:
        pass

    # Elastic IPs
    try:
        response = ec2.describe_addresses()
        for addr in response.get('Addresses', []):
            tags = addr.get('Tags', [])
            resources.append({
                'service': 'ec2',
                'type': 'elastic-ip',
                'id': addr.get('AllocationId', addr.get('PublicIp')),
                'arn': f"arn:aws:ec2:{region}:{account_id}:elastic-ip/{addr.get('AllocationId', addr.get('PublicIp'))}",
                'name': get_tag_value(tags, 'Name') or addr.get('PublicIp'),
                'region': region,
                'details': {
                    'public_ip': addr.get('PublicIp'),
                    'private_ip': addr.get('PrivateIpAddress'),
                    'instance_id': addr.get('InstanceId'),
                    'network_interface_id': addr.get('NetworkInterfaceId'),
                    'domain': addr.get('Domain'),
                },
                'tags': tags_to_dict(tags)
            })
    except Exception:
        pass

    # Network Interfaces
    try:
        paginator = ec2.get_paginator('describe_network_interfaces')
        for page in paginator.paginate():
            for eni in page.get('NetworkInterfaces', []):
                tags = eni.get('TagSet', [])
                resources.append({
                    'service': 'ec2',
                    'type': 'network-interface',
                    'id': eni['NetworkInterfaceId'],
                    'arn': f"arn:aws:ec2:{region}:{account_id}:network-interface/{eni['NetworkInterfaceId']}",
                    'name': get_tag_value(tags, 'Name') or eni['NetworkInterfaceId'],
                    'region': region,
                    'details': {
                        'vpc_id': eni.get('VpcId'),
                        'subnet_id': eni.get('SubnetId'),
                        'private_ip': eni.get('PrivateIpAddress'),
                        'status': eni.get('Status'),
                        'interface_type': eni.get('InterfaceType'),
                        'attachment_instance': eni.get('Attachment', {}).get('InstanceId'),
                    },
                    'tags': tags_to_dict(tags)
                })
    except Exception:
        pass

    # Placement Groups
    try:
        response = ec2.describe_placement_groups()
        for pg in response.get('PlacementGroups', []):
            tags = pg.get('Tags', [])
            resources.append({
                'service': 'ec2',
                'type': 'placement-group',
                'id': pg.get('GroupId', pg['GroupName']),
                'arn': f"arn:aws:ec2:{region}:{account_id}:placement-group/{pg['GroupName']}",
                'name': pg['GroupName'],
                'region': region,
                'details': {
                    'state': pg.get('State'),
                    'strategy': pg.get('Strategy'),
                    'partition_count': pg.get('PartitionCount'),
                },
                'tags': tags_to_dict(tags)
            })
    except Exception:
        pass

    return resources
