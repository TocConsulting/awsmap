"""
Bedrock resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_bedrock_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Bedrock resources: custom models, model customization jobs, provisioned throughput.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    bedrock = session.client('bedrock', region_name=region)

    # Custom Models
    try:
        paginator = bedrock.get_paginator('list_custom_models')
        for page in paginator.paginate():
            for model in page.get('modelSummaries', []):
                model_arn = model['modelArn']
                model_name = model['modelName']

                try:
                    # Get model details
                    model_response = bedrock.get_custom_model(modelIdentifier=model_arn)

                    resources.append({
                        'service': 'bedrock',
                        'type': 'custom-model',
                        'id': model_name,
                        'arn': model_arn,
                        'name': model_name,
                        'region': region,
                        'details': {
                            'base_model_arn': model_response.get('baseModelArn'),
                            'customization_type': model_response.get('customizationType'),
                            'creation_time': str(model_response.get('creationTime', '')),
                            'job_arn': model_response.get('jobArn'),
                            'training_data_config': model_response.get('trainingDataConfig'),
                            'output_data_config': model_response.get('outputDataConfig'),
                        },
                        'tags': {}
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # Model Customization Jobs (active)
    try:
        paginator = bedrock.get_paginator('list_model_customization_jobs')
        for page in paginator.paginate():
            for job in page.get('modelCustomizationJobSummaries', []):
                job_arn = job['jobArn']
                job_name = job['jobName']

                # Only include active jobs
                status = job.get('status')
                if status in ['Completed', 'Failed', 'Stopped']:
                    continue

                resources.append({
                    'service': 'bedrock',
                    'type': 'customization-job',
                    'id': job_name,
                    'arn': job_arn,
                    'name': job_name,
                    'region': region,
                    'details': {
                        'status': status,
                        'base_model_arn': job.get('baseModelArn'),
                        'customization_type': job.get('customizationType'),
                        'creation_time': str(job.get('creationTime', '')),
                        'end_time': str(job.get('endTime', '')) if job.get('endTime') else None,
                        'last_modified_time': str(job.get('lastModifiedTime', '')),
                        'custom_model_arn': job.get('customModelArn'),
                        'custom_model_name': job.get('customModelName'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Provisioned Model Throughput
    try:
        paginator = bedrock.get_paginator('list_provisioned_model_throughputs')
        for page in paginator.paginate():
            for pmt in page.get('provisionedModelSummaries', []):
                pmt_arn = pmt['provisionedModelArn']
                pmt_name = pmt['provisionedModelName']

                try:
                    # Get provisioned throughput details
                    pmt_response = bedrock.get_provisioned_model_throughput(
                        provisionedModelId=pmt_arn
                    )

                    # Get tags
                    tags = {}
                    try:
                        tag_response = bedrock.list_tags_for_resource(resourceARN=pmt_arn)
                        for tag in tag_response.get('tags', []):
                            tags[tag.get('key', '')] = tag.get('value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'bedrock',
                        'type': 'provisioned-throughput',
                        'id': pmt_name,
                        'arn': pmt_arn,
                        'name': pmt_name,
                        'region': region,
                        'details': {
                            'status': pmt_response.get('status'),
                            'model_arn': pmt_response.get('modelArn'),
                            'desired_model_arn': pmt_response.get('desiredModelArn'),
                            'foundation_model_arn': pmt_response.get('foundationModelArn'),
                            'model_units': pmt_response.get('modelUnits'),
                            'desired_model_units': pmt_response.get('desiredModelUnits'),
                            'commitment_duration': pmt_response.get('commitmentDuration'),
                            'commitment_expiration_time': str(pmt_response.get('commitmentExpirationTime', '')) if pmt_response.get('commitmentExpirationTime') else None,
                            'creation_time': str(pmt_response.get('creationTime', '')),
                            'last_modified_time': str(pmt_response.get('lastModifiedTime', '')),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # Guardrails
    try:
        paginator = bedrock.get_paginator('list_guardrails')
        for page in paginator.paginate():
            for guardrail in page.get('guardrails', []):
                guardrail_id = guardrail['id']
                guardrail_arn = guardrail['arn']
                guardrail_name = guardrail['name']

                # Get tags
                tags = {}
                try:
                    tag_response = bedrock.list_tags_for_resource(resourceARN=guardrail_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'bedrock',
                    'type': 'guardrail',
                    'id': guardrail_id,
                    'arn': guardrail_arn,
                    'name': guardrail_name,
                    'region': region,
                    'details': {
                        'status': guardrail.get('status'),
                        'version': guardrail.get('version'),
                        'created_at': str(guardrail.get('createdAt', '')),
                        'updated_at': str(guardrail.get('updatedAt', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # --- Bedrock Agent resources (uses bedrock-agent client) ---
    bedrock_agent = session.client('bedrock-agent', region_name=region)

    # Agents
    try:
        paginator = bedrock_agent.get_paginator('list_agents')
        for page in paginator.paginate():
            for agent_summary in page.get('agentSummaries', []):
                agent_id = agent_summary['agentId']

                try:
                    agent_response = bedrock_agent.get_agent(agentId=agent_id)
                    agent = agent_response['agent']
                    agent_arn = agent['agentArn']
                    agent_name = agent.get('agentName', agent_id)

                    # Get tags
                    tags = {}
                    try:
                        tag_response = bedrock_agent.list_tags_for_resource(resourceArn=agent_arn)
                        tags = tag_response.get('tags', {})
                    except Exception:
                        pass

                    resources.append({
                        'service': 'bedrock',
                        'type': 'agent',
                        'id': agent_id,
                        'arn': agent_arn,
                        'name': agent_name,
                        'region': region,
                        'details': {
                            'status': agent.get('agentStatus'),
                            'foundation_model': agent.get('foundationModel'),
                            'instruction': agent.get('instruction'),
                            'description': agent.get('description'),
                            'agent_version': agent.get('agentVersion'),
                            'idle_session_ttl': agent.get('idleSessionTTLInSeconds'),
                            'agent_resource_role_arn': agent.get('agentResourceRoleArn'),
                            'created_at': str(agent.get('createdAt', '')),
                            'updated_at': str(agent.get('updatedAt', '')),
                            'prepared_at': str(agent.get('preparedAt', '')) if agent.get('preparedAt') else None,
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    # Knowledge Bases
    try:
        paginator = bedrock_agent.get_paginator('list_knowledge_bases')
        for page in paginator.paginate():
            for kb_summary in page.get('knowledgeBaseSummaries', []):
                kb_id = kb_summary['knowledgeBaseId']

                try:
                    kb_response = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
                    kb = kb_response['knowledgeBase']
                    kb_arn = kb['knowledgeBaseArn']
                    kb_name = kb.get('name', kb_id)

                    # Get tags
                    tags = {}
                    try:
                        tag_response = bedrock_agent.list_tags_for_resource(resourceArn=kb_arn)
                        tags = tag_response.get('tags', {})
                    except Exception:
                        pass

                    # Extract embedding model ARN from knowledge base configuration
                    kb_config = kb.get('knowledgeBaseConfiguration', {})
                    embedding_model_arn = None
                    vector_config = kb_config.get('vectorKnowledgeBaseConfiguration', {})
                    if vector_config:
                        embedding_model_arn = vector_config.get('embeddingModelArn')

                    storage_config = kb.get('storageConfiguration', {})

                    resources.append({
                        'service': 'bedrock',
                        'type': 'knowledge-base',
                        'id': kb_id,
                        'arn': kb_arn,
                        'name': kb_name,
                        'region': region,
                        'details': {
                            'status': kb.get('status'),
                            'description': kb.get('description'),
                            'knowledge_base_type': kb_config.get('type'),
                            'embedding_model_arn': embedding_model_arn,
                            'storage_type': storage_config.get('type'),
                            'role_arn': kb.get('roleArn'),
                            'created_at': str(kb.get('createdAt', '')),
                            'updated_at': str(kb.get('updatedAt', '')),
                        },
                        'tags': tags
                    })

                    # Data Sources for this Knowledge Base
                    try:
                        ds_paginator = bedrock_agent.get_paginator('list_data_sources')
                        for ds_page in ds_paginator.paginate(knowledgeBaseId=kb_id):
                            for ds in ds_page.get('dataSourceSummaries', []):
                                ds_id = ds['dataSourceId']
                                ds_name = ds.get('name', ds_id)

                                resources.append({
                                    'service': 'bedrock',
                                    'type': 'data-source',
                                    'id': ds_id,
                                    'arn': f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/{kb_id}/data-source/{ds_id}",
                                    'name': ds_name,
                                    'region': region,
                                    'details': {
                                        'status': ds.get('status'),
                                        'description': ds.get('description'),
                                        'knowledge_base_id': kb_id,
                                        'updated_at': str(ds.get('updatedAt', '')),
                                    },
                                    'tags': {}
                                })
                    except Exception:
                        pass

                except Exception:
                    pass
    except Exception:
        pass

    return resources
