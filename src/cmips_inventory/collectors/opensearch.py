"""
OpenSearch Service resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_opensearch_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect OpenSearch Service resources: domains, serverless collections.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []

    # OpenSearch Domains
    opensearch = session.client('opensearch', region_name=region)
    try:
        response = opensearch.list_domain_names()
        domain_names = [d['DomainName'] for d in response.get('DomainNames', [])]

        if domain_names:
            # Describe domains
            desc_response = opensearch.describe_domains(DomainNames=domain_names)
            for domain in desc_response.get('DomainStatusList', []):
                domain_name = domain['DomainName']
                domain_arn = domain['ARN']

                # Get tags
                tags = {}
                try:
                    tag_response = opensearch.list_tags(ARN=domain_arn)
                    for tag in tag_response.get('TagList', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'opensearch',
                    'type': 'domain',
                    'id': domain['DomainId'],
                    'arn': domain_arn,
                    'name': domain_name,
                    'region': region,
                    'details': {
                        'engine_version': domain.get('EngineVersion'),
                        'created': domain.get('Created'),
                        'deleted': domain.get('Deleted'),
                        'processing': domain.get('Processing'),
                        'upgrade_processing': domain.get('UpgradeProcessing'),
                        'endpoint': domain.get('Endpoint'),
                        'endpoints': domain.get('Endpoints'),
                        'instance_type': domain.get('ClusterConfig', {}).get('InstanceType'),
                        'instance_count': domain.get('ClusterConfig', {}).get('InstanceCount'),
                        'dedicated_master_enabled': domain.get('ClusterConfig', {}).get('DedicatedMasterEnabled'),
                        'zone_awareness_enabled': domain.get('ClusterConfig', {}).get('ZoneAwarenessEnabled'),
                        'warm_enabled': domain.get('ClusterConfig', {}).get('WarmEnabled'),
                        'ebs_enabled': domain.get('EBSOptions', {}).get('EBSEnabled'),
                        'ebs_volume_size': domain.get('EBSOptions', {}).get('VolumeSize'),
                        'encryption_at_rest_enabled': domain.get('EncryptionAtRestOptions', {}).get('Enabled'),
                        'node_to_node_encryption_enabled': domain.get('NodeToNodeEncryptionOptions', {}).get('Enabled'),
                        'vpc_id': domain.get('VPCOptions', {}).get('VPCId'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    # OpenSearch Serverless Collections
    try:
        oss = session.client('opensearchserverless', region_name=region)
        paginator = oss.get_paginator('list_collections')
        for page in paginator.paginate():
            for collection in page.get('collectionSummaries', []):
                coll_id = collection['id']
                coll_name = collection['name']
                coll_arn = collection['arn']

                # Get tags
                tags = {}
                try:
                    tag_response = oss.list_tags_for_resource(resourceArn=coll_arn)
                    for tag in tag_response.get('tags', []):
                        tags[tag.get('key', '')] = tag.get('value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'opensearch',
                    'type': 'serverless-collection',
                    'id': coll_id,
                    'arn': coll_arn,
                    'name': coll_name,
                    'region': region,
                    'details': {
                        'status': collection.get('status'),
                        'type': collection.get('type'),
                    },
                    'tags': tags
                })
    except Exception:
        pass

    return resources
