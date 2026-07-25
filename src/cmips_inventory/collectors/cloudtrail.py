"""
CloudTrail resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_cloudtrail_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect CloudTrail resources: trails, event data stores.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    cloudtrail = session.client('cloudtrail', region_name=region)

    # CloudTrail Trails
    try:
        response = cloudtrail.describe_trails()
        for trail in response.get('trailList', []):
            trail_name = trail['Name']
            trail_arn = trail['TrailARN']

            # Only process trails in this region (home region)
            home_region = trail.get('HomeRegion', region)
            if home_region != region:
                continue

            # Get tags
            tags = {}
            try:
                tag_response = cloudtrail.list_tags(ResourceIdList=[trail_arn])
                for resource_tag in tag_response.get('ResourceTagList', []):
                    for tag in resource_tag.get('TagsList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
            except Exception:
                pass

            # Get trail status
            is_logging = False
            try:
                status_response = cloudtrail.get_trail_status(Name=trail_name)
                is_logging = status_response.get('IsLogging', False)
            except Exception:
                pass

            resources.append({
                'service': 'cloudtrail',
                'type': 'trail',
                'id': trail_name,
                'arn': trail_arn,
                'name': trail_name,
                'region': region,
                'details': {
                    's3_bucket_name': trail.get('S3BucketName'),
                    's3_key_prefix': trail.get('S3KeyPrefix'),
                    'sns_topic_arn': trail.get('SnsTopicARN'),
                    'include_global_service_events': trail.get('IncludeGlobalServiceEvents'),
                    'is_multi_region_trail': trail.get('IsMultiRegionTrail'),
                    'is_organization_trail': trail.get('IsOrganizationTrail'),
                    'log_file_validation_enabled': trail.get('LogFileValidationEnabled'),
                    'cloud_watch_logs_log_group_arn': trail.get('CloudWatchLogsLogGroupArn'),
                    'kms_key_id': trail.get('KMSKeyId'),
                    'has_custom_event_selectors': trail.get('HasCustomEventSelectors'),
                    'has_insight_selectors': trail.get('HasInsightSelectors'),
                    'is_logging': is_logging,
                },
                'tags': tags
            })
    except Exception:
        pass

    # Event Data Stores (CloudTrail Lake)
    try:
        paginator = cloudtrail.get_paginator('list_event_data_stores')
        for page in paginator.paginate():
            for eds in page.get('EventDataStores', []):
                eds_arn = eds['EventDataStoreArn']
                eds_name = eds.get('Name', eds_arn.split('/')[-1])

                try:
                    # Get details
                    eds_response = cloudtrail.get_event_data_store(EventDataStore=eds_arn)

                    # Get tags
                    tags = {}
                    try:
                        tag_response = cloudtrail.list_tags(ResourceIdList=[eds_arn])
                        for resource_tag in tag_response.get('ResourceTagList', []):
                            for tag in resource_tag.get('TagsList', []):
                                tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'cloudtrail',
                        'type': 'event-data-store',
                        'id': eds_arn.split('/')[-1],
                        'arn': eds_arn,
                        'name': eds_name,
                        'region': region,
                        'details': {
                            'status': eds_response.get('Status'),
                            'retention_period': eds_response.get('RetentionPeriod'),
                            'termination_protection_enabled': eds_response.get('TerminationProtectionEnabled'),
                            'multi_region_enabled': eds_response.get('MultiRegionEnabled'),
                            'organization_enabled': eds_response.get('OrganizationEnabled'),
                            'kms_key_id': eds_response.get('KmsKeyId'),
                            'created_timestamp': str(eds_response.get('CreatedTimestamp', '')),
                            'updated_timestamp': str(eds_response.get('UpdatedTimestamp', '')),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
