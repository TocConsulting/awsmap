"""
Command-line interface for AWS Inventory Tool.
"""

import csv
import io
import json
import os
import sys
import time
import click
from click.shell_completion import get_completion_class
from typing import Optional, List

from aws_inventory import __version__
from aws_inventory.auth import create_session, validate_credentials, get_account_alias
from aws_inventory.collector import collect_all, get_available_services, validate_services
from aws_inventory.config import get_config, set_config, delete_config, list_config, validate_file, _VALID_KEYS
from aws_inventory.db import (get_connection, store_scan, get_accounts, resolve_account_id,
                               account_label, run_query, format_table)
from aws_inventory.examples import (list_services as examples_list_services,
                                     list_questions as examples_list_questions,
                                     resolve_service as examples_resolve_service,
                                     search as examples_search, total_count as examples_total)
from aws_inventory.completions import (complete_services, complete_regions, complete_profiles,
                                       complete_query_names, complete_accounts, complete_config_keys,
                                       complete_example_services, complete_example_numbers)
from aws_inventory.diff import (normalize_timestamp, reconstruct_snapshot,
                                reconstruct_current_snapshot, compute_diff,
                                build_summary, snapshot_metadata)
from aws_inventory.demo import generate_demo_db
from aws_inventory.diff_formatter import format_diff_table, format_diff_json, format_diff_html
from aws_inventory.formatter import format_output, export_file
from aws_inventory.nlq import generate_sql
from aws_inventory.queries_lib import list_named_queries, load_named_query, prepare_query, _parse_header


