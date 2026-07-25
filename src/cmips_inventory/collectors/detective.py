"""
AWS Amazon Detective resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_detective_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Amazon Detective resources: behavior graphs, members, and investigations.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    detective = session.client('detective', region_name=region)

    # Behavior Graphs
    try:
        paginator = detective.get_paginator('list_graphs')
        for page in paginator.paginate():
            for graph in page.get('GraphList', []):
                graph_arn = graph['Arn']
                graph_id = graph_arn.split('/')[-1]

                details = {
                    'created_time': str(graph.get('CreatedTime', '')),
                }

                # Get tags
                tags = {}
                try:
                    tag_response = detective.list_tags_for_resource(ResourceArn=graph_arn)
                    tags = tag_response.get('Tags', {})
                except Exception:
                    pass

                resources.append({
                    'service': 'detective',
                    'type': 'graph',
                    'id': graph_id,
                    'arn': graph_arn,
                    'name': graph_id,
                    'region': region,
                    'details': details,
                    'tags': tags
                })

                # Members in this graph
                try:
                    member_paginator = detective.get_paginator('list_members')
                    for member_page in member_paginator.paginate(GraphArn=graph_arn):
                        for member in member_page.get('MemberDetails', []):
                            member_id = member['AccountId']

                            member_details = {
                                'graph_arn': graph_arn,
                                'email_address': member.get('EmailAddress'),
                                'status': member.get('Status'),
                                'disabled_reason': member.get('DisabledReason'),
                                'invited_time': str(member.get('InvitedTime', '')),
                                'updated_time': str(member.get('UpdatedTime', '')),
                                'volume_usage_in_bytes': member.get('VolumeUsageInBytes'),
                                'volume_usage_updated_time': str(member.get('VolumeUsageUpdatedTime', '')),
                                'percent_of_graph_utilization': member.get('PercentOfGraphUtilization'),
                                'invitation_type': member.get('InvitationType'),
                            }

                            # Get datasource packages for this member
                            try:
                                ds_response = detective.batch_get_graph_member_datasources(
                                    GraphArn=graph_arn,
                                    AccountIds=[member_id]
                                )
                                for ds_member in ds_response.get('MemberDatasources', []):
                                    if ds_member.get('AccountId') == member_id:
                                        member_details['datasource_packages'] = list(ds_member.get('DatasourcePackageIngestHistory', {}).keys())
                            except Exception:
                                pass

                            resources.append({
                                'service': 'detective',
                                'type': 'member',
                                'id': member_id,
                                'arn': f"{graph_arn}/member/{member_id}",
                                'name': member_id,
                                'region': region,
                                'details': member_details,
                                'tags': {}
                            })
                except Exception:
                    pass

                # Investigations in this graph
                try:
                    inv_paginator = detective.get_paginator('list_investigations')
                    for inv_page in inv_paginator.paginate(GraphArn=graph_arn):
                        for investigation in inv_page.get('InvestigationDetails', []):
                            inv_id = investigation['InvestigationId']

                            inv_details = {
                                'graph_arn': graph_arn,
                                'entity_arn': investigation.get('EntityArn'),
                                'entity_type': investigation.get('EntityType'),
                                'severity': investigation.get('Severity'),
                                'status': investigation.get('Status'),
                                'state': investigation.get('State'),
                                'created_time': str(investigation.get('CreatedTime', '')),
                            }

                            resources.append({
                                'service': 'detective',
                                'type': 'investigation',
                                'id': inv_id,
                                'arn': f"{graph_arn}/investigation/{inv_id}",
                                'name': inv_id,
                                'region': region,
                                'details': inv_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
