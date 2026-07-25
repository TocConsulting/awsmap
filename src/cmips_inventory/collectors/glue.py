"""
Glue resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_glue_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Glue resources: databases, tables, jobs, crawlers, connections.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    glue = session.client('glue', region_name=region)

    # Glue Databases
    databases = []
    try:
        paginator = glue.get_paginator('get_databases')
        for page in paginator.paginate():
            for db in page.get('DatabaseList', []):
                databases.append(db)
                db_name = db['Name']

                resources.append({
                    'service': 'glue',
                    'type': 'database',
                    'id': db_name,
                    'arn': f"arn:aws:glue:{region}:{account_id}:database/{db_name}",
                    'name': db_name,
                    'region': region,
                    'details': {
                        'description': db.get('Description'),
                        'location_uri': db.get('LocationUri'),
                        'create_time': str(db.get('CreateTime', '')),
                        'catalog_id': db.get('CatalogId'),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Glue Tables (for each database)
    for db in databases:
        db_name = db['Name']
        try:
            paginator = glue.get_paginator('get_tables')
            for page in paginator.paginate(DatabaseName=db_name):
                for table in page.get('TableList', []):
                    table_name = table['Name']

                    resources.append({
                        'service': 'glue',
                        'type': 'table',
                        'id': f"{db_name}/{table_name}",
                        'arn': f"arn:aws:glue:{region}:{account_id}:table/{db_name}/{table_name}",
                        'name': table_name,
                        'region': region,
                        'details': {
                            'database_name': db_name,
                            'description': table.get('Description'),
                            'table_type': table.get('TableType'),
                            'owner': table.get('Owner'),
                            'create_time': str(table.get('CreateTime', '')),
                            'update_time': str(table.get('UpdateTime', '')),
                            'last_access_time': str(table.get('LastAccessTime', '')),
                            'retention': table.get('Retention'),
                            'storage_descriptor_location': table.get('StorageDescriptor', {}).get('Location'),
                            'storage_descriptor_input_format': table.get('StorageDescriptor', {}).get('InputFormat'),
                            'columns_count': len(table.get('StorageDescriptor', {}).get('Columns', [])),
                            'partition_keys_count': len(table.get('PartitionKeys', [])),
                        },
                        'tags': {}
                    })
        except Exception:
            pass

    # Glue Jobs
    try:
        paginator = glue.get_paginator('get_jobs')
        for page in paginator.paginate():
            for job in page.get('Jobs', []):
                job_name = job['Name']

                # Get tags
                tags = {}
                try:
                    tag_response = glue.get_tags(
                        ResourceArn=f"arn:aws:glue:{region}:{account_id}:job/{job_name}"
                    )
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'glue',
                    'type': 'job',
                    'id': job_name,
                    'arn': f"arn:aws:glue:{region}:{account_id}:job/{job_name}",
                    'name': job_name,
                    'region': region,
                    'details': {
                        'description': job.get('Description'),
                        'role': job.get('Role'),
                        'created_on': str(job.get('CreatedOn', '')),
                        'last_modified_on': str(job.get('LastModifiedOn', '')),
                        'glue_version': job.get('GlueVersion'),
                        'worker_type': job.get('WorkerType'),
                        'number_of_workers': job.get('NumberOfWorkers'),
                        'max_capacity': job.get('MaxCapacity'),
                        'max_retries': job.get('MaxRetries'),
                        'timeout': job.get('Timeout'),
                        'execution_class': job.get('ExecutionClass'),
                        'command_name': job.get('Command', {}).get('Name'),
                        'command_python_version': job.get('Command', {}).get('PythonVersion'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Glue Crawlers
    try:
        paginator = glue.get_paginator('get_crawlers')
        for page in paginator.paginate():
            for crawler in page.get('Crawlers', []):
                crawler_name = crawler['Name']

                # Get tags
                tags = {}
                try:
                    tag_response = glue.get_tags(
                        ResourceArn=f"arn:aws:glue:{region}:{account_id}:crawler/{crawler_name}"
                    )
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'glue',
                    'type': 'crawler',
                    'id': crawler_name,
                    'arn': f"arn:aws:glue:{region}:{account_id}:crawler/{crawler_name}",
                    'name': crawler_name,
                    'region': region,
                    'details': {
                        'role': crawler.get('Role'),
                        'database_name': crawler.get('DatabaseName'),
                        'description': crawler.get('Description'),
                        'state': crawler.get('State'),
                        'table_prefix': crawler.get('TablePrefix'),
                        'schedule': crawler.get('Schedule', {}).get('ScheduleExpression'),
                        'schedule_state': crawler.get('Schedule', {}).get('State'),
                        'crawl_elapsed_time': crawler.get('CrawlElapsedTime'),
                        'creation_time': str(crawler.get('CreationTime', '')),
                        'last_updated': str(crawler.get('LastUpdated', '')),
                        'last_crawl_status': crawler.get('LastCrawl', {}).get('Status'),
                        'version': crawler.get('Version'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # Glue Connections
    try:
        paginator = glue.get_paginator('get_connections')
        for page in paginator.paginate():
            for conn in page.get('ConnectionList', []):
                conn_name = conn['Name']

                resources.append({
                    'service': 'glue',
                    'type': 'connection',
                    'id': conn_name,
                    'arn': f"arn:aws:glue:{region}:{account_id}:connection/{conn_name}",
                    'name': conn_name,
                    'region': region,
                    'details': {
                        'connection_type': conn.get('ConnectionType'),
                        'description': conn.get('Description'),
                        'creation_time': str(conn.get('CreationTime', '')),
                        'last_updated_time': str(conn.get('LastUpdatedTime', '')),
                        'physical_connection_requirements': bool(conn.get('PhysicalConnectionRequirements')),
                    },
                    'tags': {}
                })
    except Exception:
        pass

    # Glue Registries
    try:
        paginator = glue.get_paginator('list_registries')
        for page in paginator.paginate():
            for registry in page.get('Registries', []):
                registry_name = registry['RegistryName']
                registry_arn = registry['RegistryArn']

                # Get tags
                tags = {}
                try:
                    tag_response = glue.get_tags(ResourceArn=registry_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'glue',
                    'type': 'registry',
                    'id': registry_name,
                    'arn': registry_arn,
                    'name': registry_name,
                    'region': region,
                    'details': {
                        'status': registry.get('Status'),
                        'description': registry.get('Description'),
                        'created_time': str(registry.get('CreatedTime', '')),
                        'updated_time': str(registry.get('UpdatedTime', '')),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
