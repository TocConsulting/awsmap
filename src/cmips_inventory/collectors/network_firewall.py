"""
AWS Network Firewall resource collector.
"""

import boto3
from typing import List, Dict, Any, Optional


def collect_network_firewall_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Network Firewall resources: firewalls, policies, rule groups,
    and TLS inspection configurations.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    nfw = session.client('network-firewall', region_name=region)

    # Firewalls
    try:
        paginator = nfw.get_paginator('list_firewalls')
        for page in paginator.paginate():
            for fw in page.get('Firewalls', []):
                fw_name = fw.get('FirewallName')
                fw_arn = fw.get('FirewallArn', f"arn:aws:network-firewall:{region}:{account_id}:firewall/{fw_name}")

                details = {}
                tags = {}

                # Get detailed firewall info
                try:
                    fw_response = nfw.describe_firewall(FirewallArn=fw_arn)
                    firewall = fw_response.get('Firewall', {})
                    fw_status = fw_response.get('FirewallStatus', {})

                    details = {
                        'firewall_id': firewall.get('FirewallId'),
                        'firewall_policy_arn': firewall.get('FirewallPolicyArn'),
                        'vpc_id': firewall.get('VpcId'),
                        'subnet_mappings': [s.get('SubnetId') for s in firewall.get('SubnetMappings', [])],
                        'delete_protection': firewall.get('DeleteProtection'),
                        'subnet_change_protection': firewall.get('SubnetChangeProtection'),
                        'firewall_policy_change_protection': firewall.get('FirewallPolicyChangeProtection'),
                        'description': firewall.get('Description'),
                        'encryption_configuration': firewall.get('EncryptionConfiguration', {}).get('Type'),
                        'status': fw_status.get('Status'),
                        'configuration_sync_state': fw_status.get('ConfigurationSyncStateSummary'),
                    }

                    # Get sync states per AZ
                    sync_states = fw_status.get('SyncStates', {})
                    if sync_states:
                        details['availability_zones'] = list(sync_states.keys())

                    tags = {t['Key']: t['Value'] for t in firewall.get('Tags', [])}

                except Exception:
                    pass

                # Get logging configuration
                try:
                    log_response = nfw.describe_logging_configuration(FirewallArn=fw_arn)
                    log_config = log_response.get('LoggingConfiguration', {})
                    log_destinations = log_config.get('LogDestinationConfigs', [])
                    if log_destinations:
                        details['logging_types'] = [d.get('LogType') for d in log_destinations]
                        details['logging_destinations'] = [d.get('LogDestinationType') for d in log_destinations]
                except Exception:
                    pass

                resources.append({
                    'service': 'network-firewall',
                    'type': 'firewall',
                    'id': fw_name,
                    'arn': fw_arn,
                    'name': fw_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Firewall Policies
    try:
        paginator = nfw.get_paginator('list_firewall_policies')
        for page in paginator.paginate():
            for policy in page.get('FirewallPolicies', []):
                policy_name = policy.get('Name')
                policy_arn = policy.get('Arn', f"arn:aws:network-firewall:{region}:{account_id}:firewall-policy/{policy_name}")

                details = {}
                tags = {}

                # Get detailed policy info
                try:
                    policy_response = nfw.describe_firewall_policy(FirewallPolicyArn=policy_arn)
                    policy_detail = policy_response.get('FirewallPolicy', {})
                    policy_metadata = policy_response.get('FirewallPolicyResponse', {})

                    details = {
                        'policy_id': policy_metadata.get('FirewallPolicyId'),
                        'description': policy_metadata.get('Description'),
                        'status': policy_metadata.get('FirewallPolicyStatus'),
                        'number_of_associations': policy_metadata.get('NumberOfAssociations'),
                        'encryption_configuration': policy_metadata.get('EncryptionConfiguration', {}).get('Type'),
                        'stateless_default_actions': policy_detail.get('StatelessDefaultActions', []),
                        'stateless_fragment_default_actions': policy_detail.get('StatelessFragmentDefaultActions', []),
                        'stateful_engine_options': policy_detail.get('StatefulEngineOptions', {}).get('RuleOrder'),
                        'stateless_rule_group_count': len(policy_detail.get('StatelessRuleGroupReferences', [])),
                        'stateful_rule_group_count': len(policy_detail.get('StatefulRuleGroupReferences', [])),
                    }

                    tags = {t['Key']: t['Value'] for t in policy_metadata.get('Tags', [])}

                except Exception:
                    pass

                resources.append({
                    'service': 'network-firewall',
                    'type': 'firewall-policy',
                    'id': policy_name,
                    'arn': policy_arn,
                    'name': policy_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # Rule Groups
    try:
        paginator = nfw.get_paginator('list_rule_groups')
        for page in paginator.paginate():
            for rg in page.get('RuleGroups', []):
                rg_name = rg.get('Name')
                rg_arn = rg.get('Arn', f"arn:aws:network-firewall:{region}:{account_id}:rule-group/{rg_name}")

                details = {}
                tags = {}

                # Get detailed rule group info
                try:
                    rg_response = nfw.describe_rule_group(RuleGroupArn=rg_arn)
                    rg_metadata = rg_response.get('RuleGroupResponse', {})

                    details = {
                        'rule_group_id': rg_metadata.get('RuleGroupId'),
                        'description': rg_metadata.get('Description'),
                        'type': rg_metadata.get('Type'),
                        'capacity': rg_metadata.get('Capacity'),
                        'status': rg_metadata.get('RuleGroupStatus'),
                        'number_of_associations': rg_metadata.get('NumberOfAssociations'),
                        'encryption_configuration': rg_metadata.get('EncryptionConfiguration', {}).get('Type'),
                        'source_metadata': rg_metadata.get('SourceMetadata', {}).get('SourceArn'),
                        'sns_topic': rg_metadata.get('SnsTopic'),
                        'last_modified_time': str(rg_metadata.get('LastModifiedTime', '')),
                    }

                    # Get analysis results if available
                    analysis = rg_metadata.get('AnalysisResults', [])
                    if analysis:
                        details['analysis_results_count'] = len(analysis)

                    tags = {t['Key']: t['Value'] for t in rg_metadata.get('Tags', [])}

                except Exception:
                    pass

                resources.append({
                    'service': 'network-firewall',
                    'type': 'rule-group',
                    'id': rg_name,
                    'arn': rg_arn,
                    'name': rg_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    # TLS Inspection Configurations
    try:
        paginator = nfw.get_paginator('list_tls_inspection_configurations')
        for page in paginator.paginate():
            for tls in page.get('TLSInspectionConfigurations', []):
                tls_name = tls.get('Name')
                tls_arn = tls.get('Arn', f"arn:aws:network-firewall:{region}:{account_id}:tls-configuration/{tls_name}")

                details = {}
                tags = {}

                # Get detailed TLS config
                try:
                    tls_response = nfw.describe_tls_inspection_configuration(
                        TLSInspectionConfigurationArn=tls_arn
                    )
                    tls_metadata = tls_response.get('TLSInspectionConfigurationResponse', {})

                    details = {
                        'tls_inspection_configuration_id': tls_metadata.get('TLSInspectionConfigurationId'),
                        'description': tls_metadata.get('Description'),
                        'status': tls_metadata.get('TLSInspectionConfigurationStatus'),
                        'number_of_associations': tls_metadata.get('NumberOfAssociations'),
                        'encryption_configuration': tls_metadata.get('EncryptionConfiguration', {}).get('Type'),
                        'last_modified_time': str(tls_metadata.get('LastModifiedTime', '')),
                    }

                    # Get certificate info
                    certs = tls_metadata.get('Certificates', [])
                    if certs:
                        details['certificates_count'] = len(certs)
                        details['certificate_arns'] = [c.get('CertificateArn') for c in certs]

                    tags = {t['Key']: t['Value'] for t in tls_metadata.get('Tags', [])}

                except Exception:
                    pass

                resources.append({
                    'service': 'network-firewall',
                    'type': 'tls-inspection-configuration',
                    'id': tls_name,
                    'arn': tls_arn,
                    'name': tls_name,
                    'region': region,
                    'details': details,
                    'tags': tags
                })
    except Exception:
        pass

    return resources