def print_progress(service: str, status: str) -> None:
    """Print progress update for a service."""
    click.echo(f"  {service.upper():20} {status}")


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name='awsmap')
@click.option('--profile', '-p', default=None, shell_complete=complete_profiles, help='AWS profile name to use')
@click.option('--region', '-r', multiple=True, shell_complete=complete_regions, help='AWS region(s) to scan (can be specified multiple times)')
@click.option('--services', '-s', multiple=True, shell_complete=complete_services, help='Service(s) to scan (can be specified multiple times)')
@click.option('--format', '-f', 'output_format', type=click.Choice(['json', 'csv', 'html']), default='html', help='Output format')
@click.option('--output', '-o', 'output_file', default=None, help='Output file path (auto-generated if not specified)')
@click.option('--workers', '-w', default=40, type=click.IntRange(min=1), help='Maximum parallel workers (default: 40)')
@click.option('--list-services', is_flag=True, help='List available service collectors')
@click.option('--tag', '-t', multiple=True, help='Filter by tag (Key=Value format, can be specified multiple times)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
@click.option('--timings', is_flag=True, help='Show timing summary per service')
@click.option('--include-global', is_flag=True, help='Include global services even when filtering by non-global regions')
@click.option('--exclude-defaults', is_flag=True, help='Exclude default AWS resources (default VPCs, security groups, etc.)')
@click.option('--no-db', is_flag=True, help='Skip local database storage')
@click.pass_context
def main(
    ctx,
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
    exclude_defaults: bool,
    no_db: bool
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

        # Query stored inventory
        awsmap query "SELECT service, COUNT(*) as count FROM resources GROUP BY service"

        # Ask in natural language
        awsmap ask show me all EC2 without Owner tag
    """
    ctx.ensure_object(dict)

    # If a subcommand is invoked, skip scan logic
    if ctx.invoked_subcommand is not None:
        return

    # Apply config defaults for options not explicitly provided
    src = ctx.get_parameter_source
    if profile is None and src('profile') != click.core.ParameterSource.COMMANDLINE:
        profile = get_config('profile')
    if not region and src('region') != click.core.ParameterSource.COMMANDLINE:
        cfg_regions = get_config('regions')
        if cfg_regions:
            region = tuple(r.strip() for r in cfg_regions.split(',') if r.strip())
    if not services and src('services') != click.core.ParameterSource.COMMANDLINE:
        cfg_services = get_config('services')
        if cfg_services:
            services = tuple(s.strip() for s in cfg_services.split(',') if s.strip())
    if src('output_format') != click.core.ParameterSource.COMMANDLINE:
        cfg_format = get_config('format')
        if cfg_format and cfg_format in ('json', 'csv', 'html'):
            output_format = cfg_format
    if src('workers') != click.core.ParameterSource.COMMANDLINE:
        cfg_workers = get_config('workers')
        if cfg_workers and cfg_workers.isdigit():
            workers = int(cfg_workers)
    if not exclude_defaults and src('exclude_defaults') != click.core.ParameterSource.COMMANDLINE:
        exclude_defaults = get_config('exclude_defaults', '').lower() in ('true', '1', 'yes')

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

    # Store in SQLite
    if not no_db:
        try:
            cfg_db = get_config('db')
            conn = get_connection(cfg_db)
            scan_id = store_scan(conn, result, profile=profile, account_alias=account_alias,
                                scanned_services=result['metadata'].get('services_scanned_list'))
            db_path = cfg_db or '~/.awsmap/inventory.db'
            conn.close()
            if not quiet:
                click.echo(f"  Stored in: {db_path} (scan: {scan_id})")
        except Exception as e:
            if not quiet:
                click.echo(f"  Warning: Failed to store in database: {e}")


@main.command()
@click.argument('sql', required=False, default=None)
@click.option('--name', '-n', 'query_name', default=None, shell_complete=complete_query_names, help='Run a pre-built named query')
@click.option('--file', '-F', 'query_file', default=None, type=click.Path(exists=True), help='Run SQL from a file')
@click.option('--list', '-l', 'list_queries', is_flag=True, help='List available pre-built queries')
@click.option('--show', '-S', 'show_name', default=None, shell_complete=complete_query_names, help='Show SQL of a named query without running it')
@click.option('--param', '-P', 'params', multiple=True, help='Parameter for named query (key=value)')
@click.option('--account', '-a', default=None, shell_complete=complete_accounts, help='Scope to an account (name, alias, or ID)')
@click.option('--db', default=None, help='Database path (default: ~/.awsmap/inventory.db)')
@click.option('--format', '-f', 'fmt', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
def query(sql, query_name, query_file, list_queries, show_name, params, account, db, fmt):
    """Run SQL query against the local inventory database.

    Three ways to query:

    \b
      awsmap query "SELECT ..."          Raw SQL
      awsmap query -n admin-users        Pre-built named query
      awsmap query -F my-query.sql       SQL from a file

    \b
    Named queries accept parameters:
      awsmap query -n resources-by-tag -P tag=Owner
      awsmap query -n missing-tag -P tag=Environment -P service=ec2

    \b
    List and inspect:
      awsmap query --list                List all pre-built queries
      awsmap query --show admin-users    Show the SQL without running
    """
    # Apply config defaults
    if db is None:
        db = get_config('db')
    ctx = click.get_current_context()
    if ctx.get_parameter_source('fmt') != click.core.ParameterSource.COMMANDLINE:
        cfg_fmt = get_config('query_format')
        if cfg_fmt and cfg_fmt in ('table', 'json', 'csv'):
            fmt = cfg_fmt

    # --list: show available queries and exit
    if list_queries:
        queries = list_named_queries()
        if not queries:
            click.echo("No pre-built queries found.", err=True)
            sys.exit(1)
        name_width = max(len(q[0]) for q in queries)
        click.echo(f"{'Name':<{name_width}}  {'Params':<25}  Description")
        click.echo(f"{'-' * name_width}  {'-' * 25}  {'-' * 40}")
        for name, description, q_params in queries:
            param_str = ', '.join(q_params) if q_params else '-'
            click.echo(f"{name:<{name_width}}  {param_str:<25}  {description}")
        click.echo(f"\n({len(queries)} queries)")
        return

    # --show: display SQL of named query and exit
    if show_name:
        try:
            raw_sql, meta = load_named_query(show_name)
        except FileNotFoundError:
            click.echo(f"Error: Unknown query '{show_name}'. Use --list to see available queries.", err=True)
            sys.exit(1)
        click.echo(f"-- {meta.get('name', show_name)}: {meta.get('description', '')}")
        if meta.get('params'):
            click.echo(f"-- params: {', '.join(meta['params'])}")
        click.echo()
        click.echo(raw_sql)
        return

    # Determine SQL source
    if query_name:
        try:
            raw_sql, meta = load_named_query(query_name)
        except FileNotFoundError:
            click.echo(f"Error: Unknown query '{query_name}'. Use --list to see available queries.", err=True)
            sys.exit(1)
        # Parse --param flags
        param_dict = {}
        for p in params:
            if '=' in p:
                k, v = p.split('=', 1)
                param_dict[k] = v
            else:
                click.echo(f"Error: Invalid param '{p}'. Use key=value format.", err=True)
                sys.exit(1)
        # Resolve account
        account_id = None
        if account:
            try:
                conn_tmp = get_connection(db)
                account_id = resolve_account_id(conn_tmp, account)
                conn_tmp.close()
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
        elif 'account' in param_dict:
            try:
                conn_tmp = get_connection(db)
                account_id = resolve_account_id(conn_tmp, param_dict.pop('account'))
                conn_tmp.close()
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
        sql = prepare_query(raw_sql, meta, account_id=account_id, params=param_dict)
    elif query_file:
        with open(query_file) as f:
            text = f.read()
        meta = _parse_header(text)
        # Strip header comments to get raw SQL
        lines = []
        past_header = False
        for line in text.splitlines():
            if not past_header and line.strip().startswith("--"):
                continue
            past_header = True
            lines.append(line)
        raw_sql = "\n".join(lines).strip()
        # Parse --param flags
        param_dict = {}
        for p in params:
            if '=' in p:
                k, v = p.split('=', 1)
                param_dict[k] = v
            else:
                click.echo(f"Error: Invalid param '{p}'. Use key=value format.", err=True)
                sys.exit(1)
        # Resolve account
        account_id = None
        if account:
            try:
                conn_tmp = get_connection(db)
                account_id = resolve_account_id(conn_tmp, account)
                conn_tmp.close()
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
        sql = prepare_query(raw_sql, meta, account_id=account_id, params=param_dict)
    elif sql is None:
        click.echo("Error: Provide SQL, --name, or --file. Use --list to see pre-built queries.", err=True)
        sys.exit(1)

    try:
        conn = get_connection(db)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    try:
        columns, rows = run_query(conn, sql)
    except Exception as e:
        click.echo(f"Query error: {e}", err=True)
        conn.close()
        sys.exit(1)

    if fmt == 'table':
        click.echo(format_table(columns, rows))
    elif fmt == 'json':
        click.echo(json.dumps([dict(zip(columns, r)) for r in rows], indent=2, default=str))
    elif fmt == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        click.echo(output.getvalue().rstrip())

    click.echo(f"\n({len(rows)} rows)")
    conn.close()


@main.command()
@click.argument('question', nargs=-1, required=True)
@click.option('--account', '-a', default=None, shell_complete=complete_accounts, help='Scope to an account (name, alias, profile, or ID)')
@click.option('--db', default=None, help='Database path (default: ~/.awsmap/inventory.db)')
def ask(question, account, db):
    """Ask a question about your inventory in natural language.

    Examples:

        awsmap ask show me S3 buckets

        awsmap ask -a prod how many resources per region

        awsmap ask -a 123456789012 show me Lambda functions
    """
    # Apply config defaults
    if db is None:
        db = get_config('db')

    question_str = ' '.join(question)

    try:
        conn = get_connection(db)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    accounts = get_accounts(conn)
    if not accounts:
        click.echo("No scans found. Run 'awsmap' first.", err=True)
        conn.close()
        sys.exit(1)

    # Resolve account scope
    account_id = None
    if account:
        account_id = resolve_account_id(conn, account)
        if not account_id:
            click.echo(f"Error: '{account}' not found. Available accounts:", err=True)
            for acct_id, alias, prof in accounts:
                label = alias or prof or acct_id
                click.echo(f"  {label} [{acct_id}]", err=True)
            conn.close()
            sys.exit(1)

    # Show account scope
    if account_id:
        click.echo(f"  Account: {account_label(conn, account_id)} [{account_id}]")
    else:
        labels = [f"{account_label(conn, a[0])} [{a[0]}]" for a in accounts]
        click.echo(f"  Accounts: {', '.join(labels)}")

    try:
        sql = generate_sql(question_str, conn=conn, account_id=account_id)
    except Exception as e:
        click.echo(f"Error generating SQL: {e}", err=True)
        conn.close()
        sys.exit(1)

    click.echo(f"\n  SQL: {sql}\n")

    try:
        columns, rows = run_query(conn, sql)
        click.echo(format_table(columns, rows))
        click.echo(f"\n({len(rows)} rows)")
    except Exception as e:
        click.echo(f"Query error: {e}", err=True)
        click.echo("The generated SQL may be invalid. Try rephrasing your question.")
    finally:
        conn.close()


@main.command()
@click.argument('service', required=False, default=None, shell_complete=complete_example_services)
@click.argument('number', required=False, default=None, type=int, shell_complete=complete_example_numbers)
@click.option('--search', '-s', 'search_term', default=None, help='Search examples by keyword')
@click.option('--db', default=None, help='Database path (default: ~/.awsmap/inventory.db)')
def examples(service, number, search_term, db):
    """Browse and run pre-built question examples.

    \b
      awsmap examples                  List services with question counts
      awsmap examples lambda           List Lambda questions
      awsmap examples lambda 5         Run question #5
      awsmap examples --search public  Search all questions
    """
    # Apply config default for db
    if db is None:
        db = get_config('db')

    # Search mode
    if search_term:
        results = examples_search(search_term)
        if not results:
            click.echo(f"No examples matching '{search_term}'.")
            return
        click.echo(f"\n  Found {len(results)} examples matching '{search_term}':\n")
        for i, (svc, q) in enumerate(results, 1):
            click.echo(f"  {i:4}. [{svc}] {q}")
        click.echo()
        return

    # No service → list all services
    if service is None:
        services = examples_list_services()
        total = examples_total()
        click.echo(f"\n  {total} examples across {len(services)} services:\n")
        for svc_key, display, count in services:
            click.echo(f"  {svc_key:<25} {display:<25} ({count})")
        click.echo(f"\n  Usage: awsmap examples <service>")
        click.echo(f"         awsmap examples --search <keyword>\n")
        return

    # Resolve service name
    svc_key = examples_resolve_service(service)
    if svc_key is None:
        click.echo(f"Error: Unknown service '{service}'.", err=True)
        click.echo("Run 'awsmap examples' to see available services.", err=True)
        sys.exit(1)

    questions = examples_list_questions(svc_key)

    # No number → list questions for this service
    if number is None:
        click.echo(f"\n  {svc_key} ({len(questions)} examples):\n")
        for i, q in enumerate(questions, 1):
            click.echo(f"  {i:4}. {q}")
        click.echo(f"\n  Usage: awsmap examples {svc_key} <number>\n")
        return

    # Number given → run that question
    if number < 1 or number > len(questions):
        click.echo(f"Error: Choose a number between 1 and {len(questions)}.", err=True)
        sys.exit(1)

    question_str = questions[number - 1]
    click.echo(f"\n  Question: {question_str}\n")

    try:
        conn = get_connection(db)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    try:
        sql = generate_sql(question_str, conn=conn)
    except Exception as e:
        click.echo(f"Error generating SQL: {e}", err=True)
        conn.close()
        sys.exit(1)

    click.echo(f"  SQL: {sql}\n")

    try:
        columns, rows = run_query(conn, sql)
        click.echo(format_table(columns, rows))
        click.echo(f"\n({len(rows)} rows)")
    except Exception as e:
        click.echo(f"Query error: {e}", err=True)
    finally:
        conn.close()


@main.command()
@click.option('--from', 'from_date', default=None,
              help='Start date (YYYY-MM-DD, datetime, or relative: 7d, 30d, yesterday)')
@click.option('--to', 'to_date', default=None,
              help='End date (default: current state)')
@click.option('--account', '-a', default=None, shell_complete=complete_accounts,
              help='Scope to an account (name, alias, or ID)')
@click.option('--service', '-s', 'services', multiple=True, shell_complete=complete_services,
              help='Filter to service(s)')
@click.option('--region', '-r', 'regions', multiple=True, shell_complete=complete_regions,
              help='Filter to region(s)')
@click.option('--type', 'change_type', type=click.Choice(['all', 'added', 'removed', 'modified']),
              default='all', help='Show only specific change types')
@click.option('--format', '-f', 'fmt', type=click.Choice(['table', 'json', 'html']),
              default='table', help='Output format')
@click.option('--output', '-o', 'output_file', default=None, help='Output file path')
@click.option('--summary', is_flag=True, help='Show summary counts only')
@click.option('--ignore-tags', is_flag=True, help='Exclude tag changes from modification detection')
@click.option('--db', default=None, help='Database path (default: ~/.awsmap/inventory.db)')
def diff(from_date, to_date, account, services, regions, change_type, fmt, output_file,
         summary, ignore_tags, db):
    """Compare resource snapshots to detect drift.

    \b
    Examples:
      awsmap diff --from 2026-01-15 --to 2026-02-09
      awsmap diff --from 30d
      awsmap diff --from 2026-01-15 -s ec2 -r us-east-1
      awsmap diff --from 2026-01-15 --summary
      awsmap diff --from 2026-01-15 -f html -o drift.html
      awsmap diff --from 7d --type removed
    """
    if db is None:
        db = get_config('db')

    if not from_date:
        click.echo("Error: --from is required. Example: awsmap diff --from 30d", err=True)
        sys.exit(1)

    # Parse services (support comma-separated)
    services_list = None
    if services:
        services_list = []
        for s in services:
            services_list.extend([x.strip() for x in s.split(',')])

    # Parse regions
    regions_list = None
    if regions:
        regions_list = []
        for r in regions:
            regions_list.extend([x.strip() for x in r.split(',')])

    # Open database
    try:
        conn = get_connection(db)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    # Resolve account
    account_id = None
    if account:
        account_id = resolve_account_id(conn, account)
        if not account_id:
            accounts = get_accounts(conn)
            click.echo(f"Error: '{account}' not found. Available accounts:", err=True)
            for acct_id, alias, prof in accounts:
                label = alias or prof or acct_id
                click.echo(f"  {label} [{acct_id}]", err=True)
            conn.close()
            sys.exit(1)

    # Normalize timestamps
    try:
        from_ts = normalize_timestamp(from_date)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        conn.close()
        sys.exit(1)

    # Build FROM snapshot
    from_snapshot = reconstruct_snapshot(conn, from_ts,
                                        account_id=account_id,
                                        services=services_list,
                                        regions=regions_list)
    if not from_snapshot:
        click.echo(f"Warning: No scan data found before {from_date}. "
                   f"The 'from' snapshot is empty — all resources will appear as added.", err=True)

    # Build TO snapshot
    if to_date:
        try:
            to_ts = normalize_timestamp(to_date)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            conn.close()
            sys.exit(1)
        to_snapshot = reconstruct_snapshot(conn, to_ts,
                                          account_id=account_id,
                                          services=services_list,
                                          regions=regions_list)
        if not to_snapshot and not from_snapshot:
            click.echo(f"Error: No scan data found before {to_date}. Cannot compute diff.", err=True)
            conn.close()
            sys.exit(1)
    else:
        to_ts = None
        to_snapshot = reconstruct_current_snapshot(conn,
                                                   account_id=account_id,
                                                   services=services_list,
                                                   regions=regions_list)

    # Check if both snapshots resolve to the same data
    from_scan_ids = {r.get('scan_id') for r in from_snapshot.values()}
    to_scan_ids = {r.get('scan_id') for r in to_snapshot.values()}
    if from_snapshot and to_snapshot and from_scan_ids == to_scan_ids:
        click.echo("\nBoth snapshots resolve to the same data. No drift detected.")
        conn.close()
        return

    # Compute diff
    diff_result = compute_diff(from_snapshot, to_snapshot, ignore_tags=ignore_tags)
    diff_result['_summary'] = build_summary(diff_result)

    # Build metadata for formatters
    from_meta = snapshot_metadata(conn, from_ts, account_id=account_id,
                                  services=services_list, regions=regions_list)
    to_meta = snapshot_metadata(conn, to_ts, account_id=account_id,
                                services=services_list, regions=regions_list) if to_ts else {
        'service_count': len({r.get('service') for r in to_snapshot.values()}),
        'latest_scan': 'current',
        'services': sorted(s for s in {r.get('service') for r in to_snapshot.values()} if s),
    }

    acct_label = ''
    acct_labels_map = {}
    if account_id:
        acct_label = f"{account_label(conn, account_id)} [{account_id}]"
        acct_labels_map[account_id] = account_label(conn, account_id)
    else:
        accounts = get_accounts(conn)
        if accounts:
            labels = [f"{account_label(conn, a[0])} [{a[0]}]" for a in accounts]
            acct_label = ', '.join(labels)
            for a in accounts:
                acct_labels_map[a[0]] = account_label(conn, a[0])

    meta = {
        'from_date': from_date,
        'to_date': to_date or 'current',
        'account_id': account_id,
        'account_alias': acct_label,
        'account_label': acct_label,
        'account_labels': acct_labels_map,
        'services_compared': from_meta.get('service_count', 0),
        'from_info': f"{from_meta.get('service_count', 0)} services, "
                     f"latest scan: {from_meta.get('latest_scan', 'none')}",
        'to_info': f"{to_meta.get('service_count', 0)} services, "
                   f"latest scan: {to_meta.get('latest_scan', 'none')}",
        'from_snapshot': from_meta,
        'to_snapshot': to_meta,
    }

    conn.close()

    # Auto-detect format from file extension when not explicitly set
    if output_file and fmt == 'table':
        if output_file.endswith('.html') or output_file.endswith('.htm'):
            fmt = 'html'
        elif output_file.endswith('.json'):
            fmt = 'json'

    # Format output
    if fmt == 'table':
        output = format_diff_table(diff_result, meta,
                                   summary_only=summary,
                                   change_type=change_type)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            click.echo(f"Drift report saved to: {output_file}")
        else:
            click.echo(output)
    elif fmt == 'json':
        output = format_diff_json(diff_result, meta, change_type=change_type)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            click.echo(f"Drift report saved to: {output_file}")
        else:
            click.echo(output)
    elif fmt == 'html':
        output = format_diff_html(diff_result, meta, change_type=change_type)
        if not output_file:
            safe_from = from_date.replace(':', '-').replace(' ', '_')
            safe_to = (to_date or 'current').replace(':', '-').replace(' ', '_')
            output_file = f"drift_{safe_from}_to_{safe_to}.html"
        with open(output_file, 'w') as f:
            f.write(output)
        click.echo(f"Drift report saved to: {output_file}")


@main.group(invoke_without_command=True)
@click.pass_context
def config(ctx):
    """Manage awsmap configuration (~/.awsmap/config).

    \b
    Valid keys:
      profile           AWS profile name
      regions           Comma-separated regions
      services          Comma-separated services
      format            html | json | csv
      workers           Positive integer
      exclude_defaults  true | false
      db                Database file path
      query_format      table | json | csv

    \b
    Examples:
      awsmap config set profile production
      awsmap config set regions us-east-1,eu-west-1
      awsmap config get profile
      awsmap config list
      awsmap config delete profile
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(config_list)


@config.command('set')
@click.argument('key', shell_complete=complete_config_keys)
@click.argument('value')
def config_set(key, value):
    """Set a configuration value."""
    try:
        set_config(key, value)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"  {key}={value}")


@config.command('get')
@click.argument('key', shell_complete=complete_config_keys)
def config_get(key):
    """Get a configuration value."""
    value = get_config(key)
    if value is None:
        click.echo(f"  {key} is not set")
    else:
        click.echo(f"  {key}={value}")


@config.command('list')
def config_list():
    """List all configuration values."""
    # Check for corrupt/invalid entries and auto-clean
    errors = validate_file()
    if errors:
        click.echo("  Warning: invalid entries found in config file (auto-cleaned):", err=True)
        for line_num, error in errors:
            click.echo(f"    Line {line_num}: {error}", err=True)
        click.echo()

    cfg = list_config()
    if not cfg:
        click.echo("  No configuration set.\n")
        click.echo("  Valid keys:")
        for k in sorted(_VALID_KEYS):
            allowed = _VALID_KEYS[k]
            if allowed is None:
                hint = "<value>"
            elif allowed == "integer":
                hint = "<number>"
            else:
                hint = " | ".join(allowed)
            click.echo(f"    {k:<20} {hint}")
        click.echo(f"\n  Usage: awsmap config set <key> <value>")
        return
    for k in sorted(cfg):
        click.echo(f"  {k}={cfg[k]}")


@config.command('delete')
@click.argument('key', shell_complete=complete_config_keys)
def config_delete(key):
    """Delete a configuration value."""
    if get_config(key) is None:
        click.echo(f"  {key} is not set")
    else:
        delete_config(key)
        click.echo(f"  Deleted {key}")


@main.command()
@click.argument('shell', type=click.Choice(['bash', 'zsh', 'fish']))
def completion(shell):
    """Generate shell completion script.

    \b
    Activate for your shell:
      eval "$(awsmap completion bash)"     # add to ~/.bashrc
      eval "$(awsmap completion zsh)"      # add to ~/.zshrc
      awsmap completion fish > ~/.config/fish/completions/awsmap.fish
    """
    comp_cls = get_completion_class(shell)
    comp = comp_cls(main, {}, "awsmap", "_AWSMAP_COMPLETE")
    click.echo(comp.source())


@main.command()
@click.option('--db', default=None, help='Database path (default: ~/.awsmap/demo.db)')
@click.option('--accounts', default=3, type=click.IntRange(1, 5), help='Number of accounts (default: 3)')
@click.option('--scans', default=3, type=click.IntRange(1, 5), help='Number of scans for drift (default: 3)')
@click.option('--seed', default=42, type=int, help='Random seed for reproducibility (default: 42)')
@click.option('--force', is_flag=True, help='Overwrite existing demo database')
def demo(db, accounts, scans, seed, force):
    """Generate a demo database with synthetic AWS inventory data.

    Creates a realistic database covering all 150+ services, multiple accounts,
    and multiple scans — so you can try query, ask, examples, and diff without
    needing an AWS account.

    \b
    Examples:
      awsmap demo                           Generate with defaults
      awsmap demo --db ./demo.db            Custom path
      awsmap demo --accounts 2 --scans 5    2 accounts, 5 scans each
      awsmap demo --force                   Overwrite existing

    \b
    After generating, try:
      awsmap query --db ~/.awsmap/demo.db -n admin-users
      awsmap ask --db ~/.awsmap/demo.db show me all EC2 instances
      awsmap diff --db ~/.awsmap/demo.db --from 30d
      awsmap examples lambda 5 --db ~/.awsmap/demo.db
    """
    if db is None:
        db = os.path.expanduser("~/.awsmap/demo.db")

    if os.path.exists(db) and not force:
        click.echo(f"Error: {db} already exists. Use --force to overwrite.", err=True)
        sys.exit(1)

    if os.path.exists(db) and force:
        os.remove(db)

    click.echo(f"\nGenerating demo database...")
    click.echo(f"  Path: {db}")
    click.echo(f"  Accounts: {accounts}")
    click.echo(f"  Scans per account: {scans}")
    click.echo(f"  Seed: {seed}")
    click.echo()

    def progress(msg):
        click.echo(f"  {msg}")

    try:
        stats = generate_demo_db(db, n_accounts=accounts, n_scans=scans,
                                 seed=seed, progress=progress)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)

    click.echo(f"\nDone! Generated {stats['total_resource_rows']:,} resource rows "
               f"across {stats['scans']} scans.")
    click.echo(f"  Services covered: {stats['services_covered']}")
    click.echo(f"  Database: {stats['db_path']}")
    click.echo(f"\nTry it:")
    click.echo(f"  awsmap query --db {db} -n admin-users")
    click.echo(f"  awsmap ask --db {db} show me all EC2 instances")
    click.echo(f"  awsmap diff --db {db} --from 30d")
    click.echo(f"  awsmap examples lambda 5 --db {db}")
    click.echo(f"\nOr set it as default:")
    click.echo(f"  awsmap config set db {db}")
    click.echo()


if __name__ == '__main__':
    main()
