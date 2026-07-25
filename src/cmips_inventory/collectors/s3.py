"""
S3 resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional

from cmips_inventory.auth import get_enabled_regions


def collect_s3_resources(session: boto3.Session, region: Optional[str], account_id: str, filter_regions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Collect S3 buckets. S3 is a global service but buckets exist in regions.

    Args:
        session: boto3.Session to use
        region: Not used for S3 (global service)
        account_id: AWS account ID
        filter_regions: Optional list of regions to limit S3 Tables collection

    Returns:
        List of resource dictionaries
    """
    resources = []
    s3 = session.client('s3')

    # List all buckets
    try:
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
    except Exception:
        return resources

    for bucket in buckets:
        bucket_name = bucket['Name']
        creation_date = bucket.get('CreationDate')

        # Get bucket location
        bucket_region = 'us-east-1'  # Default
        try:
            loc_response = s3.get_bucket_location(Bucket=bucket_name)
            loc = loc_response.get('LocationConstraint')
            if loc:
                bucket_region = loc
        except Exception:
            pass

        # Get bucket tags
        tags = {}
        try:
            tag_response = s3.get_bucket_tagging(Bucket=bucket_name)
            for tag in tag_response.get('TagSet', []):
                tags[tag.get('Key', '')] = tag.get('Value', '')
        except Exception:
            pass

        # Get versioning status
        versioning = None
        try:
            ver_response = s3.get_bucket_versioning(Bucket=bucket_name)
            versioning = ver_response.get('Status')
        except Exception:
            pass

        # Get encryption configuration
        encryption = None
        try:
            enc_response = s3.get_bucket_encryption(Bucket=bucket_name)
            rules = enc_response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            if rules:
                encryption = rules[0].get('ApplyServerSideEncryptionByDefault', {}).get('SSEAlgorithm')
        except Exception:
            pass

        # Get public access block
        public_access_blocked = None
        try:
            pab_response = s3.get_public_access_block(Bucket=bucket_name)
            config = pab_response.get('PublicAccessBlockConfiguration', {})
            public_access_blocked = all([
                config.get('BlockPublicAcls', False),
                config.get('IgnorePublicAcls', False),
                config.get('BlockPublicPolicy', False),
                config.get('RestrictPublicBuckets', False)
            ])
        except Exception:
            pass

        resources.append({
            'service': 's3',
            'type': 'bucket',
            'id': bucket_name,
            'arn': f"arn:aws:s3:::{bucket_name}",
            'name': bucket_name,
            'region': bucket_region,
            'details': {
                'creation_date': str(creation_date) if creation_date else None,
                'versioning': versioning,
                'encryption': encryption,
                'public_access_blocked': public_access_blocked,
            },
            'tags': tags
        })

    # S3 Tables - regional service, use filter_regions if provided
    try:
        table_regions = filter_regions if filter_regions else get_enabled_regions(session)
    except Exception:
        table_regions = []

    for table_region in table_regions:
        try:
            s3tables = session.client('s3tables', region_name=table_region)
        except Exception:
            continue

        # List table buckets
        table_buckets = []
        try:
            paginator = s3tables.get_paginator('list_table_buckets')
            for page in paginator.paginate():
                table_buckets.extend(page.get('tableBuckets', []))
        except Exception:
            continue

        for tb in table_buckets:
            tb_arn = tb['arn']
            tb_name = tb['name']

            # Get tags for table bucket
            tags = {}
            try:
                tag_response = s3tables.list_tags_for_resource(resourceArn=tb_arn)
                tags = tag_response.get('tags', {})
            except Exception:
                pass

            resources.append({
                'service': 's3',
                'type': 'table-bucket',
                'id': tb_name,
                'arn': tb_arn,
                'name': tb_name,
                'region': table_region,
                'details': {
                    'creation_date': str(tb.get('createdAt')) if tb.get('createdAt') else None,
                    'owner_account_id': tb.get('ownerAccountId'),
                    'table_bucket_id': tb.get('tableBucketId'),
                    'bucket_type': tb.get('type'),
                },
                'tags': tags
            })

            # List namespaces for this table bucket
            try:
                ns_paginator = s3tables.get_paginator('list_namespaces')
                for ns_page in ns_paginator.paginate(tableBucketARN=tb_arn):
                    for ns in ns_page.get('namespaces', []):
                        ns_name = ns.get('namespace', [])
                        ns_name_str = '/'.join(ns_name) if isinstance(ns_name, list) else str(ns_name)
                        ns_id = ns.get('namespaceId', ns_name_str)

                        resources.append({
                            'service': 's3',
                            'type': 'namespace',
                            'id': ns_id,
                            'arn': f"{tb_arn}/namespace/{ns_name_str}",
                            'name': ns_name_str,
                            'region': table_region,
                            'details': {
                                'table_bucket_arn': tb_arn,
                                'table_bucket_name': tb_name,
                                'namespace_id': ns_id,
                                'created_at': str(ns.get('createdAt')) if ns.get('createdAt') else None,
                                'created_by': ns.get('createdBy'),
                                'owner_account_id': ns.get('ownerAccountId'),
                            },
                            'tags': {}
                        })
            except Exception:
                pass

            # List tables for this table bucket
            try:
                tbl_paginator = s3tables.get_paginator('list_tables')
                for tbl_page in tbl_paginator.paginate(tableBucketARN=tb_arn):
                    for tbl in tbl_page.get('tables', []):
                        tbl_arn = tbl['tableARN']
                        tbl_name = tbl['name']
                        tbl_namespace = tbl.get('namespace', [])
                        tbl_namespace_str = '/'.join(tbl_namespace) if isinstance(tbl_namespace, list) else str(tbl_namespace)

                        # Get tags for table
                        tbl_tags = {}
                        try:
                            tbl_tag_response = s3tables.list_tags_for_resource(resourceArn=tbl_arn)
                            tbl_tags = tbl_tag_response.get('tags', {})
                        except Exception:
                            pass

                        resources.append({
                            'service': 's3',
                            'type': 'table',
                            'id': tbl_name,
                            'arn': tbl_arn,
                            'name': tbl_name,
                            'region': table_region,
                            'details': {
                                'table_bucket_arn': tb_arn,
                                'table_bucket_name': tb_name,
                                'namespace': tbl_namespace_str,
                                'table_type': tbl.get('type'),
                                'created_at': str(tbl.get('createdAt')) if tbl.get('createdAt') else None,
                                'modified_at': str(tbl.get('modifiedAt')) if tbl.get('modifiedAt') else None,
                                'managed_by_service': tbl.get('managedByService'),
                                'namespace_id': tbl.get('namespaceId'),
                                'table_bucket_id': tbl.get('tableBucketId'),
                            },
                            'tags': tbl_tags
                        })
            except Exception:
                pass

    return resources
