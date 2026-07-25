"""
AWS GameLift resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


# GameLift supported regions (from https://docs.aws.amazon.com/general/latest/gr/gamelift.html)
GAMELIFT_REGIONS = {
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
    'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2',
    'sa-east-1',
}


def collect_gamelift_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS GameLift resources: builds, fleets, aliases, scripts, game session queues,
    matchmaking configurations, and matchmaking rule sets.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    # Skip unsupported regions
    if region not in GAMELIFT_REGIONS:
        return []

    resources = []
    gamelift = session.client('gamelift', region_name=region)

    # Builds
    try:
        paginator = gamelift.get_paginator('list_builds')
        for page in paginator.paginate():
            for build in page.get('Builds', []):
                build_id = build['BuildId']
                build_arn = build.get('BuildArn', f"arn:aws:gamelift:{region}:{account_id}:build/{build_id}")
                build_name = build.get('Name', build_id)

                details = {
                    'version': build.get('Version'),
                    'status': build.get('Status'),
                    'size_on_disk': build.get('SizeOnDisk'),
                    'operating_system': build.get('OperatingSystem'),
                    'server_sdk_version': build.get('ServerSdkVersion'),
                }

                resources.append({
                    'service': 'gamelift',
                    'type': 'build',
                    'id': build_id,
                    'arn': build_arn,
                    'name': build_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Fleets
    try:
        fleet_ids = []
        paginator = gamelift.get_paginator('list_fleets')
        for page in paginator.paginate():
            fleet_ids.extend(page.get('FleetIds', []))

        if fleet_ids:
            # Get fleet attributes in batches
            for i in range(0, len(fleet_ids), 25):
                batch = fleet_ids[i:i+25]
                try:
                    response = gamelift.describe_fleet_attributes(FleetIds=batch)
                    for fleet in response.get('FleetAttributes', []):
                        fleet_id = fleet['FleetId']
                        fleet_arn = fleet.get('FleetArn', f"arn:aws:gamelift:{region}:{account_id}:fleet/{fleet_id}")
                        fleet_name = fleet.get('Name', fleet_id)

                        details = {
                            'status': fleet.get('Status'),
                            'fleet_type': fleet.get('FleetType'),
                            'instance_type': fleet.get('InstanceType'),
                            'compute_type': fleet.get('ComputeType'),
                            'operating_system': fleet.get('OperatingSystem'),
                            'build_id': fleet.get('BuildId'),
                            'script_id': fleet.get('ScriptId'),
                        }

                        resources.append({
                            'service': 'gamelift',
                            'type': 'fleet',
                            'id': fleet_id,
                            'arn': fleet_arn,
                            'name': fleet_name,
                            'region': region,
                            'details': details,
                            'tags': {}
                        })
                except Exception:
                    pass
    except Exception:
        pass

    # Aliases
    try:
        paginator = gamelift.get_paginator('list_aliases')
        for page in paginator.paginate():
            for alias in page.get('Aliases', []):
                alias_id = alias['AliasId']
                alias_arn = alias.get('AliasArn', f"arn:aws:gamelift:{region}:{account_id}:alias/{alias_id}")
                alias_name = alias.get('Name', alias_id)

                routing = alias.get('RoutingStrategy', {})
                details = {
                    'description': alias.get('Description'),
                    'routing_type': routing.get('Type'),
                    'routing_fleet_id': routing.get('FleetId'),
                }

                resources.append({
                    'service': 'gamelift',
                    'type': 'alias',
                    'id': alias_id,
                    'arn': alias_arn,
                    'name': alias_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Scripts
    try:
        paginator = gamelift.get_paginator('list_scripts')
        for page in paginator.paginate():
            for script in page.get('Scripts', []):
                script_id = script['ScriptId']
                script_arn = script.get('ScriptArn', f"arn:aws:gamelift:{region}:{account_id}:script/{script_id}")
                script_name = script.get('Name', script_id)

                details = {
                    'version': script.get('Version'),
                    'size_on_disk': script.get('SizeOnDisk'),
                }

                resources.append({
                    'service': 'gamelift',
                    'type': 'script',
                    'id': script_id,
                    'arn': script_arn,
                    'name': script_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Game Session Queues
    try:
        paginator = gamelift.get_paginator('describe_game_session_queues')
        for page in paginator.paginate():
            for queue in page.get('GameSessionQueues', []):
                queue_name = queue['Name']
                queue_arn = queue.get('GameSessionQueueArn', f"arn:aws:gamelift:{region}:{account_id}:gamesessionqueue/{queue_name}")

                details = {
                    'timeout_in_seconds': queue.get('TimeoutInSeconds'),
                    'destinations': [d.get('DestinationArn') for d in queue.get('Destinations', [])],
                }

                resources.append({
                    'service': 'gamelift',
                    'type': 'game-session-queue',
                    'id': queue_name,
                    'arn': queue_arn,
                    'name': queue_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Matchmaking Configurations
    try:
        paginator = gamelift.get_paginator('describe_matchmaking_configurations')
        for page in paginator.paginate():
            for config in page.get('Configurations', []):
                config_name = config['Name']
                config_arn = config.get('ConfigurationArn', f"arn:aws:gamelift:{region}:{account_id}:matchmakingconfiguration/{config_name}")

                details = {
                    'description': config.get('Description'),
                    'rule_set_name': config.get('RuleSetName'),
                    'acceptance_required': config.get('AcceptanceRequired'),
                    'acceptance_timeout_seconds': config.get('AcceptanceTimeoutSeconds'),
                    'flex_match_mode': config.get('FlexMatchMode'),
                }

                resources.append({
                    'service': 'gamelift',
                    'type': 'matchmaking-configuration',
                    'id': config_name,
                    'arn': config_arn,
                    'name': config_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Matchmaking Rule Sets
    try:
        paginator = gamelift.get_paginator('describe_matchmaking_rule_sets')
        for page in paginator.paginate():
            for ruleset in page.get('RuleSets', []):
                ruleset_name = ruleset['RuleSetName']
                ruleset_arn = ruleset.get('RuleSetArn', f"arn:aws:gamelift:{region}:{account_id}:matchmakingruleset/{ruleset_name}")

                details = {}

                resources.append({
                    'service': 'gamelift',
                    'type': 'matchmaking-rule-set',
                    'id': ruleset_name,
                    'arn': ruleset_arn,
                    'name': ruleset_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
