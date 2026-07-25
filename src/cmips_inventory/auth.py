"""
AWS authentication and session management.
"""

import boto3
import botocore.exceptions
from typing import Optional, Dict, Any, List


def create_session(profile_name: Optional[str] = None, region: Optional[str] = None) -> boto3.Session:
    """
    Create a boto3 session with optional profile and region.

    Args:
        profile_name: AWS profile name to use
        region: AWS region to use

    Returns:
        boto3.Session configured with the specified credentials
    """
    kwargs = {}
    if profile_name:
        kwargs['profile_name'] = profile_name
    if region:
        kwargs['region_name'] = region

    return boto3.Session(**kwargs)


def validate_credentials(session: boto3.Session) -> Dict[str, Any]:
    """
    Validate AWS credentials and return caller identity.

    Args:
        session: boto3.Session to validate

    Returns:
        Dict with account_id, user_id, and arn

    Raises:
        ValueError: If credentials are invalid
    """
    try:
        sts_client = session.client('sts')
        identity = sts_client.get_caller_identity()
        return {
            'account_id': identity['Account'],
            'user_id': identity['UserId'],
            'arn': identity['Arn']
        }
    except botocore.exceptions.NoCredentialsError:
        raise ValueError("No AWS credentials found")
    except botocore.exceptions.ClientError as e:
        raise ValueError(f"Invalid AWS credentials: {e}")


def get_account_id(session: boto3.Session) -> str:
    """
    Get the AWS account ID for the current session.

    Args:
        session: boto3.Session to use

    Returns:
        AWS account ID as string
    """
    sts_client = session.client('sts')
    return sts_client.get_caller_identity()['Account']


def get_enabled_regions(session: boto3.Session) -> List[str]:
    """
    Get list of enabled AWS regions for the account.

    Args:
        session: boto3.Session to use

    Returns:
        List of enabled region names
    """
    try:
        account = session.client('account', region_name='us-east-1')
        paginator = account.get_paginator('list_regions')

        regions = []
        for page in paginator.paginate(
            RegionOptStatusContains=['ENABLED', 'ENABLED_BY_DEFAULT']
        ):
            for region in page.get('Regions', []):
                regions.append(region['RegionName'])

        return sorted(regions)
    except Exception:
        # Fallback to common regions if list_regions fails
        return [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1', 'eu-north-1',
            'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
            'ap-southeast-1', 'ap-southeast-2', 'ap-south-1',
            'sa-east-1', 'ca-central-1'
        ]


def get_account_alias(session: boto3.Session) -> Optional[str]:
    """
    Get the AWS account alias if set.

    Args:
        session: boto3.Session to use

    Returns:
        Account alias or None if not set
    """
    try:
        iam_client = session.client('iam')
        response = iam_client.list_account_aliases()
        aliases = response.get('AccountAliases', [])
        return aliases[0] if aliases else None
    except Exception:
        return None
