"""
GuardDuty resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_guardduty_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect GuardDuty resources: detectors, IP sets, threat intel sets, filters.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    guardduty = session.client('guardduty', region_name=region)

    # Detectors
    detector_ids = []
    try:
        paginator = guardduty.get_paginator('list_detectors')
        for page in paginator.paginate():
            detector_ids.extend(page.get('DetectorIds', []))
    except Exception:
        pass

    for detector_id in detector_ids:
        try:
            # Get detector details
            response = guardduty.get_detector(DetectorId=detector_id)

            # Get tags
            tags = response.get('Tags', {})

            resources.append({
                'service': 'guardduty',
                'type': 'detector',
                'id': detector_id,
                'arn': f"arn:aws:guardduty:{region}:{account_id}:detector/{detector_id}",
                'name': f"detector-{detector_id[:8]}",
                'region': region,
                'details': {
                    'status': response.get('Status'),
                    'service_role': response.get('ServiceRole'),
                    'created_at': str(response.get('CreatedAt', '')),
                    'updated_at': str(response.get('UpdatedAt', '')),
                    'finding_publishing_frequency': response.get('FindingPublishingFrequency'),
                    'data_sources': response.get('DataSources'),
                    'features': response.get('Features'),
                },
                'tags': tags
            })

            # IP Sets for this detector
            try:
                ipset_paginator = guardduty.get_paginator('list_ip_sets')
                for ipset_page in ipset_paginator.paginate(DetectorId=detector_id):
                    for ipset_id in ipset_page.get('IpSetIds', []):
                        try:
                            ipset_response = guardduty.get_ip_set(
                                DetectorId=detector_id,
                                IpSetId=ipset_id
                            )

                            ipset_tags = ipset_response.get('Tags', {})

                            resources.append({
                                'service': 'guardduty',
                                'type': 'ip-set',
                                'id': ipset_id,
                                'arn': f"arn:aws:guardduty:{region}:{account_id}:detector/{detector_id}/ipset/{ipset_id}",
                                'name': ipset_response.get('Name', ipset_id),
                                'region': region,
                                'details': {
                                    'detector_id': detector_id,
                                    'format': ipset_response.get('Format'),
                                    'location': ipset_response.get('Location'),
                                    'status': ipset_response.get('Status'),
                                },
                                'tags': ipset_tags
                            })
                        except Exception:
                            pass
            except Exception:
                pass

            # Threat Intel Sets for this detector
            try:
                ti_paginator = guardduty.get_paginator('list_threat_intel_sets')
                for ti_page in ti_paginator.paginate(DetectorId=detector_id):
                    for ti_id in ti_page.get('ThreatIntelSetIds', []):
                        try:
                            ti_response = guardduty.get_threat_intel_set(
                                DetectorId=detector_id,
                                ThreatIntelSetId=ti_id
                            )

                            ti_tags = ti_response.get('Tags', {})

                            resources.append({
                                'service': 'guardduty',
                                'type': 'threat-intel-set',
                                'id': ti_id,
                                'arn': f"arn:aws:guardduty:{region}:{account_id}:detector/{detector_id}/threatintelset/{ti_id}",
                                'name': ti_response.get('Name', ti_id),
                                'region': region,
                                'details': {
                                    'detector_id': detector_id,
                                    'format': ti_response.get('Format'),
                                    'location': ti_response.get('Location'),
                                    'status': ti_response.get('Status'),
                                },
                                'tags': ti_tags
                            })
                        except Exception:
                            pass
            except Exception:
                pass

            # Filters for this detector
            try:
                filter_paginator = guardduty.get_paginator('list_filters')
                for filter_page in filter_paginator.paginate(DetectorId=detector_id):
                    for filter_name in filter_page.get('FilterNames', []):
                        try:
                            filter_response = guardduty.get_filter(
                                DetectorId=detector_id,
                                FilterName=filter_name
                            )

                            filter_tags = filter_response.get('Tags', {})

                            resources.append({
                                'service': 'guardduty',
                                'type': 'filter',
                                'id': filter_name,
                                'arn': f"arn:aws:guardduty:{region}:{account_id}:detector/{detector_id}/filter/{filter_name}",
                                'name': filter_name,
                                'region': region,
                                'details': {
                                    'detector_id': detector_id,
                                    'description': filter_response.get('Description'),
                                    'rank': filter_response.get('Rank'),
                                    'action': filter_response.get('Action'),
                                },
                                'tags': filter_tags
                            })
                        except Exception:
                            pass
            except Exception:
                pass

        except Exception:
            pass

    return resources
