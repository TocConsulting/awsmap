"""
AWS Transfer Family resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_transfer_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Transfer Family resources: servers, users, workflows, connectors,
    certificates, profiles, agreements, host keys, and web apps.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    transfer = session.client('transfer', region_name=region)

    # Servers
    server_ids = []
    try:
        paginator = transfer.get_paginator('list_servers')
        for page in paginator.paginate():
            for server in page.get('Servers', []):
                server_id = server['ServerId']
                server_ids.append(server_id)
                server_arn = server.get('Arn', f"arn:aws:transfer:{region}:{account_id}:server/{server_id}")

                details = {
                    'state': server.get('State'),
                    'endpoint_type': server.get('EndpointType'),
                    'identity_provider_type': server.get('IdentityProviderType'),
                    'logging_role': server.get('LoggingRole'),
                    'user_count': server.get('UserCount'),
                    'domain': server.get('Domain'),
                }

                # Get detailed server info
                try:
                    desc_response = transfer.describe_server(ServerId=server_id)
                    srv = desc_response.get('Server', {})
                    details.update({
                        'protocols': srv.get('Protocols', []),
                        'security_policy_name': srv.get('SecurityPolicyName'),
                        'certificate': srv.get('Certificate'),
                        'endpoint': srv.get('EndpointDetails', {}).get('AddressAllocationIds'),
                        'vpc_endpoint_id': srv.get('EndpointDetails', {}).get('VpcEndpointId'),
                        'vpc_id': srv.get('EndpointDetails', {}).get('VpcId'),
                        'subnet_ids': srv.get('EndpointDetails', {}).get('SubnetIds'),
                        'security_group_ids': srv.get('EndpointDetails', {}).get('SecurityGroupIds'),
                        'host_key_fingerprint': srv.get('HostKeyFingerprint'),
                        'workflow_on_upload': srv.get('WorkflowDetails', {}).get('OnUpload'),
                        'workflow_on_partial_upload': srv.get('WorkflowDetails', {}).get('OnPartialUpload'),
                        'structured_log_destinations': srv.get('StructuredLogDestinations'),
                        's3_storage_options': srv.get('S3StorageOptions'),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = transfer.list_tags_for_resource(Arn=server_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'transfer',
                    'type': 'server',
                    'id': server_id,
                    'arn': server_arn,
                    'name': server_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Users (per server)
    for server_id in server_ids:
        try:
            paginator = transfer.get_paginator('list_users')
            for page in paginator.paginate(ServerId=server_id):
                for user in page.get('Users', []):
                    user_name = user['UserName']
                    user_arn = user.get('Arn', f"arn:aws:transfer:{region}:{account_id}:user/{server_id}/{user_name}")

                    details = {
                        'server_id': server_id,
                        'home_directory_type': user.get('HomeDirectoryType'),
                        'home_directory': user.get('HomeDirectory'),
                        'role': user.get('Role'),
                        'ssh_public_key_count': user.get('SshPublicKeyCount'),
                    }

                    # Get detailed user info
                    try:
                        desc_response = transfer.describe_user(ServerId=server_id, UserName=user_name)
                        usr = desc_response.get('User', {})
                        details.update({
                            'home_directory_mappings': usr.get('HomeDirectoryMappings'),
                            'policy': usr.get('Policy'),
                            'posix_profile': usr.get('PosixProfile'),
                        })
                    except Exception:
                        pass

                    # Get tags
                    tags = {}
                    try:
                        tag_response = transfer.list_tags_for_resource(Arn=user_arn)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'transfer',
                        'type': 'user',
                        'id': f"{server_id}/{user_name}",
                        'arn': user_arn,
                        'name': user_name,
                        'region': region,
                        'details': details,
                        'tags': tags
                    })
        except Exception:
            pass

    # Host Keys (per server)
    for server_id in server_ids:
        try:
            paginator = transfer.get_paginator('list_host_keys')
            for page in paginator.paginate(ServerId=server_id):
                for key in page.get('HostKeys', []):
                    key_id = key['HostKeyId']
                    key_arn = key.get('Arn', f"arn:aws:transfer:{region}:{account_id}:host-key/{server_id}/{key_id}")

                    # Get tags
                    tags = {}
                    try:
                        tag_response = transfer.list_tags_for_resource(Arn=key_arn)
                        for tag in tag_response.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                    except Exception:
                        pass

                    resources.append({
                        'service': 'transfer',
                        'type': 'host-key',
                        'id': f"{server_id}/{key_id}",
                        'arn': key_arn,
                        'name': key.get('Description', key_id),
                        'region': region,
                        'details': {
                            'server_id': server_id,
                            'fingerprint': key.get('Fingerprint'),
                            'type': key.get('Type'),
                            'date_imported': str(key.get('DateImported', '')),
                        },
                        'tags': tags
                    })
        except Exception:
            pass

    # Workflows
    try:
        paginator = transfer.get_paginator('list_workflows')
        for page in paginator.paginate():
            for workflow in page.get('Workflows', []):
                workflow_id = workflow['WorkflowId']
                workflow_arn = workflow.get('Arn', f"arn:aws:transfer:{region}:{account_id}:workflow/{workflow_id}")

                details = {
                    'description': workflow.get('Description'),
                }

                # Get detailed workflow info
                try:
                    desc_response = transfer.describe_workflow(WorkflowId=workflow_id)
                    wf = desc_response.get('Workflow', {})
                    steps = wf.get('Steps', [])
                    on_exception_steps = wf.get('OnExceptionSteps', [])
                    details.update({
                        'steps_count': len(steps),
                        'on_exception_steps_count': len(on_exception_steps),
                        'step_types': [s.get('Type') for s in steps],
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = transfer.list_tags_for_resource(Arn=workflow_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'transfer',
                    'type': 'workflow',
                    'id': workflow_id,
                    'arn': workflow_arn,
                    'name': workflow.get('Description', workflow_id),
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Connectors
    try:
        paginator = transfer.get_paginator('list_connectors')
        for page in paginator.paginate():
            for connector in page.get('Connectors', []):
                connector_id = connector['ConnectorId']
                connector_arn = connector.get('Arn', f"arn:aws:transfer:{region}:{account_id}:connector/{connector_id}")

                details = {
                    'url': connector.get('Url'),
                }

                # Get detailed connector info
                try:
                    desc_response = transfer.describe_connector(ConnectorId=connector_id)
                    conn = desc_response.get('Connector', {})
                    details.update({
                        'access_role': conn.get('AccessRole'),
                        'logging_role': conn.get('LoggingRole'),
                        'security_policy_name': conn.get('SecurityPolicyName'),
                        'sftp_user_secret_id': conn.get('SftpConfig', {}).get('UserSecretId'),
                        'sftp_trusted_host_keys': conn.get('SftpConfig', {}).get('TrustedHostKeys'),
                        'as2_local_profile_id': conn.get('As2Config', {}).get('LocalProfileId'),
                        'as2_partner_profile_id': conn.get('As2Config', {}).get('PartnerProfileId'),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = transfer.list_tags_for_resource(Arn=connector_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'transfer',
                    'type': 'connector',
                    'id': connector_id,
                    'arn': connector_arn,
                    'name': connector_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Certificates
    try:
        paginator = transfer.get_paginator('list_certificates')
        for page in paginator.paginate():
            for cert in page.get('Certificates', []):
                cert_id = cert['CertificateId']
                cert_arn = cert.get('Arn', f"arn:aws:transfer:{region}:{account_id}:certificate/{cert_id}")

                details = {
                    'usage': cert.get('Usage'),
                    'status': cert.get('Status'),
                    'active_date': str(cert.get('ActiveDate', '')),
                    'inactive_date': str(cert.get('InactiveDate', '')),
                    'type': cert.get('Type'),
                    'description': cert.get('Description'),
                }

                # Get detailed certificate info
                try:
                    desc_response = transfer.describe_certificate(CertificateId=cert_id)
                    certificate = desc_response.get('Certificate', {})
                    details.update({
                        'serial': certificate.get('Serial'),
                        'not_before_date': str(certificate.get('NotBeforeDate', '')),
                        'not_after_date': str(certificate.get('NotAfterDate', '')),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = transfer.list_tags_for_resource(Arn=cert_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'transfer',
                    'type': 'certificate',
                    'id': cert_id,
                    'arn': cert_arn,
                    'name': cert.get('Description', cert_id),
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Profiles (AS2)
    try:
        paginator = transfer.get_paginator('list_profiles')
        for page in paginator.paginate():
            for profile in page.get('Profiles', []):
                profile_id = profile['ProfileId']
                profile_arn = profile.get('Arn', f"arn:aws:transfer:{region}:{account_id}:profile/{profile_id}")

                details = {
                    'profile_type': profile.get('ProfileType'),
                    'as2_id': profile.get('As2Id'),
                }

                # Get detailed profile info
                try:
                    desc_response = transfer.describe_profile(ProfileId=profile_id)
                    prof = desc_response.get('Profile', {})
                    details.update({
                        'certificate_ids': prof.get('CertificateIds', []),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = transfer.list_tags_for_resource(Arn=profile_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'transfer',
                    'type': 'profile',
                    'id': profile_id,
                    'arn': profile_arn,
                    'name': profile.get('As2Id', profile_id),
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Agreements (AS2)
    try:
        paginator = transfer.get_paginator('list_agreements')
        # Agreements require a server ID, so iterate over servers
        for server_id in server_ids:
            try:
                for page in paginator.paginate(ServerId=server_id):
                    for agreement in page.get('Agreements', []):
                        agreement_id = agreement['AgreementId']
                        agreement_arn = agreement.get('Arn', f"arn:aws:transfer:{region}:{account_id}:agreement/{server_id}/{agreement_id}")

                        details = {
                            'server_id': server_id,
                            'status': agreement.get('Status'),
                            'local_profile_id': agreement.get('LocalProfileId'),
                            'partner_profile_id': agreement.get('PartnerProfileId'),
                        }

                        # Get detailed agreement info
                        try:
                            desc_response = transfer.describe_agreement(AgreementId=agreement_id, ServerId=server_id)
                            agr = desc_response.get('Agreement', {})
                            details.update({
                                'description': agr.get('Description'),
                                'base_directory': agr.get('BaseDirectory'),
                                'access_role': agr.get('AccessRole'),
                            })
                        except Exception:
                            pass

                        # Get tags
                        tags = {}
                        try:
                            tag_response = transfer.list_tags_for_resource(Arn=agreement_arn)
                            for tag in tag_response.get('Tags', []):
                                tags[tag.get('Key', '')] = tag.get('Value', '')
                        except Exception:
                            pass

                        resources.append({
                            'service': 'transfer',
                            'type': 'agreement',
                            'id': f"{server_id}/{agreement_id}",
                            'arn': agreement_arn,
                            'name': agreement.get('Description', agreement_id),
                            'region': region,
                            'details': details,
                            'tags': tags
                        })
            except Exception:
                pass
    except Exception:
        pass

    # Web Apps
    try:
        paginator = transfer.get_paginator('list_web_apps')
        for page in paginator.paginate():
            for webapp in page.get('WebApps', []):
                webapp_id = webapp['WebAppId']
                webapp_arn = webapp.get('Arn', f"arn:aws:transfer:{region}:{account_id}:webapp/{webapp_id}")

                details = {
                    'access_endpoint': webapp.get('AccessEndpoint'),
                    'web_app_endpoint': webapp.get('WebAppEndpoint'),
                }

                # Get detailed web app info
                try:
                    desc_response = transfer.describe_web_app(WebAppId=webapp_id)
                    app = desc_response.get('WebApp', {})
                    details.update({
                        'identity_provider_type': app.get('IdentityProviderDetails', {}).get('IdentityProviderType'),
                        'described_identity_provider_details': app.get('DescribedIdentityProviderDetails'),
                    })
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_response = transfer.list_tags_for_resource(Arn=webapp_arn)
                    for tag in tag_response.get('Tags', []):
                        tags[tag.get('Key', '')] = tag.get('Value', '')
                except Exception:
                    pass

                resources.append({
                    'service': 'transfer',
                    'type': 'web-app',
                    'id': webapp_id,
                    'arn': webapp_arn,
                    'name': webapp_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
