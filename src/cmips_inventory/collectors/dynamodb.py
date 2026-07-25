"""
DynamoDB resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_dynamodb_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect DynamoDB resources: tables, global tables, backups.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    dynamodb = session.client('dynamodb', region_name=region)

    # DynamoDB Tables
    table_names = []
    try:
        paginator = dynamodb.get_paginator('list_tables')
        for page in paginator.paginate():
            table_names.extend(page.get('TableNames', []))
    except Exception:
        pass

    for table_name in table_names:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            table = response.get('Table', {})

            # Get tags
            tags = {}
            try:
                tag_response = dynamodb.list_tags_of_resource(
                    ResourceArn=table['TableArn']
                )
                for tag in tag_response.get('Tags', []):
                    tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            # Billing mode
            billing_mode = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')

            resources.append({
                'service': 'dynamodb',
                'type': 'table',
                'id': table_name,
                'arn': table['TableArn'],
                'name': table_name,
                'region': region,
                'details': {
                    'status': table.get('TableStatus'),
                    'billing_mode': billing_mode,
                    'item_count': table.get('ItemCount'),
                    'size_bytes': table.get('TableSizeBytes'),
                    'read_capacity': table.get('ProvisionedThroughput', {}).get('ReadCapacityUnits'),
                    'write_capacity': table.get('ProvisionedThroughput', {}).get('WriteCapacityUnits'),
                    'gsi_count': len(table.get('GlobalSecondaryIndexes', [])),
                    'lsi_count': len(table.get('LocalSecondaryIndexes', [])),
                    'stream_enabled': table.get('StreamSpecification', {}).get('StreamEnabled', False),
                    'table_class': table.get('TableClassSummary', {}).get('TableClass'),
                    'deletion_protection': table.get('DeletionProtectionEnabled'),
                    'key_schema': [
                        {k.get('AttributeName'): k.get('KeyType')}
                        for k in table.get('KeySchema', [])
                    ],
                },
                'tags': tags
            })
        except Exception:
            pass

    # DynamoDB Global Tables
    try:
        response = dynamodb.list_global_tables()
        for gt in response.get('GlobalTables', []):
            table_name = gt['GlobalTableName']
            resources.append({
                'service': 'dynamodb',
                'type': 'global-table',
                'id': table_name,
                'arn': f"arn:aws:dynamodb::{account_id}:global-table/{table_name}",
                'name': table_name,
                'region': region,
                'details': {
                    'replication_regions': [r.get('RegionName') for r in gt.get('ReplicationGroup', [])],
                },
                'tags': {}
            })
    except Exception:
        pass

    # DynamoDB Backups
    try:
        paginator = dynamodb.get_paginator('list_backups')
        for page in paginator.paginate():
            for backup in page.get('BackupSummaries', []):
                backup_name = backup['BackupName']
                resources.append({
                    'service': 'dynamodb',
                    'type': 'backup',
                    'id': backup['BackupArn'].split('/')[-1],
                    'arn': backup['BackupArn'],
                    'name': backup_name,
                    'region': region,
                    'details': {
                        'table_name': backup.get('TableName'),
                        'table_arn': backup.get('TableArn'),
                        'backup_status': backup.get('BackupStatus'),
                        'backup_type': backup.get('BackupType'),
                        'backup_size_bytes': backup.get('BackupSizeBytes'),
                        'backup_creation_datetime': str(backup.get('BackupCreationDateTime', '')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # DynamoDB Streams
    try:
        streams_client = session.client('dynamodbstreams', region_name=region)
        response = streams_client.list_streams()
        for stream in response.get('Streams', []):
            stream_arn = stream['StreamArn']
            table_name = stream.get('TableName', '')
            stream_label = stream.get('StreamLabel', '')

            # Get stream details
            stream_status = None
            stream_view_type = None
            shard_count = 0
            try:
                desc_response = streams_client.describe_stream(StreamArn=stream_arn)
                stream_desc = desc_response.get('StreamDescription', {})
                stream_status = stream_desc.get('StreamStatus')
                stream_view_type = stream_desc.get('StreamViewType')
                shard_count = len(stream_desc.get('Shards', []))
            except Exception:
                pass

            resources.append({
                'service': 'dynamodb',
                'type': 'stream',
                'id': stream_label,
                'arn': stream_arn,
                'name': f"{table_name}-stream",
                'region': region,
                'details': {
                    'table_name': table_name,
                    'stream_label': stream_label,
                    'stream_status': stream_status,
                    'stream_view_type': stream_view_type,
                    'shard_count': shard_count,
                },
                'tags': {}
            })
    except Exception:
        pass

    return resources
