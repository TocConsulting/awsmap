"""
AWS Service Catalog resource collector.
"""

import boto3  # noqa: F401
from typing import List, Dict, Any, Optional


def collect_servicecatalog_resources(session: boto3.Session, region: Optional[str], account_id: str) -> List[Dict[str, Any]]:
    """
    Collect AWS Service Catalog resources: portfolios and products.

    Args:
        session: boto3.Session to use
        region: AWS region
        account_id: AWS account ID

    Returns:
        List of resource dictionaries
    """
    resources = []
    sc = session.client('servicecatalog', region_name=region)

    # Portfolios
    try:
        paginator = sc.get_paginator('list_portfolios')
        for page in paginator.paginate():
            for portfolio in page.get('PortfolioDetails', []):
                portfolio_id = portfolio['Id']
                portfolio_arn = portfolio.get('ARN', f"arn:aws:catalog:{region}:{account_id}:portfolio/{portfolio_id}")
                portfolio_name = portfolio.get('DisplayName', portfolio_id)

                details = {
                    'description': portfolio.get('Description'),
                    'provider_name': portfolio.get('ProviderName'),
                }

                resources.append({
                    'service': 'servicecatalog',
                    'type': 'portfolio',
                    'id': portfolio_id,
                    'arn': portfolio_arn,
                    'name': portfolio_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    # Products (as admin)
    try:
        paginator = sc.get_paginator('search_products_as_admin')
        for page in paginator.paginate():
            for product_detail in page.get('ProductViewDetails', []):
                product_arn = product_detail.get('ProductARN', '')
                status = product_detail.get('Status')

                summary = product_detail.get('ProductViewSummary', {})
                product_id = summary.get('ProductId', '')
                product_name = summary.get('Name', product_id)

                details = {
                    'status': status,
                    'type': summary.get('Type'),
                    'owner': summary.get('Owner'),
                    'short_description': summary.get('ShortDescription'),
                    'distributor': summary.get('Distributor'),
                    'has_default_path': summary.get('HasDefaultPath'),
                    'support_email': summary.get('SupportEmail'),
                }

                resources.append({
                    'service': 'servicecatalog',
                    'type': 'product',
                    'id': product_id,
                    'arn': product_arn,
                    'name': product_name,
                    'region': region,
                    'details': details,
                    'tags': {}
                })
    except Exception:
        pass

    return resources
