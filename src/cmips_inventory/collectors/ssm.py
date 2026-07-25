"""
Systems Manager resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_ssm_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect SSM resources: parameters, documents, maintenance windows, patch baselines.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    ssm = session.client('ssm', region_name=region)

    # SSM Parameters
    try:
        paginator = ssm.get_paginator('describe_parameters')
        for page in paginator.paginate():
            for param in page.get('Parameters', []):
                param_name = param['Name']

                # Get tags
                tags = {}
                try:
                    tag_response = ssm.list_tags_for_resource(
                        ResourceType='Parameter',
                        ResourceId=param_name
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'ssm',
                    'type': 'parameter',
                    'id': param_name,
                    'arn': f"arn:aws:ssm:{region}:{account_id}:parameter{param_name if param_name.startswith('/') else '/' + param_name}",
                    'name': param_name,
                    'region': region,
                    'details': {
                        'type': param.get('Type'),
                        'key_id': param.get('KeyId'),
                        'version': param.get('Version'),
                        'tier': param.get('Tier'),
                        'policies': param.get('Policies', []),
                        'data_type': param.get('DataType'),
                        'last_modified_date': str(param.get('LastModifiedDate', '')),
                        'last_modified_user': param.get('LastModifiedUser'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # SSM Documents (owned by account, not AWS)
    try:
        paginator = ssm.get_paginator('list_documents')
        for page in paginator.paginate(Filters=[{'Key': 'Owner', 'Values': ['Self']}]):
            for doc in page.get('DocumentIdentifiers', []):
                doc_name = doc['Name']

                # Get tags
                tags = {}
                try:
                    tag_response = ssm.list_tags_for_resource(
                        ResourceType='Document',
                        ResourceId=doc_name
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'ssm',
                    'type': 'document',
                    'id': doc_name,
                    'arn': f"arn:aws:ssm:{region}:{account_id}:document/{doc_name}",
                    'name': doc_name,
                    'region': region,
                    'details': {
                        'document_type': doc.get('DocumentType'),
                        'document_format': doc.get('DocumentFormat'),
                        'document_version': doc.get('DocumentVersion'),
                        'platform_types': doc.get('PlatformTypes', []),
                        'schema_version': doc.get('SchemaVersion'),
                        'target_type': doc.get('TargetType'),
                        'created_date': str(doc.get('CreatedDate', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Maintenance Windows
    try:
        paginator = ssm.get_paginator('describe_maintenance_windows')
        for page in paginator.paginate():
            for mw in page.get('WindowIdentities', []):
                mw_id = mw['WindowId']
                mw_name = mw.get('Name', mw_id)

                # Get tags
                tags = {}
                try:
                    tag_response = ssm.list_tags_for_resource(
                        ResourceType='MaintenanceWindow',
                        ResourceId=mw_id
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'ssm',
                    'type': 'maintenance-window',
                    'id': mw_id,
                    'arn': f"arn:aws:ssm:{region}:{account_id}:maintenancewindow/{mw_id}",
                    'name': mw_name,
                    'region': region,
                    'details': {
                        'description': mw.get('Description'),
                        'enabled': mw.get('Enabled'),
                        'duration': mw.get('Duration'),
                        'cutoff': mw.get('Cutoff'),
                        'schedule': mw.get('Schedule'),
                        'schedule_timezone': mw.get('ScheduleTimezone'),
                        'next_execution_time': str(mw.get('NextExecutionTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Patch Baselines (owned by account)
    try:
        paginator = ssm.get_paginator('describe_patch_baselines')
        for page in paginator.paginate(Filters=[{'Key': 'OWNER', 'Values': ['Self']}]):
            for pb in page.get('BaselineIdentities', []):
                pb_id = pb['BaselineId']
                pb_name = pb.get('BaselineName', pb_id)

                # Get tags
                tags = {}
                try:
                    tag_response = ssm.list_tags_for_resource(
                        ResourceType='PatchBaseline',
                        ResourceId=pb_id
                    )
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'ssm',
                    'type': 'patch-baseline',
                    'id': pb_id,
                    'arn': f"arn:aws:ssm:{region}:{account_id}:patchbaseline/{pb_id}",
                    'name': pb_name,
                    'region': region,
                    'details': {
                        'description': pb.get('BaselineDescription'),
                        'operating_system': pb.get('OperatingSystem'),
                        'default_baseline': pb.get('DefaultBaseline'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Associations
    try:
        paginator = ssm.get_paginator('list_associations')
        for page in paginator.paginate():
            for assoc in page.get('Associations', []):
                assoc_id = assoc.get('AssociationId')
                if not assoc_id:
                    continue

                resources.append({
                    'service': 'ssm',
                    'type': 'association',
                    'id': assoc_id,
                    'arn': f"arn:aws:ssm:{region}:{account_id}:association/{assoc_id}",
                    'name': assoc.get('AssociationName') or assoc.get('Name', assoc_id),
                    'region': region,
                    'details': {
                        'document_name': assoc.get('Name'),
                        'document_version': assoc.get('DocumentVersion'),
                        'association_version': assoc.get('AssociationVersion'),
                        'schedule_expression': assoc.get('ScheduleExpression'),
                        'targets': assoc.get('Targets', []),
                        'last_execution_date': str(assoc.get('LastExecutionDate', '')),
                        'overview': assoc.get('Overview'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    return resources
