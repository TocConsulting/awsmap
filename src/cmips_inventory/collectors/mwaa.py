"""
AWS MWAA (Managed Workflows for Apache Airflow) resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_mwaa_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS MWAA resources: environments.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    mwaa = session.client('mwaa', region_name=region)

    # Environments
    try:
        paginator = mwaa.get_paginator('list_environments')
        for page in paginator.paginate():
            for env_name in page.get('Environments', []):
                env_arn = f"arn:aws:airflow:{region}:{account_id}:environment/{env_name}"

                details = {}
                tags = {}

                # Get detailed environment info
                try:
                    env_response = mwaa.get_environment(Name=env_name)
                    env = env_response.get('Environment', {})
                    env_arn = env.get('Arn', env_arn)

                    details = {
                        'status': env.get('Status'),
                        'airflow_version': env.get('AirflowVersion'),
                        'environment_class': env.get('EnvironmentClass'),
                        'max_workers': env.get('MaxWorkers'),
                        'min_workers': env.get('MinWorkers'),
                        'schedulers': env.get('Schedulers'),
                        'webserver_access_mode': env.get('WebserverAccessMode'),
                        'webserver_url': env.get('WebserverUrl'),
                        'execution_role_arn': env.get('ExecutionRoleArn'),
                        'service_role_arn': env.get('ServiceRoleArn'),
                        'kms_key': env.get('KmsKey'),
                        'source_bucket_arn': env.get('SourceBucketArn'),
                        'dag_s3_path': env.get('DagS3Path'),
                        'plugins_s3_path': env.get('PluginsS3Path'),
                        'requirements_s3_path': env.get('RequirementsS3Path'),
                        'startup_script_s3_path': env.get('StartupScriptS3Path'),
                        'weekly_maintenance_window_start': env.get('WeeklyMaintenanceWindowStart'),
                        'created_at': str(env.get('CreatedAt', '')),
                    }

                    # Network configuration
                    network = env.get('NetworkConfiguration', {})
                    if network:
                        details['security_group_ids'] = network.get('SecurityGroupIds', [])
                        details['subnet_ids'] = network.get('SubnetIds', [])

                    # Logging configuration
                    logging = env.get('LoggingConfiguration', {})
                    if logging:
                        log_types = []
                        for log_type in ['DagProcessingLogs', 'SchedulerLogs', 'TaskLogs', 'WebserverLogs', 'WorkerLogs']:
                            log_config = logging.get(log_type, {})
                            if log_config.get('Enabled'):
                                log_types.append(log_type.replace('Logs', ''))
                        details['enabled_log_types'] = log_types

                    # Get tags from environment response
                    tags = env.get('Tags', {})

                except Exception:
                    pass

                # If we didn't get tags from get_environment, try list_tags_for_resource
                if not tags:
                    try:
                        tag_response = mwaa.list_tags_for_resource(ResourceArn=env_arn)
                        tags = tag_response.get('Tags', {})
                    except Exception:
                        pass

                resources.append({
                    'service': 'mwaa',
                    'type': 'environment',
                    'id': env_name,
                    'arn': env_arn,
                    'name': env_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
