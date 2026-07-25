"""
AWS Comprehend resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# Comprehend supported regions (from https://docs.aws.amazon.com/general/latest/gr/comprehend.html)
COMPREHEND_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2',
}


def collect_comprehend_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Comprehend resources: entity recognizers, document classifiers, endpoints, and flywheels.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in COMPREHEND_REGIONS:
        return []

    resources = []
    comprehend = session.client('comprehend', region_name=region)

    # Entity Recognizers
    try:
        paginator = comprehend.get_paginator('list_entity_recognizers')
        for page in paginator.paginate():
            for recognizer in page.get('EntityRecognizerPropertiesList', []):
                recognizer_arn = recognizer['EntityRecognizerArn']
                recognizer_name = recognizer_arn.split('/')[-1] if '/' in recognizer_arn else recognizer_arn

                details = {
                    'language_code': recognizer.get('LanguageCode'),
                    'status': recognizer.get('Status'),
                    'submit_time': str(recognizer.get('SubmitTime', '')),
                    'end_time': str(recognizer.get('EndTime', '')),
                    'training_start_time': str(recognizer.get('TrainingStartTime', '')),
                    'training_end_time': str(recognizer.get('TrainingEndTime', '')),
                    'data_access_role_arn': recognizer.get('DataAccessRoleArn'),
                    'volume_kms_key_id': recognizer.get('VolumeKmsKeyId'),
                    'model_kms_key_id': recognizer.get('ModelKmsKeyId'),
                    'version_name': recognizer.get('VersionName'),
                }

                resources.append({
                    'service': 'comprehend',
                    'type': 'entity-recognizer',
                    'id': recognizer_name,
                    'arn': recognizer_arn,
                    'name': recognizer_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Document Classifiers
    try:
        paginator = comprehend.get_paginator('list_document_classifiers')
        for page in paginator.paginate():
            for classifier in page.get('DocumentClassifierPropertiesList', []):
                classifier_arn = classifier['DocumentClassifierArn']
                classifier_name = classifier_arn.split('/')[-1] if '/' in classifier_arn else classifier_arn

                details = {
                    'language_code': classifier.get('LanguageCode'),
                    'status': classifier.get('Status'),
                    'submit_time': str(classifier.get('SubmitTime', '')),
                    'end_time': str(classifier.get('EndTime', '')),
                    'training_start_time': str(classifier.get('TrainingStartTime', '')),
                    'training_end_time': str(classifier.get('TrainingEndTime', '')),
                    'data_access_role_arn': classifier.get('DataAccessRoleArn'),
                    'volume_kms_key_id': classifier.get('VolumeKmsKeyId'),
                    'model_kms_key_id': classifier.get('ModelKmsKeyId'),
                    'version_name': classifier.get('VersionName'),
                    'mode': classifier.get('Mode'),
                }

                resources.append({
                    'service': 'comprehend',
                    'type': 'document-classifier',
                    'id': classifier_name,
                    'arn': classifier_arn,
                    'name': classifier_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Endpoints
    try:
        paginator = comprehend.get_paginator('list_endpoints')
        for page in paginator.paginate():
            for endpoint in page.get('EndpointPropertiesList', []):
                endpoint_arn = endpoint['EndpointArn']
                endpoint_name = endpoint_arn.split('/')[-1] if '/' in endpoint_arn else endpoint_arn

                details = {
                    'status': endpoint.get('Status'),
                    'model_arn': endpoint.get('ModelArn'),
                    'desired_model_arn': endpoint.get('DesiredModelArn'),
                    'desired_inference_units': endpoint.get('DesiredInferenceUnits'),
                    'current_inference_units': endpoint.get('CurrentInferenceUnits'),
                    'creation_time': str(endpoint.get('CreationTime', '')),
                    'last_modified_time': str(endpoint.get('LastModifiedTime', '')),
                    'data_access_role_arn': endpoint.get('DataAccessRoleArn'),
                    'desired_data_access_role_arn': endpoint.get('DesiredDataAccessRoleArn'),
                    'flywheel_arn': endpoint.get('FlywheelArn'),
                }

                resources.append({
                    'service': 'comprehend',
                    'type': 'endpoint',
                    'id': endpoint_name,
                    'arn': endpoint_arn,
                    'name': endpoint_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Flywheels
    try:
        paginator = comprehend.get_paginator('list_flywheels')
        for page in paginator.paginate():
            for flywheel in page.get('FlywheelSummaryList', []):
                flywheel_arn = flywheel['FlywheelArn']
                flywheel_name = flywheel_arn.split('/')[-1] if '/' in flywheel_arn else flywheel_arn

                details = {
                    'active_model_arn': flywheel.get('ActiveModelArn'),
                    'data_lake_s3_uri': flywheel.get('DataLakeS3Uri'),
                    'status': flywheel.get('Status'),
                    'model_type': flywheel.get('ModelType'),
                    'creation_time': str(flywheel.get('CreationTime', '')),
                    'last_modified_time': str(flywheel.get('LastModifiedTime', '')),
                    'latest_flywheel_iteration': flywheel.get('LatestFlywheelIteration'),
                }

                resources.append({
                    'service': 'comprehend',
                    'type': 'flywheel',
                    'id': flywheel_name,
                    'arn': flywheel_arn,
                    'name': flywheel_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
