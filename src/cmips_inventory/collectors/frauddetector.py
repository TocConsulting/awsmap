"""
Amazon Fraud Detector resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


# Fraud Detector supported regions
FRAUDDETECTOR_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'eu-west-1',
    'ap-southeast-1', 'ap-southeast-2',
}


def collect_frauddetector_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Amazon Fraud Detector resources: detectors, models, event types.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in FRAUDDETECTOR_REGIONS:
        return []

    resources = []
    frauddetector = session.client('frauddetector', region_name=region)

    # Detectors
    try:
        response = frauddetector.get_detectors()
        for detector in response.get('detectors', []):
            detector_id = detector.get('detectorId', '')
            detector_arn = detector.get('arn', f"arn:aws:frauddetector:{region}:{account_id}:detector/{detector_id}")

            details = {
                'description': detector.get('description'),
                'event_type_name': detector.get('eventTypeName'),
                'last_updated_time': detector.get('lastUpdatedTime'),
                'created_time': detector.get('createdTime'),
            }

            resources.append({
                'service': 'frauddetector',
                'type': 'detector',
                'id': detector_id,
                'arn': detector_arn,
                'name': detector_id,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Models
    try:
        response = frauddetector.get_models()
        for model in response.get('models', []):
            model_id = model.get('modelId', '')
            model_arn = model.get('arn', f"arn:aws:frauddetector:{region}:{account_id}:model/{model_id}")

            details = {
                'model_type': model.get('modelType'),
                'description': model.get('description'),
                'event_type_name': model.get('eventTypeName'),
                'created_time': model.get('createdTime'),
                'last_updated_time': model.get('lastUpdatedTime'),
            }

            resources.append({
                'service': 'frauddetector',
                'type': 'model',
                'id': model_id,
                'arn': model_arn,
                'name': model_id,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    # Event Types
    try:
        response = frauddetector.get_event_types()
        for event_type in response.get('eventTypes', []):
            event_type_name = event_type.get('name', '')
            event_type_arn = event_type.get('arn', f"arn:aws:frauddetector:{region}:{account_id}:event-type/{event_type_name}")

            details = {
                'description': event_type.get('description'),
                'event_variables': event_type.get('eventVariables'),
                'labels': event_type.get('labels'),
                'entity_types': event_type.get('entityTypes'),
                'created_time': event_type.get('createdTime'),
                'last_updated_time': event_type.get('lastUpdatedTime'),
            }

            resources.append({
                'service': 'frauddetector',
                'type': 'event-type',
                'id': event_type_name,
                'arn': event_type_arn,
                'name': event_type_name,
                'region': region,
                'details': details,
                'tags': {}
            })
    except Exception:
        pass

    return resources
