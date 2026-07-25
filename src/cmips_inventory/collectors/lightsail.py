"""
AWS Lightsail resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


# Lightsail supported regions (not available in all regions)
# Source: https://docs.aws.amazon.com/general/latest/gr/lightsail.html
LIGHTSAIL_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1',
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2',
    'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3',
}


def collect_lightsail_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Lightsail resources: instances, disks, load balancers, databases,
    distributions, buckets, container services, static IPs, domains, and certificates.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions to avoid connection timeouts
    if region not in LIGHTSAIL_REGIONS:
        return []

    resources = []
    lightsail = session.client('lightsail', region_name=region)

    # Instances
    try:
        paginator = lightsail.get_paginator('get_instances')
        for page in paginator.paginate():
            for instance in page.get('instances', []):
                instance_name = instance['name']
                instance_arn = instance.get('arn', f"arn:aws:lightsail:{region}:{account_id}:Instance/{instance_name}")

                details = {
                    'blueprint_id': instance.get('blueprintId'),
                    'blueprint_name': instance.get('blueprintName'),
                    'bundle_id': instance.get('bundleId'),
                    'state': instance.get('state', {}).get('name'),
                    'public_ip': instance.get('publicIpAddress'),
                    'private_ip': instance.get('privateIpAddress'),
                    'ipv6_addresses': instance.get('ipv6Addresses', []),
                    'hardware_cpu_count': instance.get('hardware', {}).get('cpuCount'),
                    'hardware_ram_size_gb': instance.get('hardware', {}).get('ramSizeInGb'),
                    'hardware_disks': len(instance.get('hardware', {}).get('disks', [])),
                    'is_static_ip': instance.get('isStaticIp'),
                    'username': instance.get('username'),
                    'ssh_key_name': instance.get('sshKeyName'),
                    'created_at': str(instance.get('createdAt', '')),
                }

                # Get networking info
                networking = instance.get('networking', {})
                if networking:
                    details['monthly_transfer_gb'] = networking.get('monthlyTransfer', {}).get('gbPerMonthAllocated')
                    ports = networking.get('ports', [])
                    details['open_ports'] = [f"{p.get('fromPort')}-{p.get('toPort')}/{p.get('protocol')}" for p in ports]

                tags = {t['key']: t.get('value', '') for t in instance.get('tags', [])}

                resources.append({
                    'service': 'lightsail',
                    'type': 'instance',
                    'id': instance_name,
                    'arn': instance_arn,
                    'name': instance_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Disks
    try:
        paginator = lightsail.get_paginator('get_disks')
        for page in paginator.paginate():
            for disk in page.get('disks', []):
                disk_name = disk['name']
                disk_arn = disk.get('arn', f"arn:aws:lightsail:{region}:{account_id}:Disk/{disk_name}")

                details = {
                    'size_in_gb': disk.get('sizeInGb'),
                    'state': disk.get('state'),
                    'is_attached': disk.get('isAttached'),
                    'attached_to': disk.get('attachedTo'),
                    'attachment_state': disk.get('attachmentState'),
                    'path': disk.get('path'),
                    'iops': disk.get('iops'),
                    'is_system_disk': disk.get('isSystemDisk'),
                    'created_at': str(disk.get('createdAt', '')),
                }

                tags = {t['key']: t.get('value', '') for t in disk.get('tags', [])}

                resources.append({
                    'service': 'lightsail',
                    'type': 'disk',
                    'id': disk_name,
                    'arn': disk_arn,
                    'name': disk_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Load Balancers
    try:
        paginator = lightsail.get_paginator('get_load_balancers')
        for page in paginator.paginate():
            for lb in page.get('loadBalancers', []):
                lb_name = lb['name']
                lb_arn = lb.get('arn', f"arn:aws:lightsail:{region}:{account_id}:LoadBalancer/{lb_name}")

                details = {
                    'dns_name': lb.get('dnsName'),
                    'state': lb.get('state'),
                    'protocol': lb.get('protocol'),
                    'public_ports': lb.get('publicPorts', []),
                    'health_check_path': lb.get('healthCheckPath'),
                    'instance_port': lb.get('instancePort'),
                    'instance_health_summary': len(lb.get('instanceHealthSummary', [])),
                    'tls_certificate_summaries': len(lb.get('tlsCertificateSummaries', [])),
                    'https_redirection_enabled': lb.get('httpsRedirectionEnabled'),
                    'ip_address_type': lb.get('ipAddressType'),
                    'created_at': str(lb.get('createdAt', '')),
                }

                tags = {t['key']: t.get('value', '') for t in lb.get('tags', [])}

                resources.append({
                    'service': 'lightsail',
                    'type': 'load-balancer',
                    'id': lb_name,
                    'arn': lb_arn,
                    'name': lb_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Relational Databases
    try:
        paginator = lightsail.get_paginator('get_relational_databases')
        for page in paginator.paginate():
            for db in page.get('relationalDatabases', []):
                db_name = db['name']
                db_arn = db.get('arn', f"arn:aws:lightsail:{region}:{account_id}:RelationalDatabase/{db_name}")

                details = {
                    'engine': db.get('engine'),
                    'engine_version': db.get('engineVersion'),
                    'state': db.get('state'),
                    'master_username': db.get('masterUsername'),
                    'master_database_name': db.get('masterDatabaseName'),
                    'bundle_id': db.get('relationalDatabaseBundleId'),
                    'blueprint_id': db.get('relationalDatabaseBlueprintId'),
                    'hardware_cpu_count': db.get('hardware', {}).get('cpuCount'),
                    'hardware_ram_size_gb': db.get('hardware', {}).get('ramSizeInGb'),
                    'hardware_disk_size_gb': db.get('hardware', {}).get('diskSizeInGb'),
                    'publicly_accessible': db.get('publiclyAccessible'),
                    'master_endpoint_address': db.get('masterEndpoint', {}).get('address'),
                    'master_endpoint_port': db.get('masterEndpoint', {}).get('port'),
                    'backup_retention_enabled': db.get('backupRetentionEnabled'),
                    'preferred_backup_window': db.get('preferredBackupWindow'),
                    'preferred_maintenance_window': db.get('preferredMaintenanceWindow'),
                    'ca_certificate_identifier': db.get('caCertificateIdentifier'),
                    'created_at': str(db.get('createdAt', '')),
                }

                tags = {t['key']: t.get('value', '') for t in db.get('tags', [])}

                resources.append({
                    'service': 'lightsail',
                    'type': 'database',
                    'id': db_name,
                    'arn': db_arn,
                    'name': db_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Distributions (CDN)
    try:
        response = lightsail.get_distributions()
        for dist in response.get('distributions', []):
            dist_name = dist['name']
            dist_arn = dist.get('arn', f"arn:aws:lightsail:{region}:{account_id}:Distribution/{dist_name}")

            details = {
                'status': dist.get('status'),
                'domain_name': dist.get('domainName'),
                'alternative_domain_names': dist.get('alternativeDomainNames', []),
                'origin_name': dist.get('origin', {}).get('name'),
                'origin_protocol_policy': dist.get('origin', {}).get('protocolPolicy'),
                'origin_region': dist.get('origin', {}).get('regionName'),
                'default_cache_behavior': dist.get('defaultCacheBehavior', {}).get('behavior'),
                'certificate_name': dist.get('certificateName'),
                'is_enabled': dist.get('isEnabled'),
                'ip_address_type': dist.get('ipAddressType'),
                'bundle_id': dist.get('bundleId'),
                'created_at': str(dist.get('createdAt', '')),
            }

            tags = {t['key']: t.get('value', '') for t in dist.get('tags', [])}

            resources.append({
                'service': 'lightsail',
                'type': 'distribution',
                'id': dist_name,
                'arn': dist_arn,
                'name': dist_name,
                'region': region,
                'details': details,
                'tags': tags
            })
    except Exception:
        pass

    # Buckets
    try:
        response = lightsail.get_buckets()
        for bucket in response.get('buckets', []):
            bucket_name = bucket['name']
            bucket_arn = bucket.get('arn', f"arn:aws:lightsail:{region}:{account_id}:Bucket/{bucket_name}")

            details = {
                'url': bucket.get('url'),
                'state': bucket.get('state', {}).get('code'),
                'access_rules_public': bucket.get('accessRules', {}).get('getObject'),
                'access_rules_allow_public_overrides': bucket.get('accessRules', {}).get('allowPublicOverrides'),
                'object_versioning': bucket.get('objectVersioning'),
                'able_to_update_bundle': bucket.get('ableToUpdateBundle'),
                'bundle_id': bucket.get('bundleId'),
                'readonly_access_accounts': bucket.get('readonlyAccessAccounts', []),
                'resources_receiving_access': len(bucket.get('resourcesReceivingAccess', [])),
                'created_at': str(bucket.get('createdAt', '')),
            }

            tags = {t['key']: t.get('value', '') for t in bucket.get('tags', [])}

            resources.append({
                'service': 'lightsail',
                'type': 'bucket',
                'id': bucket_name,
                'arn': bucket_arn,
                'name': bucket_name,
                'region': region,
                'details': details,
                'tags': tags
            })
    except Exception:
        pass

    # Container Services
    try:
        response = lightsail.get_container_services()
        for cs in response.get('containerServices', []):
            cs_name = cs['containerServiceName']
            cs_arn = cs.get('arn', f"arn:aws:lightsail:{region}:{account_id}:ContainerService/{cs_name}")

            details = {
                'state': cs.get('state'),
                'state_detail': cs.get('stateDetail', {}).get('code'),
                'power': cs.get('power'),
                'power_id': cs.get('powerId'),
                'scale': cs.get('scale'),
                'is_disabled': cs.get('isDisabled'),
                'principal_arn': cs.get('principalArn'),
                'private_domain_name': cs.get('privateDomainName'),
                'url': cs.get('url'),
                'public_domain_names': cs.get('publicDomainNames', {}),
                'private_registry_access': cs.get('privateRegistryAccess', {}).get('ecrImagePullerRole', {}).get('isActive'),
                'created_at': str(cs.get('createdAt', '')),
            }

            tags = {t['key']: t.get('value', '') for t in cs.get('tags', [])}

            resources.append({
                'service': 'lightsail',
                'type': 'container-service',
                'id': cs_name,
                'arn': cs_arn,
                'name': cs_name,
                'region': region,
                'details': details,
                'tags': tags
            })
    except Exception:
        pass

    # Static IPs
    try:
        paginator = lightsail.get_paginator('get_static_ips')
        for page in paginator.paginate():
            for ip in page.get('staticIps', []):
                ip_name = ip['name']
                ip_arn = ip.get('arn', f"arn:aws:lightsail:{region}:{account_id}:StaticIp/{ip_name}")

                details = {
                    'ip_address': ip.get('ipAddress'),
                    'is_attached': ip.get('isAttached'),
                    'attached_to': ip.get('attachedTo'),
                    'created_at': str(ip.get('createdAt', '')),
                }

                resources.append({
                    'service': 'lightsail',
                    'type': 'static-ip',
                    'id': ip_name,
                    'arn': ip_arn,
                    'name': ip_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Domains
    try:
        paginator = lightsail.get_paginator('get_domains')
        for page in paginator.paginate():
            for domain in page.get('domains', []):
                domain_name = domain['name']
                domain_arn = domain.get('arn', f"arn:aws:lightsail:{region}:{account_id}:Domain/{domain_name}")

                details = {
                    'domain_entries_count': len(domain.get('domainEntries', [])),
                    'registered_domain_delegation_info': domain.get('registeredDomainDelegationInfo'),
                    'created_at': str(domain.get('createdAt', '')),
                }

                tags = {t['key']: t.get('value', '') for t in domain.get('tags', [])}

                resources.append({
                    'service': 'lightsail',
                    'type': 'domain',
                    'id': domain_name,
                    'arn': domain_arn,
                    'name': domain_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Certificates
    try:
        response = lightsail.get_certificates()
        for cert in response.get('certificates', []):
            cert_summary = cert.get('certificateSummary', cert)
            cert_name = cert_summary.get('certificateName', cert_summary.get('name', 'unknown'))
            cert_arn = cert_summary.get('certificateArn', f"arn:aws:lightsail:{region}:{account_id}:Certificate/{cert_name}")

            details = {
                'domain_name': cert_summary.get('domainName'),
                'certificate_detail': cert.get('certificateDetail', {}),
            }

            # Get more details if available
            cert_detail = cert.get('certificateDetail', {})
            if cert_detail:
                details.update({
                    'status': cert_detail.get('status'),
                    'subject_alternative_names': cert_detail.get('subjectAlternativeNames', []),
                    'issuer': cert_detail.get('issuer'),
                    'not_before': str(cert_detail.get('notBefore', '')),
                    'not_after': str(cert_detail.get('notAfter', '')),
                    'in_use_resource_count': cert_detail.get('inUseResourceCount'),
                    'key_algorithm': cert_detail.get('keyAlgorithm'),
                })

            tags = {t['key']: t.get('value', '') for t in cert.get('tags', [])}

            resources.append({
                'service': 'lightsail',
                'type': 'certificate',
                'id': cert_name,
                'arn': cert_arn,
                'name': cert_name,
                'region': region,
                'details': details,
                'tags': tags
            })
    except Exception:
        pass

    # Key Pairs
    try:
        paginator = lightsail.get_paginator('get_key_pairs')
        for page in paginator.paginate():
            for kp in page.get('keyPairs', []):
                kp_name = kp['name']
                kp_arn = kp.get('arn', f"arn:aws:lightsail:{region}:{account_id}:KeyPair/{kp_name}")

                details = {
                    'fingerprint': kp.get('fingerprint'),
                    'created_at': str(kp.get('createdAt', '')),
                }

                tags = {t['key']: t.get('value', '') for t in kp.get('tags', [])}

                resources.append({
                    'service': 'lightsail',
                    'type': 'key-pair',
                    'id': kp_name,
                    'arn': kp_arn,
                    'name': kp_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
