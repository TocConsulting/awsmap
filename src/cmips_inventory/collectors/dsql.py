"""
Aurora DSQL resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_dsql_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect Aurora DSQL resources: clusters.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    dsql = session.client('dsql', region_name=region)

    # DSQL Clusters
    try:
        paginator = dsql.get_paginator('list_clusters')
        for page in paginator.paginate():
            for cluster_summary in page.get('clusters', []):
                cluster_id = cluster_summary['identifier']

                try:
                    # Get cluster details
                    cluster = dsql.get_cluster(identifier=cluster_id)

                    cluster_arn = cluster.get('arn', f"arn:aws:dsql:{region}:{account_id}:cluster/{cluster_id}")

                    # Tags are included in get_cluster response
                    tags = cluster.get('tags', {})

                    encryption = cluster.get('encryptionDetails', {})
                    multi_region = cluster.get('multiRegionProperties', {})

                    resources.append({
                        'service': 'dsql',
                        'type': 'cluster',
                        'id': cluster_id,
                        'arn': cluster_arn,
                        'name': cluster_id,
                        'region': region,
                        'details': {
                            'status': cluster.get('status'),
                            'endpoint': cluster.get('endpoint'),
                            'creation_time': str(cluster.get('creationTime', '')),
                            'deletion_protection_enabled': cluster.get('deletionProtectionEnabled'),
                            'encryption_type': encryption.get('encryptionType'),
                            'encryption_status': encryption.get('encryptionStatus'),
                            'kms_key_arn': encryption.get('kmsKeyArn'),
                            'witness_region': multi_region.get('witnessRegion'),
                            'linked_clusters': multi_region.get('clusters', []),
                        },
                        'tags': tags
                    })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
