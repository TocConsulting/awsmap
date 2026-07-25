"""
AWS Amazon Macie resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_macie2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Amazon Macie resources: classification jobs, custom data identifiers,
    findings filters, allow lists, and members.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    macie = session.client('macie2', region_name=region)

    # Check if Macie is enabled
    try:
        status = macie.get_macie_session()
        if status.get('status') != 'ENABLED':
            return []
    except Exception:
        return []

    # Classification Jobs
    try:
        paginator = macie.get_paginator('list_classification_jobs')
        for page in paginator.paginate():
            for job in page.get('items', []):
                job_id = job['jobId']

                details = {
                    'job_type': job.get('jobType'),
                    'job_status': job.get('jobStatus'),
                    'name': job.get('name'),
                    'created_at': str(job.get('createdAt', '')),
                    'bucket_criteria_includes': job.get('bucketCriteria', {}).get('includes'),
                }

                # Get full job details
                try:
                    job_detail = macie.describe_classification_job(jobId=job_id)
                    details['description'] = job_detail.get('description')
                    details['sampling_percentage'] = job_detail.get('samplingPercentage')
                    details['initial_run'] = job_detail.get('initialRun')
                    details['last_run_time'] = str(job_detail.get('lastRunTime', ''))
                    details['managed_data_identifier_selector'] = job_detail.get('managedDataIdentifierSelector')

                    schedule = job_detail.get('scheduleFrequency', {})
                    if schedule:
                        details['schedule_frequency'] = schedule
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = macie.list_tags_for_resource(
                        resourceArn=f"arn:aws:macie2:{region}:{account_id}:classification-job/{job_id}"
                    )
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'macie2',
                    'type': 'classification-job',
                    'id': job_id,
                    'arn': f"arn:aws:macie2:{region}:{account_id}:classification-job/{job_id}",
                    'name': job.get('name', job_id),
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Custom Data Identifiers
    try:
        paginator = macie.get_paginator('list_custom_data_identifiers')
        for page in paginator.paginate():
            for cdi in page.get('items', []):
                cdi_id = cdi['id']
                cdi_name = cdi.get('name', cdi_id)

                details = {
                    'description': cdi.get('description'),
                    'created_at': str(cdi.get('createdAt', '')),
                }

                # Get full details
                try:
                    cdi_detail = macie.get_custom_data_identifier(id=cdi_id)
                    details['regex'] = cdi_detail.get('regex')
                    details['keywords'] = cdi_detail.get('keywords', [])
                    details['ignore_words'] = cdi_detail.get('ignoreWords', [])
                    details['maximum_match_distance'] = cdi_detail.get('maximumMatchDistance')
                    details['severity_levels'] = cdi_detail.get('severityLevels', [])
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = macie.list_tags_for_resource(
                        resourceArn=cdi.get('arn', f"arn:aws:macie2:{region}:{account_id}:custom-data-identifier/{cdi_id}")
                    )
                    tags = tag_response.get('tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'macie2',
                    'type': 'custom-data-identifier',
                    'id': cdi_id,
                    'arn': cdi.get('arn', f"arn:aws:macie2:{region}:{account_id}:custom-data-identifier/{cdi_id}"),
                    'name': cdi_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Findings Filters
    try:
        paginator = macie.get_paginator('list_findings_filters')
        for page in paginator.paginate():
            for ff in page.get('findingsFilterListItems', []):
                ff_id = ff['id']
                ff_name = ff.get('name', ff_id)

                details = {
                    'action': ff.get('action'),
                }

                # Get full details
                try:
                    ff_detail = macie.get_findings_filter(id=ff_id)
                    details['description'] = ff_detail.get('description')
                    details['position'] = ff_detail.get('position')
                    details['finding_criteria'] = ff_detail.get('findingCriteria', {})
                except Exception:
                    pass

                # Get tags
                tags = ff.get('tags', {})

                resources.append({
                    'service': 'macie2',
                    'type': 'findings-filter',
                    'id': ff_id,
                    'arn': ff.get('arn', f"arn:aws:macie2:{region}:{account_id}:findings-filter/{ff_id}"),
                    'name': ff_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Allow Lists
    try:
        paginator = macie.get_paginator('list_allow_lists')
        for page in paginator.paginate():
            for al in page.get('allowLists', []):
                al_id = al['id']
                al_name = al.get('name', al_id)

                details = {
                    'description': al.get('description'),
                    'created_at': str(al.get('createdAt', '')),
                    'updated_at': str(al.get('updatedAt', '')),
                }

                # Get full details
                try:
                    al_detail = macie.get_allow_list(id=al_id)
                    criteria = al_detail.get('criteria', {})
                    if 's3WordsList' in criteria:
                        details['s3_bucket'] = criteria['s3WordsList'].get('bucketName')
                        details['s3_object_key'] = criteria['s3WordsList'].get('objectKey')
                    if 'regex' in criteria:
                        details['regex'] = criteria['regex']
                except Exception:
                    pass

                # Get tags
                tags = al.get('tags', {})

                resources.append({
                    'service': 'macie2',
                    'type': 'allow-list',
                    'id': al_id,
                    'arn': al.get('arn', f"arn:aws:macie2:{region}:{account_id}:allow-list/{al_id}"),
                    'name': al_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Members (multi-account)
    try:
        paginator = macie.get_paginator('list_members')
        for page in paginator.paginate():
            for member in page.get('members', []):
                member_id = member['accountId']

                details = {
                    'email': member.get('email'),
                    'relationship_status': member.get('relationshipStatus'),
                    'administrator_account_id': member.get('administratorAccountId'),
                    'master_account_id': member.get('masterAccountId'),
                    'invited_at': str(member.get('invitedAt', '')),
                    'updated_at': str(member.get('updatedAt', '')),
                }

                tags = member.get('tags', {})

                resources.append({
                    'service': 'macie2',
                    'type': 'member',
                    'id': member_id,
                    'arn': member.get('arn', f"arn:aws:macie2:{region}:{account_id}:member/{member_id}"),
                    'name': member_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
