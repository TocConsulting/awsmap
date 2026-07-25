"""
Amazon Keyspaces resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_keyspaces_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Amazon Keyspaces resources: keyspaces, tables.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    keyspaces = session.client('keyspaces', region_name=region)

    # Keyspaces (skip AWS system keyspaces: system, system_schema, system_schema_mcs, system_multiregion_info)
    keyspace_list = []
    try:
        paginator = keyspaces.get_paginator('list_keyspaces')
        for page in paginator.paginate():
            for ks in page.get('keyspaces', []):
                ks_name = ks['keyspaceName']

                # Skip AWS system keyspaces
                if ks_name.startswith('system'):
                    continue

                keyspace_list.append(ks)
                ks_arn = ks['resourceArn']

                # Get tags
                tags = {}
                try:
                    tag_response = keyspaces.list_tags_for_resource(resourceArn=ks_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'keyspaces',
                    'type': 'keyspace',
                    'id': ks_name,
                    'arn': ks_arn,
                    'name': ks_name,
                    'region': region,
                    'details': {
                        'replication_strategy': ks.get('replicationStrategy'),
                        'replication_regions': ks.get('replicationRegions', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Tables (for each user keyspace)
    for ks in keyspace_list:
        ks_name = ks['keyspaceName']
        try:
            table_paginator = keyspaces.get_paginator('list_tables')
            for table_page in table_paginator.paginate(keyspaceName=ks_name):
                for table in table_page.get('tables', []):
                    table_name = table['tableName']
                    table_arn = table['resourceArn']

                    try:
                        # Get table details
                        table_response = keyspaces.get_table(
                            keyspaceName=ks_name,
                            tableName=table_name
                        )

                        # Get tags
                        tags = {}
                        try:
                            tag_response = keyspaces.list_tags_for_resource(resourceArn=table_arn)
                            for tag in tag_response.get('tags', []):
                                tags[tag.get('key', '')] = tag.get('value', '')
                        except Exception:
                            pass

                        resources.append({
                            'service': 'keyspaces',
                            'type': 'table',
                            'id': f"{ks_name}/{table_name}",
                            'arn': table_arn,
                            'name': table_name,
                            'region': region,
                            'details': {
                                'keyspace_name': ks_name,
                                'status': table_response.get('status'),
                                'default_time_to_live': table_response.get('defaultTimeToLive'),
                                'creation_timestamp': str(table_response.get('creationTimestamp', '')),
                                'capacity_specification_mode': table_response.get('capacitySpecification', {}).get('throughputMode'),
                                'read_capacity_units': table_response.get('capacitySpecification', {}).get('readCapacityUnits'),
                                'write_capacity_units': table_response.get('capacitySpecification', {}).get('writeCapacityUnits'),
                                'encryption_type': table_response.get('encryptionSpecification', {}).get('type'),
                                'point_in_time_recovery_enabled': table_response.get('pointInTimeRecovery', {}).get('status') == 'ENABLED',
                                'ttl_status': table_response.get('ttl', {}).get('status'),
                            },
                            'tags': tags
                        })
                    except Exception:
                        pass
        except Exception:
            pass

    return resources
