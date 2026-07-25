"""
Kinesis Data Firehose resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_firehose_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Kinesis Data Firehose delivery streams.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    firehose = session.client('firehose', region_name=region)

    try:
        # List all delivery streams
        stream_names = []
        response = firehose.list_delivery_streams()
        stream_names.extend(response.get('DeliveryStreamNames', []))

        while response.get('HasMoreDeliveryStreams'):
            response = firehose.list_delivery_streams(
                ExclusiveStartDeliveryStreamName=stream_names[-1]
            )
            stream_names.extend(response.get('DeliveryStreamNames', []))

        # Describe each stream
        for stream_name in stream_names:
            try:
                stream_response = firehose.describe_delivery_stream(
                    DeliveryStreamName=stream_name
                )
                stream_desc = stream_response.get('DeliveryStreamDescription', {})

                stream_arn = stream_desc.get('DeliveryStreamARN')

                # Get tags
                tags = {}
                try:
                    tag_response = firehose.list_tags_for_delivery_stream(
                        DeliveryStreamName=stream_name
                    )
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                # Determine destination type
                destinations = stream_desc.get('Destinations', [])
                destination_types = []
                for dest in destinations:
                    if dest.get('S3DestinationDescription'):
                        destination_types.append('S3')
                    if dest.get('RedshiftDestinationDescription'):
                        destination_types.append('Redshift')
                    if dest.get('ElasticsearchDestinationDescription'):
                        destination_types.append('Elasticsearch')
                    if dest.get('HttpEndpointDestinationDescription'):
                        destination_types.append('HTTP')
                    if dest.get('SplunkDestinationDescription'):
                        destination_types.append('Splunk')
                    if dest.get('AmazonOpenSearchServerlessDestinationDescription'):
                        destination_types.append('OpenSearchServerless')
                    if dest.get('AmazonopensearchserviceDestinationDescription'):
                        destination_types.append('OpenSearch')

                resources.append({
                    'service': 'firehose',
                    'type': 'delivery-stream',
                    'id': stream_name,
                    'arn': stream_arn,
                    'name': stream_name,
                    'region': region,
                    'details': {
                        'status': stream_desc.get('DeliveryStreamStatus'),
                        'delivery_stream_type': stream_desc.get('DeliveryStreamType'),
                        'version_id': stream_desc.get('VersionId'),
                        'destination_types': destination_types,
                        'source_kinesis_stream_arn': stream_desc.get('Source', {}).get('KinesisStreamSourceDescription', {}).get('KinesisStreamARN'),
                        'create_timestamp': str(stream_desc.get('CreateTimestamp', '')),
                        'last_update_timestamp': str(stream_desc.get('LastUpdateTimestamp', '')),
                    },
                    'tags': tags
                })
            except Exception:
                pass
    except Exception:
        pass

    return resources
