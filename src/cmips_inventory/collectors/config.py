"""
AWS Config resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_config_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Config resources: configuration recorders, delivery channels, rules, aggregators.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    config = session.client('config', region_name=region)

    # Configuration Recorders
    try:
        response = config.describe_configuration_recorders()
        for recorder in response.get('ConfigurationRecorders', []):
            recorder_name = recorder['name']

            # Get recorder status
            status = 'unknown'
            try:
                status_response = config.describe_configuration_recorder_status(
                    ConfigurationRecorderNames=[recorder_name]
                )
                statuses = status_response.get('ConfigurationRecordersStatus', [])
                if statuses:
                    status = 'recording' if statuses[0].get('recording') else 'stopped'
            except Exception:
                pass

            resources.append({
                'service': 'config',
                'type': 'configuration-recorder',
                'id': recorder_name,
                'arn': f"arn:aws:config:{region}:{account_id}:config-recorder/{recorder_name}",
                'name': recorder_name,
                'region': region,
                'details': {
                    'role_arn': recorder.get('roleARN'),
                    'recording_group': recorder.get('recordingGroup'),
                    'status': status,
                },
                'tags': {}
            })
    except Exception:
        pass

    # Delivery Channels
    try:
        response = config.describe_delivery_channels()
        for channel in response.get('DeliveryChannels', []):
            channel_name = channel['name']

            resources.append({
                'service': 'config',
                'type': 'delivery-channel',
                'id': channel_name,
                'arn': f"arn:aws:config:{region}:{account_id}:delivery-channel/{channel_name}",
                'name': channel_name,
                'region': region,
                'details': {
                    's3_bucket_name': channel.get('s3BucketName'),
                    's3_key_prefix': channel.get('s3KeyPrefix'),
                    's3_kms_key_arn': channel.get('s3KmsKeyArn'),
                    'sns_topic_arn': channel.get('snsTopicARN'),
                    'config_snapshot_delivery_properties': channel.get('configSnapshotDeliveryProperties'),
                },
                'tags': {}
            })
    except Exception:
        pass

    # Config Rules
    try:
        paginator = config.get_paginator('describe_config_rules')
        for page in paginator.paginate():
            for rule in page.get('ConfigRules', []):
                rule_name = rule['ConfigRuleName']
                rule_arn = rule['ConfigRuleArn']

                # Get tags
                tags = {}
                try:
                    tag_response = config.list_tags_for_resource(ResourceArn=rule_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'config',
                    'type': 'config-rule',
                    'id': rule_name,
                    'arn': rule_arn,
                    'name': rule_name,
                    'region': region,
                    'details': {
                        'config_rule_state': rule.get('ConfigRuleState'),
                        'description': rule.get('Description'),
                        'scope': rule.get('Scope'),
                        'source': rule.get('Source', {}).get('Owner'),
                        'source_identifier': rule.get('Source', {}).get('SourceIdentifier'),
                        'maximum_execution_frequency': rule.get('MaximumExecutionFrequency'),
                        'created_by': rule.get('CreatedBy'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Configuration Aggregators
    try:
        paginator = config.get_paginator('describe_configuration_aggregators')
        for page in paginator.paginate():
            for aggregator in page.get('ConfigurationAggregators', []):
                agg_name = aggregator['ConfigurationAggregatorName']
                agg_arn = aggregator['ConfigurationAggregatorArn']

                # Get tags
                tags = {}
                try:
                    tag_response = config.list_tags_for_resource(ResourceArn=agg_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'config',
                    'type': 'configuration-aggregator',
                    'id': agg_name,
                    'arn': agg_arn,
                    'name': agg_name,
                    'region': region,
                    'details': {
                        'account_aggregation_sources': aggregator.get('AccountAggregationSources'),
                        'organization_aggregation_source': aggregator.get('OrganizationAggregationSource'),
                        'creation_time': str(aggregator.get('CreationTime', '')),
                        'last_updated_time': str(aggregator.get('LastUpdatedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Conformance Packs
    try:
        paginator = config.get_paginator('describe_conformance_packs')
        for page in paginator.paginate():
            for pack in page.get('ConformancePackDetails', []):
                pack_name = pack['ConformancePackName']
                pack_arn = pack['ConformancePackArn']

                resources.append({
                    'service': 'config',
                    'type': 'conformance-pack',
                    'id': pack_name,
                    'arn': pack_arn,
                    'name': pack_name,
                    'region': region,
                    'details': {
                        'delivery_s3_bucket': pack.get('DeliveryS3Bucket'),
                        'delivery_s3_key_prefix': pack.get('DeliveryS3KeyPrefix'),
                        'created_by': pack.get('CreatedBy'),
                        'last_update_requested_time': str(pack.get('LastUpdateRequestedTime', '')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
