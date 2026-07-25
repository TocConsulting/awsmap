"""
AWS Lex V2 resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_lexv2_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Lex V2 resources: bots and bot aliases.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    lex = session.client('lexv2-models', region_name=region)

    # Bots
    try:
        paginator = lex.get_paginator('list_bots')
        for page in paginator.paginate():
            for bot in page.get('botSummaries', []):
                bot_id = bot['botId']
                bot_name = bot.get('botName', bot_id)

                details = {
                    'bot_status': bot.get('botStatus'),
                    'bot_type': bot.get('botType'),
                    'description': bot.get('description'),
                    'latest_bot_version': bot.get('latestBotVersion'),
                    'last_updated_date_time': str(bot.get('lastUpdatedDateTime', '')),
                }

                # Get bot details for more info
                try:
                    bot_info = lex.describe_bot(botId=bot_id)
                    details['data_privacy'] = bot_info.get('dataPrivacy', {}).get('childDirected')
                    details['idle_session_ttl_in_seconds'] = bot_info.get('idleSessionTTLInSeconds')
                    details['role_arn'] = bot_info.get('roleArn')
                    details['creation_date_time'] = str(bot_info.get('creationDateTime', ''))
                except Exception:
                    pass

                resources.append({
                    'service': 'lexv2',
                    'type': 'bot',
                    'id': bot_id,
                    'arn': f"arn:aws:lex:{region}:{account_id}:bot/{bot_id}",
                    'name': bot_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })

                # Bot Aliases for this bot
                try:
                    alias_paginator = lex.get_paginator('list_bot_aliases')
                    for alias_page in alias_paginator.paginate(botId=bot_id):
                        for alias in alias_page.get('botAliasSummaries', []):
                            alias_id = alias['botAliasId']
                            alias_name = alias.get('botAliasName', alias_id)

                            alias_details = {
                                'bot_id': bot_id,
                                'bot_alias_status': alias.get('botAliasStatus'),
                                'bot_version': alias.get('botVersion'),
                                'description': alias.get('description'),
                                'creation_date_time': str(alias.get('creationDateTime', '')),
                                'last_updated_date_time': str(alias.get('lastUpdatedDateTime', '')),
                            }

                            resources.append({
                                'service': 'lexv2',
                                'type': 'bot-alias',
                                'id': alias_id,
                                'arn': f"arn:aws:lex:{region}:{account_id}:bot-alias/{bot_id}/{alias_id}",
                                'name': alias_name,
                                'region': region,
                                'details': alias_details,
                                'tags': {}
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return resources
