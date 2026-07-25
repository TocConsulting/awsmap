"""
SageMaker resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_sagemaker_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect SageMaker resources: notebook instances, endpoints, models, domains.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sagemaker = session.client('sagemaker', region_name=region)

    # SageMaker Notebook Instances
    try:
        paginator = sagemaker.get_paginator('list_notebook_instances')
        for page in paginator.paginate():
            for nb in page.get('NotebookInstances', []):
                nb_name = nb['NotebookInstanceName']
                nb_arn = nb['NotebookInstanceArn']

                # Get tags
                tags = {}
                try:
                    tag_response = sagemaker.list_tags(ResourceArn=nb_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'sagemaker',
                    'type': 'notebook-instance',
                    'id': nb_name,
                    'arn': nb_arn,
                    'name': nb_name,
                    'region': region,
                    'details': {
                        'status': nb.get('NotebookInstanceStatus'),
                        'instance_type': nb.get('InstanceType'),
                        'url': nb.get('Url'),
                        'creation_time': str(nb.get('CreationTime', '')),
                        'last_modified_time': str(nb.get('LastModifiedTime', '')),
                        'default_code_repository': nb.get('DefaultCodeRepository'),
                        'additional_code_repositories': nb.get('AdditionalCodeRepositories', []),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # SageMaker Endpoints
    try:
        paginator = sagemaker.get_paginator('list_endpoints')
        for page in paginator.paginate():
            for endpoint in page.get('Endpoints', []):
                endpoint_name = endpoint['EndpointName']
                endpoint_arn = endpoint['EndpointArn']

                # Get tags
                tags = {}
                try:
                    tag_response = sagemaker.list_tags(ResourceArn=endpoint_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'sagemaker',
                    'type': 'endpoint',
                    'id': endpoint_name,
                    'arn': endpoint_arn,
                    'name': endpoint_name,
                    'region': region,
                    'details': {
                        'status': endpoint.get('EndpointStatus'),
                        'creation_time': str(endpoint.get('CreationTime', '')),
                        'last_modified_time': str(endpoint.get('LastModifiedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # SageMaker Models
    try:
        paginator = sagemaker.get_paginator('list_models')
        for page in paginator.paginate():
            for model in page.get('Models', []):
                model_name = model['ModelName']
                model_arn = model['ModelArn']

                # Get tags
                tags = {}
                try:
                    tag_response = sagemaker.list_tags(ResourceArn=model_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'sagemaker',
                    'type': 'model',
                    'id': model_name,
                    'arn': model_arn,
                    'name': model_name,
                    'region': region,
                    'details': {
                        'creation_time': str(model.get('CreationTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # SageMaker Domains (Studio)
    try:
        paginator = sagemaker.get_paginator('list_domains')
        for page in paginator.paginate():
            for domain in page.get('Domains', []):
                domain_id = domain['DomainId']
                domain_arn = domain['DomainArn']
                domain_name = domain.get('DomainName', domain_id)

                # Get tags
                tags = {}
                try:
                    tag_response = sagemaker.list_tags(ResourceArn=domain_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'sagemaker',
                    'type': 'domain',
                    'id': domain_id,
                    'arn': domain_arn,
                    'name': domain_name,
                    'region': region,
                    'details': {
                        'status': domain.get('Status'),
                        'creation_time': str(domain.get('CreationTime', '')),
                        'last_modified_time': str(domain.get('LastModifiedTime', '')),
                        'url': domain.get('Url'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # SageMaker Training Jobs (recent active)
    try:
        paginator = sagemaker.get_paginator('list_training_jobs')
        for page in paginator.paginate(StatusEquals='InProgress', MaxResults=100):
            for job in page.get('TrainingJobSummaries', []):
                job_name = job['TrainingJobName']
                job_arn = job['TrainingJobArn']

                # Get tags
                tags = {}
                try:
                    tag_response = sagemaker.list_tags(ResourceArn=job_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'sagemaker',
                    'type': 'training-job',
                    'id': job_name,
                    'arn': job_arn,
                    'name': job_name,
                    'region': region,
                    'details': {
                        'status': job.get('TrainingJobStatus'),
                        'creation_time': str(job.get('CreationTime', '')),
                        'training_end_time': str(job.get('TrainingEndTime', '')),
                        'last_modified_time': str(job.get('LastModifiedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # SageMaker Feature Groups
    try:
        paginator = sagemaker.get_paginator('list_feature_groups')
        for page in paginator.paginate():
            for fg in page.get('FeatureGroupSummaries', []):
                fg_name = fg['FeatureGroupName']
                fg_arn = fg['FeatureGroupArn']

                # Get tags
                tags = {}
                try:
                    tag_response = sagemaker.list_tags(ResourceArn=fg_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'sagemaker',
                    'type': 'feature-group',
                    'id': fg_name,
                    'arn': fg_arn,
                    'name': fg_name,
                    'region': region,
                    'details': {
                        'status': fg.get('FeatureGroupStatus'),
                        'creation_time': str(fg.get('CreationTime', '')),
                        'offline_store_status': fg.get('OfflineStoreStatus', {}).get('Status'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
