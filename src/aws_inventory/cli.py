"""
Command-line interface for AWS Inventory Tool.
"""

import sys
import time
import click
from typing import Optional, List

from aws_inventory.auth import create_session, validate_credentials, get_account_alias
from aws_inventory.collector import collect_all, get_available_services, validate_services
from aws_inventory.formatter import format_output, export_file


def print_progress(service: str, status: str) -> None:
    """Print progress update for a service."""
    click.echo(f"  {service.upper():20} {status}")


@click.command()
@click.option('--profile', '-p', default=None, help='AWS profile name to use')
@click.option('--region', '-r', multiple=True, help='AWS region(s) to scan (can be specified multiple times)')
@click.option('--services', '-s', multiple=True, help='Service(s) to scan (can be specified multiple times)')
@click.option('--format', '-f', 'output_format', type=click.Choice(['json', 'csv', 'html']), default='html', help='Output format')
@click.option('--output', '-o', 'output_file', default=None, help='Output file path (auto-generated if not specified)')
@click.option('--workers', '-w', default=40, type=int, help='Maximum parallel workers (default: 40)')
@click.option('--list-services', is_flag=True, help='List available service collectors')
@click.option('--tag', '-t', multiple=True, help='Filter by tag (Key=Value format, can be specified multiple times)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
@click.option('--timings', is_flag=True, help='Show timing summary per service')
@click.option('--include-global', is_flag=True, help='Include global services even when filtering by non-global regions')
@click.option('--exclude-defaults', is_flag=True, help='Exclude default AWS resources (default VPCs, security groups, etc.)')
def main(
    profile: Optional[str],
    region: tuple,
    services: tuple,
    output_format: str,
    output_file: Optional[str],
    workers: int,
    list_services: bool,
    tag: tuple,
    quiet: bool,
    timings: bool,
    include_global: bool,
    exclude_defaults: bool
) -> None:
    """
    awsmap - Map and inventory AWS resources.

    Examples:

        # Scan all services in all regions (HTML output)
        awsmap

        # Scan specific services
        awsmap -s ec2 -s s3 -s rds

        # Scan specific regions
        awsmap -r us-east-1 -r eu-west-1

        # Use specific AWS profile
        awsmap -p production

        # Filter by tags
        awsmap -t Owner=Tarek -t Environment=Production

        # Output as JSON
        awsmap -f json -o inventory.json

        # List available collectors
        awsmap --list-services
    """
    # List services mode
    if list_services:
        services = get_available_services()
        click.echo(f"\nAvailable service collectors ({len(services)}):\n")
        for i, svc in enumerate(services, 1):
            click.echo(f"  {i:3}. {svc}")
        click.echo()
        return

    # Parse and validate services early (no AWS credentials needed)
    services_list: Optional[List[str]] = None
    if services:
        services_list = []
        for s in services:
            services_list.extend([x.strip() for x in s.split(',')])
        try:
            validate_services(services_list)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    # Create session
    try:
        session = create_session(profile_name=profile)
    except Exception as e:
        click.echo(f"Error creating session: {e}", err=True)
        sys.exit(1)

    # Validate credentials
    if not quiet:
        click.echo("\nValidating AWS credentials...")

    try:
        identity = validate_credentials(session)
        account_id = identity['account_id']
        account_alias = get_account_alias(session)

        if not quiet:
            click.echo(f"  Account ID: {account_id}")
            if account_alias:
                click.echo(f"  Account Alias: {account_alias}")
            click.echo(f"  User ARN: {identity['arn']}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Parse regions (support both -r us-east-1 -r eu-west-1 and -r us-east-1,eu-west-1)
    regions_list: Optional[List[str]] = None
    if region:
        regions_list = []
        for r in region:
            regions_list.extend([x.strip() for x in r.split(',')])

    # Run collection
    if not quiet:
        click.echo("\nCollecting resources...")
        click.echo("-" * 40)

    start_time = time.time()

    progress_callback = None if quiet else print_progress

    try:
        result = collect_all(
            session=session,
            services=services_list,
            regions=regions_list,
            max_workers=workers,
            progress_callback=progress_callback,
            show_timings=timings,
            include_global=include_global
        )
    except Exception as e:
        click.echo(f"Error during collection: {e}", err=True)
        sys.exit(1)

    elapsed = time.time() - start_time

    # Apply tag filters (same key = OR, different keys = AND)
    if tag:
        tag_filters = {}
        for t in tag:
            if '=' in t:
                key, value = t.split('=', 1)
                if key not in tag_filters:
                    tag_filters[key] = []
                tag_filters[key].append(value)

        if tag_filters:
            filtered_resources = []
            for resource in result['resources']:
                resource_tags = resource.get('tags', {})
                # All keys must match (AND), but values are OR within same key
                match = all(
                    resource_tags.get(k) in values
                    for k, values in tag_filters.items()
                )
                if match:
                    filtered_resources.append(resource)

            result['resources'] = filtered_resources
            result['metadata']['resource_count'] = len(filtered_resources)
            result['metadata']['tag_filter'] = tag_filters

    # Exclude default AWS resources
    if exclude_defaults:
        result['resources'] = [r for r in result['resources'] if not r.get('is_default')]
        result['metadata']['resource_count'] = len(result['resources'])
        result['metadata']['exclude_defaults'] = True

    # Summary
    if not quiet:
        click.echo("-" * 40)
        click.echo(f"\nCollection complete!")
        click.echo(f"  Resources found: {result['metadata']['resource_count']:,}")
        click.echo(f"  Services scanned: {result['metadata']['services_scanned']}")
        click.echo(f"  Regions scanned: {result['metadata']['regions_scanned']}")
        click.echo(f"  Duration: {elapsed:.1f}s")

    # Format output
    try:
        output_content = format_output(result, output_format)
    except Exception as e:
        click.echo(f"Error formatting output: {e}", err=True)
        sys.exit(1)

    # Determine output file path
    if not output_file:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        ext = output_format
        output_file = f"{account_id}_inventory_{timestamp}.{ext}"

    # Write output
    try:
        export_file(output_content, output_file)
        if not quiet:
            click.echo(f"\nOutput saved to: {output_file}")
    except Exception as e:
        click.echo(f"Error writing output: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
