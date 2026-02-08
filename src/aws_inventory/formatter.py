"""
Output formatters for inventory results - JSON, CSV, HTML.
"""

import json
import csv
import io
from typing import Dict, Any, List


def format_json(data: Dict[str, Any]) -> str:
    """
    Format inventory data as JSON.

    Args:
        data: Inventory data with metadata and resources

    Returns:
        JSON string
    """
    return json.dumps(data, indent=2, default=str)


def format_csv(data: Dict[str, Any]) -> str:
    """
    Format inventory data as CSV.

    Args:
        data: Inventory data with metadata and resources

    Returns:
        CSV string
    """
    resources = data.get('resources', [])

    if not resources:
        return "service,type,id,name,region,arn,tags\n"

    output = io.StringIO()
    fieldnames = ['service', 'type', 'id', 'name', 'region', 'arn', 'tags']
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()

    for resource in resources:
        tags = resource.get('tags', {})
        tags_str = '; '.join(f"{k}={v}" for k, v in tags.items()) if tags else ''

        writer.writerow({
            'service': resource.get('service', ''),
            'type': resource.get('type', ''),
            'id': resource.get('id', ''),
            'name': resource.get('name', ''),
            'region': resource.get('region', ''),
            'arn': resource.get('arn', ''),
            'tags': tags_str
        })

    return output.getvalue()


def format_html(data: Dict[str, Any]) -> str:
    """
    Format inventory data as beautiful HTML report.

    Args:
        data: Inventory data with metadata and resources

    Returns:
        HTML string
    """
    resources = data.get('resources', [])
    metadata = data.get('metadata', {})

    account_id = metadata.get('account_id', 'Unknown')
    timestamp = metadata.get('timestamp', '')
    duration = metadata.get('scan_duration_seconds', 0)
    total_resources = len(resources)

    # Group by service
    services = {}
    for r in resources:
        svc = r.get('service', 'unknown')
        if svc not in services:
            services[svc] = []
        services[svc].append(r)

    # Group by region
    regions = {}
    for r in resources:
        reg = r.get('region', 'global') or 'global'
        if reg not in regions:
            regions[reg] = 0
        regions[reg] += 1

    # Collect all unique tags
    all_tags = {}
    for r in resources:
        tags = r.get('tags', {})
        for k, v in tags.items():
            if k not in all_tags:
                all_tags[k] = set()
            all_tags[k].add(v)

    # Count resource types
    resource_types = {}
    for r in resources:
        rt = f"{r.get('service', '')}/{r.get('type', '')}"
        resource_types[rt] = resource_types.get(rt, 0) + 1

    # Escape function
    def esc(s):
        if s is None:
            return ''
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    # Build service options
    service_options = '\n'.join(
        f'<option value="{esc(s)}">{esc(s.upper())}</option>'
        for s in sorted(services.keys())
    )

    # Build region options
    region_options = '\n'.join(
        f'<option value="{esc(r)}">{esc(r)}</option>'
        for r in sorted(regions.keys())
    )

    # Build tag options (Key=Value format)
    tag_options = []
    for k in sorted(all_tags.keys()):
        for v in sorted(all_tags[k]):
            tag_options.append(f'<option value="{esc(k)}={esc(v)}">{esc(k)}={esc(v)}</option>')
    tag_options_html = '\n'.join(tag_options)

    # Detail value formatter
    def format_detail_value(value):
        if value is None:
            return '<span class="detail-value null-value">&mdash;</span>'
        if isinstance(value, bool):
            cls = 'bool-true' if value else 'bool-false'
            text = 'Yes' if value else 'No'
            return f'<span class="detail-value {cls}">{text}</span>'
        if isinstance(value, list):
            if not value:
                return '<span class="detail-value null-value">&mdash;</span>'
            items = ''.join(f'<span class="detail-list-item">{esc(str(item))}</span>' for item in value)
            return f'<span class="detail-value"><span class="detail-list">{items}</span></span>'
        if isinstance(value, dict):
            return f'<span class="detail-value">{esc(json.dumps(value, default=str))}</span>'
        return f'<span class="detail-value">{esc(str(value))}</span>'

    # Detail key formatter: snake_case -> Title Case
    def format_detail_key(key):
        return key.replace('_', ' ').title()

    # Build service sections
    num_columns = 5  # Type, Name, ID/ARN, Region, Tags
    service_sections = []
    for service_name in sorted(services.keys()):
        service_resources = services[service_name]
        count = len(service_resources)

        rows = []
        for r in service_resources:
            tags = r.get('tags', {})
            tag_badges = ''
            all_tags_html = ''
            if tags:
                for k, v in list(tags.items())[:3]:
                    tag_badges += f'<span class="tag">{esc(k)}={esc(v)}</span>'
                if len(tags) > 3:
                    tag_badges += f'<span class="tag more" onclick="toggleTags(this)">+{len(tags)-3}</span>'
                    all_tags_html = '<div class="tags-tooltip">'
                    for k, v in tags.items():
                        all_tags_html += f'<span class="tag">{esc(k)}={esc(v)}</span>'
                    all_tags_html += '</div>'

            # Build tags data attribute for filtering
            tags_data = '|'.join(f"{esc(k)}={esc(v)}" for k, v in tags.items()) if tags else ''
            region_val = r.get('region', 'global') or 'global'

            details = r.get('details', {})
            has_details = bool(details)

            # Main resource row
            detail_attrs = ''
            if has_details:
                detail_text = ' '.join(str(v) for v in details.values()).lower()
                detail_text = ''.join(c if c >= ' ' else ' ' for c in detail_text)
                detail_attrs = f' data-has-details="true" data-details="{esc(detail_text)}" onclick="toggleDetails(this)"'

            rows.append(f'''
                <tr data-service="{esc(service_name)}" data-region="{esc(region_val)}" data-name="{esc(str(r.get('name', '')).lower())}" data-id="{esc(str(r.get('id', '')).lower())}" data-tags="{tags_data}"{detail_attrs}>
                    <td>{esc(r.get('type', ''))}</td>
                    <td>{esc(r.get('name', '') or r.get('id', ''))}</td>
                    <td class="resource-id" title="Click to copy ARN" onclick="event.stopPropagation(); copyToClipboard(this)">{esc(r.get('arn', '') or r.get('id', ''))}</td>
                    <td><span class="region-badge" data-region="{esc(region_val)}">{esc(region_val)}</span></td>
                    <td class="tags-cell">{tag_badges}{all_tags_html}</td>
                </tr>
            ''')

            # Detail row (hidden by default)
            if has_details:
                detail_items = ''.join(
                    f'<div class="detail-item"><span class="detail-key">{esc(format_detail_key(k))}</span>{format_detail_value(v)}</div>'
                    for k, v in details.items()
                )
                rows.append(f'''
                <tr class="details-row collapsed">
                    <td colspan="{num_columns}">
                        <div class="details-panel">
                            <div class="details-grid">{detail_items}</div>
                        </div>
                    </td>
                </tr>
            ''')

        service_sections.append(f'''
            <div class="service-section" data-service="{esc(service_name)}">
                <div class="service-header" onclick="toggleSection(this)">
                    <span class="service-name">{esc(service_name.upper())}</span>
                    <span class="service-count">{count} resource{'s' if count != 1 else ''}</span>
                    <span class="toggle-icon">+</span>
                </div>
                <div class="service-content collapsed">
                    <table>
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Name</th>
                                <th>ID / ARN</th>
                                <th>Region</th>
                                <th>Tags</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        ''')

    # Build stats cards
    top_services = sorted(services.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    service_stats = ''.join(
        f'<div class="stat-bar"><span class="stat-label">{esc(s.upper())}</span><div class="bar" style="width: {min(100, len(r)*100//max(1,total_resources))}%"></div><span class="stat-value">{len(r)}</span></div>'
        for s, r in top_services
    )

    # Build region stats
    top_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)[:5]
    region_stats = ''.join(
        f'<div class="stat-bar"><span class="stat-label">{esc(reg)}</span><div class="bar region-bar" style="width: {min(100, count*100//max(1,total_resources))}%"></div><span class="stat-value">{count}</span></div>'
        for reg, count in top_regions
    )

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>awsmap - {esc(account_id)}</title>
    <style>
        :root {{
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #f97316;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}

        .dark {{
            --bg: #0f172a;
            --card: #1e293b;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #334155;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

        header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 30px;
            border-radius: 16px;
        }}

        header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        header .subtitle {{ opacity: 0.9; font-size: 1.1em; }}

        .meta-info {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}

        .meta-item {{
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.95em;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: var(--card);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .stat-card .number {{
            font-size: 2.5em;
            font-weight: 700;
            color: var(--primary);
        }}

        .stat-card .label {{
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
            margin-top: 5px;
        }}

        .controls {{
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .controls-row {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}

        .search-box {{
            flex: 1;
            min-width: 250px;
            padding: 12px 16px;
            border: 2px solid var(--border);
            border-radius: 8px;
            font-size: 1em;
            background: var(--bg);
            color: var(--text);
        }}

        .search-box:focus {{
            outline: none;
            border-color: var(--primary);
        }}

        .filter-select {{
            padding: 12px 16px;
            border: 2px solid var(--border);
            border-radius: 8px;
            font-size: 1em;
            background: var(--bg);
            color: var(--text);
            min-width: 150px;
        }}

        .btn {{
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .btn-primary {{
            background: var(--primary);
            color: white;
        }}

        .btn-primary:hover {{
            background: var(--primary-dark);
        }}

        .btn-secondary {{
            background: var(--border);
            color: var(--text);
        }}

        .theme-toggle {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 100;
            background: var(--card);
            border: 2px solid var(--border);
            width: 44px;
            height: 44px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2em;
        }}

        .charts-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .chart-card {{
            background: var(--card);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .chart-card h3 {{
            margin-bottom: 20px;
            color: var(--text);
        }}

        .stat-bar {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }}

        .stat-bar .stat-label {{
            width: 80px;
            font-size: 0.85em;
            color: var(--text-muted);
        }}

        .stat-bar .bar {{
            height: 24px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 4px;
            min-width: 4px;
        }}

        .stat-bar .stat-value {{
            font-weight: 600;
            min-width: 40px;
        }}

        .service-section {{
            background: var(--card);
            border-radius: 12px;
            margin-bottom: 16px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .service-header {{
            display: flex;
            align-items: center;
            padding: 16px 20px;
            cursor: pointer;
            background: var(--card);
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
        }}

        .service-header:hover {{
            background: var(--bg);
        }}

        .service-name {{
            font-weight: 600;
            font-size: 1.1em;
            color: var(--primary);
        }}

        .service-count {{
            margin-left: auto;
            margin-right: 15px;
            color: var(--text-muted);
            font-size: 0.95em;
        }}

        .toggle-icon {{
            width: 24px;
            text-align: center;
            font-weight: bold;
            color: var(--text-muted);
        }}

        .service-content {{
            overflow-x: auto;
        }}

        .service-content.collapsed {{
            display: none;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background: var(--bg);
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 0.5px;
        }}

        tr:hover {{
            background: var(--bg);
        }}

        .resource-id {{
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.85em;
            color: var(--text-muted);
            cursor: pointer;
            max-width: 500px;
            overflow-wrap: break-word;
            line-height: 1.4;
            position: relative;
            padding-right: 24px;
        }}

        .resource-id::after {{
            content: '\\1F4CB';
            position: absolute;
            right: 4px;
            top: 50%;
            transform: translateY(-50%);
            opacity: 0;
            font-size: 0.9em;
            transition: opacity 0.2s;
        }}

        .resource-id:hover {{
            color: var(--primary);
            background: var(--bg);
        }}

        .resource-id:hover::after {{
            opacity: 0.7;
        }}

        .resource-id.copied::after {{
            content: '\\2705';
            opacity: 1;
        }}

        .region-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
        }}

        /* Region color coding */
        .region-badge[data-region^="us-"] {{ background: #dbeafe; color: #1e40af; }}
        .region-badge[data-region^="eu-"] {{ background: #dcfce7; color: #166534; }}
        .region-badge[data-region^="ap-"] {{ background: #fef3c7; color: #92400e; }}
        .region-badge[data-region^="sa-"] {{ background: #fce7f3; color: #9d174d; }}
        .region-badge[data-region^="ca-"] {{ background: #f3e8ff; color: #7c3aed; }}
        .region-badge[data-region^="af-"] {{ background: #ffedd5; color: #c2410c; }}
        .region-badge[data-region^="me-"] {{ background: #fee2e2; color: #b91c1c; }}
        .region-badge[data-region="global"] {{ background: #e0e7ff; color: #4338ca; }}

        .dark .region-badge[data-region^="us-"] {{ background: #1e3a5f; color: #93c5fd; }}
        .dark .region-badge[data-region^="eu-"] {{ background: #14532d; color: #86efac; }}
        .dark .region-badge[data-region^="ap-"] {{ background: #78350f; color: #fcd34d; }}
        .dark .region-badge[data-region^="sa-"] {{ background: #831843; color: #f9a8d4; }}
        .dark .region-badge[data-region^="ca-"] {{ background: #4c1d95; color: #c4b5fd; }}
        .dark .region-badge[data-region^="af-"] {{ background: #7c2d12; color: #fdba74; }}
        .dark .region-badge[data-region^="me-"] {{ background: #7f1d1d; color: #fca5a5; }}
        .dark .region-badge[data-region="global"] {{ background: #312e81; color: #a5b4fc; }}

        .stat-bar .region-bar {{
            background: linear-gradient(90deg, #22c55e, #3b82f6);
        }}

        .tag {{
            display: inline-block;
            padding: 2px 8px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border-radius: 10px;
            font-size: 0.75em;
            margin-right: 4px;
            margin-bottom: 2px;
        }}

        .tag.more {{
            background: var(--text-muted);
            cursor: pointer;
        }}

        .tag.more:hover {{
            background: var(--primary);
        }}

        .tags-cell {{
            max-width: 300px;
            position: relative;
        }}

        .tags-tooltip {{
            display: none;
            position: absolute;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 400px;
            top: 100%;
            left: 0;
        }}

        .tags-tooltip.show {{
            display: block;
        }}

        .tags-tooltip .tag {{
            margin-bottom: 4px;
        }}

        /* Detail rows */
        .details-row {{
            background: var(--bg);
        }}

        .details-row.collapsed {{
            display: none;
        }}

        .details-row:hover {{
            background: var(--bg);
        }}

        .details-row td {{
            padding: 0;
            border-bottom: 1px solid var(--border);
        }}

        .details-panel {{
            padding: 16px 24px;
        }}

        .details-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 8px 24px;
        }}

        .detail-item {{
            display: flex;
            gap: 8px;
            padding: 4px 0;
            min-width: 0;
            overflow: hidden;
        }}

        .detail-key {{
            color: var(--text-muted);
            font-size: 0.85em;
            min-width: 120px;
            flex-shrink: 0;
        }}

        .detail-value {{
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.85em;
            overflow-wrap: break-word;
            min-width: 0;
        }}

        .detail-value.bool-true {{
            color: #16a34a;
        }}

        .detail-value.bool-false {{
            color: #dc2626;
        }}

        .dark .detail-value.bool-true {{
            color: #4ade80;
        }}

        .dark .detail-value.bool-false {{
            color: #f87171;
        }}

        .detail-value.null-value {{
            color: var(--text-muted);
            font-style: italic;
        }}

        .detail-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }}

        .detail-list-item {{
            display: inline-block;
            padding: 2px 8px;
            background: var(--border);
            border-radius: 10px;
            font-size: 0.85em;
        }}

        mark {{ background: #fef08a; color: #1e293b; padding: 1px 2px; border-radius: 2px; }}
        .dark mark {{ background: #854d0e; color: #fef3c7; }}

        tr[data-has-details] {{
            cursor: pointer;
        }}

        tr[data-has-details] td:first-child {{
            position: relative;
            padding-left: 28px;
        }}

        tr[data-has-details] td:first-child::before {{
            content: '\\25B6';
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.65em;
            color: var(--text-muted);
            transition: transform 0.2s;
        }}

        tr[data-has-details].expanded td:first-child::before {{
            transform: translateY(-50%) rotate(90deg);
        }}

        .hidden {{ display: none !important; }}

        .toast {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--primary);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 1000;
        }}

        .toast.show {{ opacity: 1; }}

        .export-btns {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }}

        footer {{
            text-align: center;
            padding: 30px 20px;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            margin-top: 40px;
        }}

        .footer-logo {{
            font-size: 1.5em;
            font-weight: 700;
            background: linear-gradient(135deg, #ff9900 0%, #ffb84d 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        @media (max-width: 768px) {{
            header h1 {{ font-size: 1.8em; }}
            .meta-info {{ flex-direction: column; gap: 10px; }}
            .controls-row {{ flex-direction: column; }}
            .search-box, .filter-select {{ width: 100%; }}
        }}

        @media print {{
            .controls, .theme-toggle, .export-btns, .toggle-icon {{ display: none; }}
            .service-content.collapsed {{ display: block; }}
            .details-row.collapsed {{ display: table-row; }}
            tr[data-has-details] td:first-child::before {{ content: none; }}
            body {{ background: white; }}
        }}
    </style>
</head>
<body>
    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode">
        <span id="theme-icon">&#x1F319;</span>
    </button>

    <div class="container">
        <header>
            <h1>AWS Inventory Report</h1>
            <div class="subtitle">Comprehensive Cloud Asset Discovery</div>
            <div class="meta-info">
                <span class="meta-item">Account: {esc(account_id)}</span>
                <span class="meta-item">Generated: {esc(timestamp)}</span>
                <span class="meta-item">Duration: {duration}s</span>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">{total_resources:,}</div>
                <div class="label">Total Resources</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(services)}</div>
                <div class="label">Services</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(regions)}</div>
                <div class="label">Regions</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(resource_types)}</div>
                <div class="label">Resource Types</div>
            </div>
        </div>

        <div class="charts-row">
            <div class="chart-card">
                <h3>Top Services</h3>
                {service_stats}
            </div>
            <div class="chart-card">
                <h3>Top Regions</h3>
                {region_stats}
            </div>
        </div>

        <div class="controls">
            <div class="controls-row">
                <input type="text" class="search-box" id="searchBox" placeholder="Search resources..." onkeyup="debouncedFilter()">
                <select class="filter-select" id="serviceFilter" onchange="filterResources()">
                    <option value="">All Services</option>
                    {service_options}
                </select>
                <select class="filter-select" id="regionFilter" onchange="filterResources()">
                    <option value="">All Regions</option>
                    {region_options}
                </select>
                <select class="filter-select" id="tagFilter" onchange="filterResources()">
                    <option value="">All Tags</option>
                    {tag_options_html}
                </select>
                <button class="btn btn-secondary" onclick="clearFilters()">Clear</button>
                <button class="btn btn-secondary" onclick="expandAll()">Expand All</button>
                <button class="btn btn-secondary" onclick="collapseAll()">Collapse All</button>
            </div>
            <div class="export-btns">
                <button class="btn btn-primary" onclick="exportCSV()">Export CSV</button>
                <button class="btn btn-primary" onclick="window.print()">Print</button>
            </div>
        </div>

        <div id="services-container">
            {''.join(service_sections)}
        </div>

        <footer>
            <div class="footer-logo">awsmap</div>
        </footer>
    </div>

    <div class="toast" id="toast">Copied!</div>

    <script>
        function toggleTheme() {{
            document.body.classList.toggle('dark');
            const icon = document.getElementById('theme-icon');
            icon.innerHTML = document.body.classList.contains('dark') ? '&#x2600;' : '&#x1F319;';
            localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
        }}

        if (localStorage.getItem('theme') === 'dark') {{
            document.body.classList.add('dark');
            document.getElementById('theme-icon').innerHTML = '&#x2600;';
        }}

        function highlightMatches(element, term, selector) {{
            clearHighlights(element);
            if (!term) return;
            element.querySelectorAll(selector || '.detail-value').forEach(node => {{
                const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
                const textNodes = [];
                while (walker.nextNode()) textNodes.push(walker.currentNode);
                textNodes.forEach(textNode => {{
                    const text = textNode.nodeValue;
                    const lower = text.toLowerCase();
                    const termLower = term.toLowerCase();
                    const frag = document.createDocumentFragment();
                    let lastIdx = 0, idx, found = false;
                    while ((idx = lower.indexOf(termLower, lastIdx)) !== -1) {{
                        found = true;
                        if (idx > lastIdx) frag.appendChild(document.createTextNode(text.substring(lastIdx, idx)));
                        const mark = document.createElement('mark');
                        mark.textContent = text.substring(idx, idx + term.length);
                        frag.appendChild(mark);
                        lastIdx = idx + term.length;
                    }}
                    if (!found) return;
                    if (lastIdx < text.length) frag.appendChild(document.createTextNode(text.substring(lastIdx)));
                    textNode.parentNode.replaceChild(frag, textNode);
                }});
            }});
        }}

        function clearHighlights(element) {{
            element.querySelectorAll('mark').forEach(mark => {{
                const parent = mark.parentNode;
                parent.replaceChild(document.createTextNode(mark.textContent), mark);
                parent.normalize();
            }});
        }}

        let debounceTimer;
        function debouncedFilter() {{
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(filterResources, 300);
        }}

        function toggleSection(header) {{
            const content = header.nextElementSibling;
            const icon = header.querySelector('.toggle-icon');
            content.classList.toggle('collapsed');
            icon.textContent = content.classList.contains('collapsed') ? '+' : '-';
        }}

        function expandAll() {{
            document.querySelectorAll('.service-content').forEach(c => c.classList.remove('collapsed'));
            document.querySelectorAll('.toggle-icon').forEach(i => i.textContent = '-');
            document.querySelectorAll('.details-row').forEach(r => r.classList.remove('collapsed'));
            document.querySelectorAll('tr[data-has-details]').forEach(r => r.classList.add('expanded'));
        }}

        function collapseAll() {{
            document.querySelectorAll('.service-content').forEach(c => c.classList.add('collapsed'));
            document.querySelectorAll('.toggle-icon').forEach(i => i.textContent = '+');
            document.querySelectorAll('.details-row').forEach(r => r.classList.add('collapsed'));
            document.querySelectorAll('tr[data-has-details]').forEach(r => r.classList.remove('expanded'));
        }}

        function toggleDetails(row) {{
            const detailRow = row.nextElementSibling;
            if (detailRow && detailRow.classList.contains('details-row')) {{
                detailRow.classList.toggle('collapsed');
                row.classList.toggle('expanded');
            }}
        }}

        function filterResources() {{
            const search = document.getElementById('searchBox').value.toLowerCase();
            const service = document.getElementById('serviceFilter').value;
            const region = document.getElementById('regionFilter').value;
            const tag = document.getElementById('tagFilter').value;

            document.querySelectorAll('.service-section').forEach(section => {{
                const sectionService = section.dataset.service;
                if (service && sectionService !== service) {{
                    section.classList.add('hidden');
                    return;
                }}

                let hasVisible = false;
                section.querySelectorAll('tbody tr:not(.details-row)').forEach(row => {{
                    const rowService = row.dataset.service;
                    const rowRegion = row.dataset.region;
                    const rowName = row.dataset.name;
                    const rowId = row.dataset.id;
                    const rowTags = row.dataset.tags || '';

                    const matchService = !service || rowService === service;
                    const matchRegion = !region || rowRegion === region;
                    const detailText = row.dataset.details || '';
                    const matchSearch = !search || rowName.includes(search) || rowId.includes(search) || detailText.includes(search);
                    const matchTag = !tag || rowTags.split('|').includes(tag);

                    const matchedInName = search && (rowName.includes(search) || rowId.includes(search));
                    const matchedInDetails = search && detailText.includes(search);

                    if (matchService && matchRegion && matchSearch && matchTag) {{
                        row.classList.remove('hidden');
                        hasVisible = true;
                        if (search) {{
                            highlightMatches(row, search, 'td:nth-child(-n+3)');
                        }} else {{
                            clearHighlights(row);
                        }}
                        const detailRow = row.nextElementSibling;
                        if (detailRow && detailRow.classList.contains('details-row')) {{
                            detailRow.classList.remove('hidden');
                            if (matchedInDetails) {{
                                detailRow.classList.remove('collapsed');
                                row.classList.add('expanded');
                                row.dataset.autoExpanded = 'true';
                                highlightMatches(detailRow, search);
                            }} else if (row.dataset.autoExpanded) {{
                                detailRow.classList.add('collapsed');
                                row.classList.remove('expanded');
                                delete row.dataset.autoExpanded;
                                clearHighlights(detailRow);
                            }}
                        }}
                    }} else {{
                        row.classList.add('hidden');
                        clearHighlights(row);
                        const detailRow = row.nextElementSibling;
                        if (detailRow && detailRow.classList.contains('details-row')) {{
                            detailRow.classList.add('hidden');
                            clearHighlights(detailRow);
                        }}
                        if (row.dataset.autoExpanded) {{
                            delete row.dataset.autoExpanded;
                        }}
                    }}
                }});

                section.classList.toggle('hidden', !hasVisible);
                const content = section.querySelector('.service-content');
                const icon = section.querySelector('.toggle-icon');
                if (hasVisible && search) {{
                    content.classList.remove('collapsed');
                    if (icon) icon.textContent = '-';
                    section.dataset.autoExpanded = 'true';
                }} else if (!search && section.dataset.autoExpanded) {{
                    content.classList.add('collapsed');
                    if (icon) icon.textContent = '+';
                    delete section.dataset.autoExpanded;
                }}
            }});
        }}

        function clearFilters() {{
            document.getElementById('searchBox').value = '';
            document.getElementById('serviceFilter').value = '';
            document.getElementById('regionFilter').value = '';
            document.getElementById('tagFilter').value = '';
            filterResources();
        }}

        function copyToClipboard(el) {{
            navigator.clipboard.writeText(el.textContent.trim()).then(() => {{
                el.classList.add('copied');
                const toast = document.getElementById('toast');
                toast.classList.add('show');
                setTimeout(() => {{
                    toast.classList.remove('show');
                    el.classList.remove('copied');
                }}, 2000);
            }});
        }}

        function toggleTags(el) {{
            event.stopPropagation();
            const tooltip = el.parentElement.querySelector('.tags-tooltip');
            if (tooltip) {{
                // Close any other open tooltips
                document.querySelectorAll('.tags-tooltip.show').forEach(t => {{
                    if (t !== tooltip) t.classList.remove('show');
                }});
                tooltip.classList.toggle('show');
            }}
        }}

        // Close tooltips when clicking outside
        document.addEventListener('click', function(e) {{
            if (!e.target.classList.contains('more') && !e.target.closest('.tags-tooltip')) {{
                document.querySelectorAll('.tags-tooltip.show').forEach(t => t.classList.remove('show'));
            }}
        }});

        function exportCSV() {{
            let csv = 'Service,Type,Name,ID/ARN,Region\\n';
            document.querySelectorAll('tbody tr:not(.hidden):not(.details-row)').forEach(row => {{
                const cells = row.querySelectorAll('td');
                const data = [
                    row.dataset.service,
                    cells[0].textContent,
                    cells[1].textContent,
                    cells[2].textContent,
                    row.dataset.region
                ].map(s => '"' + s.replace(/"/g, '""') + '"');
                csv += data.join(',') + '\\n';
            }});

            const blob = new Blob([csv], {{type: 'text/csv'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'aws-inventory.csv';
            a.click();
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>'''

    return html


def format_output(data: Dict[str, Any], format_type: str) -> str:
    """
    Format inventory data in the specified format.

    Args:
        data: Inventory data with metadata and resources
        format_type: Output format (json, csv, html)

    Returns:
        Formatted string

    Raises:
        ValueError: If format type is not supported
    """
    format_type = format_type.lower()

    if format_type == 'json':
        return format_json(data)
    elif format_type == 'csv':
        return format_csv(data)
    elif format_type == 'html':
        return format_html(data)
    else:
        raise ValueError(f"Unsupported format: {format_type}")


def export_file(content: str, file_path: str) -> None:
    """
    Export content to a file.

    Args:
        content: Content to write
        file_path: Destination file path
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
