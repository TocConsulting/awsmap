"""
Output formatters for drift detection results — table, JSON, HTML.
"""

import json
import shutil


MAX_RESOURCES_PER_CATEGORY = 100


def format_diff_table(diff_result: dict, metadata: dict,
                      summary_only: bool = False,
                      change_type: str = 'all') -> str:
    """Format diff result as terminal table output."""
    lines = []
    summary = diff_result['_summary']
    multi_account = not metadata.get('account_id')
    account_labels = metadata.get('account_labels', {})

    # Header
    lines.append("")
    lines.append("Drift Report")
    lines.append("=" * 60)

    if metadata.get('account_label'):
        lines.append(f"  Account:    {metadata['account_label']}")
    lines.append(f"  From:       {metadata.get('from_date', '?')}"
                 f" ({metadata.get('from_info', '')})")
    lines.append(f"  To:         {metadata.get('to_date', 'current')}"
                 f" ({metadata.get('to_info', '')})")
    if metadata.get('services_compared'):
        lines.append(f"  Services:   {metadata['services_compared']} compared")

    lines.append("")
    lines.append(f"  Summary:  +{summary['added']:,} added, "
                 f"-{summary['removed']:,} removed, "
                 f"~{summary['modified']:,} modified, "
                 f"{summary['unchanged']:,} unchanged")
    lines.append("=" * 60)

    # Summary-only: per-service breakdown
    if summary_only:
        by_service = summary.get('by_service', {})
        if by_service:
            lines.append("")
            lines.append("  By Service:")

            # Column widths
            svc_width = max(len(s) for s in by_service) if by_service else 7
            svc_width = max(svc_width, 7)
            lines.append(f"    {'service':<{svc_width}}  {'added':>5}  {'removed':>7}  "
                         f"{'modified':>8}  {'unchanged':>9}")
            lines.append(f"    {'-' * svc_width}  {'-' * 5}  {'-' * 7}  "
                         f"{'-' * 8}  {'-' * 9}")
            for svc, counts in by_service.items():
                lines.append(f"    {svc:<{svc_width}}  {counts['added']:>5}  "
                             f"{counts['removed']:>7}  {counts['modified']:>8}  "
                             f"{counts['unchanged']:>9}")
        lines.append("")
        return '\n'.join(lines)

    # Detailed output
    added = diff_result.get('added', [])
    removed = diff_result.get('removed', [])
    modified = diff_result.get('modified', [])

    if change_type in ('all', 'added') and added:
        lines.append("")
        lines.append(f"ADDED ({len(added)})")
        lines.append("-" * 60)
        _format_resource_table(lines, added, MAX_RESOURCES_PER_CATEGORY,
                               multi_account, account_labels)

    if change_type in ('all', 'removed') and removed:
        lines.append("")
        lines.append(f"REMOVED ({len(removed)})")
        lines.append("-" * 60)
        _format_resource_table(lines, removed, MAX_RESOURCES_PER_CATEGORY,
                               multi_account, account_labels)

    if change_type in ('all', 'modified') and modified:
        lines.append("")
        lines.append(f"MODIFIED ({len(modified)})")
        lines.append("-" * 60)
        shown = modified[:MAX_RESOURCES_PER_CATEGORY]
        for entry in shown:
            r = entry['resource']
            changes = entry['changes']
            region = r.get('region') or 'global'
            acct_prefix = ''
            if multi_account:
                acct_id = r.get('account_id', '')
                acct_prefix = f"{account_labels.get(acct_id, acct_id)}  "
            lines.append(f"  {acct_prefix}{r['service']}/{r['type']}  {r['id']}  "
                         f"{r.get('name') or ''}  {region}")

            # Name change
            if 'name' in changes:
                lines.append(f"    name: {changes['name']['from']} -> "
                             f"{changes['name']['to']}")

            # Detail changes
            if 'details' in changes:
                lines.append("    details:")
                for d in changes['details']:
                    old_val = _format_val(d['from'])
                    new_val = _format_val(d['to'])
                    lines.append(f"      {d['field']}:  {old_val}  ->  {new_val}")

            # Tag changes
            if 'tags' in changes:
                tag_changes = changes['tags']
                lines.append("    tags:")
                for k, v in sorted(tag_changes.get('added', {}).items()):
                    lines.append(f"      + {k} = {v}")
                for k, v in sorted(tag_changes.get('changed', {}).items()):
                    lines.append(f"      ~ {k}: {v['from']} -> {v['to']}")
                for k, v in sorted(tag_changes.get('removed', {}).items()):
                    lines.append(f"      - {k}")

            lines.append("")

        remaining = len(modified) - MAX_RESOURCES_PER_CATEGORY
        if remaining > 0:
            lines.append(f"  (... and {remaining} more)")

    # No changes
    if change_type == 'all' and not added and not removed and not modified:
        lines.append("")
        lines.append("  No changes detected.")
    elif change_type != 'all':
        shown_list = {'added': added, 'removed': removed, 'modified': modified}
        if not shown_list.get(change_type):
            lines.append("")
            lines.append(f"  No {change_type} resources found.")

    lines.append("")
    return '\n'.join(lines)


def _format_resource_table(lines: list, resources: list, max_show: int,
                           multi_account: bool = False,
                           account_labels: dict = None):
    """Format a list of resources as aligned rows."""
    if account_labels is None:
        account_labels = {}
    shown = resources[:max_show]

    # Calculate column widths
    term_width = shutil.get_terminal_size((120, 24)).columns
    rows_data = []
    for r in shown:
        region = r.get('region') or 'global'
        row = []
        if multi_account:
            acct_id = r.get('account_id', '')
            row.append(account_labels.get(acct_id, acct_id))
        row.extend([
            r.get('service', ''),
            r.get('type', ''),
            r.get('id', ''),
            r.get('name', '') or '',
            region
        ])
        rows_data.append(tuple(row))

    if not rows_data:
        return

    n_cols = len(rows_data[0])
    widths = [max(len(row[i]) for row in rows_data) for i in range(n_cols)]
    # Cap widths to fit terminal
    total = sum(widths) + 2 * (n_cols - 1)
    if total > term_width - 4:
        # Shrink id and name columns (indices shift if multi_account)
        fixed_idx = [0, 1, n_cols - 1] if not multi_account else [0, 1, 2, n_cols - 1]
        fixed_w = sum(widths[i] for i in fixed_idx) + 2 * (n_cols - 1)
        available = term_width - 4 - fixed_w
        id_idx = 2 if not multi_account else 3
        name_idx = 3 if not multi_account else 4
        id_w = min(widths[id_idx], available * 2 // 3)
        name_w = min(widths[name_idx], available // 3)
        widths[id_idx] = max(id_w, 10)
        widths[name_idx] = max(name_w, 8)

    for row in rows_data:
        parts = []
        for val, w in zip(row, widths):
            if len(val) > w and w > 3:
                parts.append(val[:w - 3] + '...')
            else:
                parts.append(val.ljust(w))
        lines.append("  " + "  ".join(parts))

    remaining = len(resources) - max_show
    if remaining > 0:
        lines.append(f"  (... and {remaining} more)")


def _format_val(v) -> str:
    """Format a value for display."""
    if v is None:
        return '(none)'
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (list, dict)):
        return json.dumps(v, default=str)
    return str(v)


def format_diff_json(diff_result: dict, metadata: dict,
                     change_type: str = 'all') -> str:
    """Format diff result as JSON."""
    summary = diff_result['_summary']

    output = {
        "metadata": {
            "from_date": metadata.get('from_date'),
            "to_date": metadata.get('to_date', 'current'),
            "account_id": metadata.get('account_id'),
            "account_alias": metadata.get('account_alias'),
            "from_snapshot": metadata.get('from_snapshot', {}),
            "to_snapshot": metadata.get('to_snapshot', {}),
        },
        "summary": summary,
    }
    if change_type in ('all', 'added'):
        output["added"] = [_resource_to_json(r) for r in diff_result.get('added', [])]
    if change_type in ('all', 'removed'):
        output["removed"] = [_resource_to_json(r) for r in diff_result.get('removed', [])]
    if change_type in ('all', 'modified'):
        output["modified"] = [_modified_to_json(m) for m in diff_result.get('modified', [])]

    return json.dumps(output, indent=2, default=str)


def _resource_to_json(r: dict) -> dict:
    """Convert a resource dict to clean JSON output."""
    details = r.get('details')
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except (json.JSONDecodeError, TypeError):
            details = {}

    tags = r.get('tags')
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = {}

    result = {
        "service": r.get('service'),
        "type": r.get('type'),
        "id": r.get('id'),
        "name": r.get('name'),
        "region": r.get('region'),
        "arn": r.get('arn'),
        "details": details or {},
        "tags": tags or {},
    }
    if r.get('account_id'):
        result['account_id'] = r['account_id']
    return result


def _modified_to_json(entry: dict) -> dict:
    """Convert a modified resource entry to JSON."""
    r = entry['resource']
    result = _resource_to_json(r)
    result['changes'] = entry['changes']
    return result


def format_diff_html(diff_result: dict, metadata: dict,
                     change_type: str = 'all') -> str:
    """Format diff result as HTML report."""
    summary = diff_result['_summary']
    added = diff_result.get('added', []) if change_type in ('all', 'added') else []
    removed = diff_result.get('removed', []) if change_type in ('all', 'removed') else []
    modified = diff_result.get('modified', []) if change_type in ('all', 'modified') else []
    by_service = summary.get('by_service', {})

    total = summary['added'] + summary['removed'] + summary['modified'] + summary['unchanged']

    from_date = metadata.get('from_date', '?')
    to_date = metadata.get('to_date', 'current')
    account_label = metadata.get('account_label', '')

    def esc(s):
        if s is None:
            return ''
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    # Service options for filter
    all_services = set()
    for r in added:
        all_services.add(r.get('service', ''))
    for r in removed:
        all_services.add(r.get('service', ''))
    for m in modified:
        all_services.add(m['resource'].get('service', ''))
    service_options = '\n'.join(
        f'<option value="{esc(s)}">{esc(s.upper())}</option>'
        for s in sorted(all_services)
    )

    # Region options for filter
    all_regions = set()
    for r in added + removed:
        all_regions.add(r.get('region') or 'global')
    for m in modified:
        all_regions.add(m['resource'].get('region') or 'global')
    region_options = '\n'.join(
        f'<option value="{esc(r)}">{esc(r)}</option>'
        for r in sorted(all_regions)
    )

    # Per-service breakdown bars
    service_bars = ''
    if by_service:
        max_total = max(
            (s['added'] + s['removed'] + s['modified'] + s['unchanged'])
            for s in by_service.values()
        ) or 1
        for svc, counts in sorted(by_service.items()):
            svc_total = counts['added'] + counts['removed'] + counts['modified'] + counts['unchanged']
            a_pct = counts['added'] * 100 // max(1, max_total)
            r_pct = counts['removed'] * 100 // max(1, max_total)
            m_pct = counts['modified'] * 100 // max(1, max_total)
            service_bars += f'''
                <div class="svc-bar-row">
                    <span class="svc-bar-label">{esc(svc.upper())}</span>
                    <div class="svc-bar-track">
                        <div class="svc-bar added" style="width:{a_pct}%"></div>
                        <div class="svc-bar removed" style="width:{r_pct}%"></div>
                        <div class="svc-bar modified" style="width:{m_pct}%"></div>
                    </div>
                    <span class="svc-bar-count">{svc_total}</span>
                </div>'''

    # Build resource rows for each category
    multi_account = not metadata.get('account_id')
    html_account_labels = metadata.get('account_labels', {})

    def _acct_cell(r):
        if not multi_account:
            return ''
        acct_id = r.get('account_id', '')
        label = esc(html_account_labels.get(acct_id, acct_id))
        return f'<td class="account-cell">{label}</td>'

    def build_added_rows(resources):
        rows = ''
        for r in resources:
            region = esc(r.get('region') or 'global')
            svc = esc(r.get('service', ''))
            rows += f'''
                <tr class="diff-row added" data-service="{svc}" data-region="{region}">
                    <td><span class="badge badge-added">ADDED</span></td>
                    {_acct_cell(r)}
                    <td>{svc}/{esc(r.get('type', ''))}</td>
                    <td class="resource-id">{esc(r.get('id', ''))}</td>
                    <td>{esc(r.get('name') or '')}</td>
                    <td><span class="region-badge">{region}</span></td>
                </tr>'''
        return rows

    def build_removed_rows(resources):
        rows = ''
        for r in resources:
            region = esc(r.get('region') or 'global')
            svc = esc(r.get('service', ''))
            rows += f'''
                <tr class="diff-row removed" data-service="{svc}" data-region="{region}">
                    <td><span class="badge badge-removed">REMOVED</span></td>
                    {_acct_cell(r)}
                    <td>{svc}/{esc(r.get('type', ''))}</td>
                    <td class="resource-id">{esc(r.get('id', ''))}</td>
                    <td>{esc(r.get('name') or '')}</td>
                    <td><span class="region-badge">{region}</span></td>
                </tr>'''
        return rows

    def build_modified_rows(entries):
        rows = ''
        for entry in entries:
            r = entry['resource']
            changes = entry['changes']
            region = esc(r.get('region') or 'global')
            svc = esc(r.get('service', ''))

            # Build changes detail HTML
            changes_html = '<div class="changes-detail">'

            if 'name' in changes:
                changes_html += (f'<div class="change-item">'
                                 f'<span class="change-field">name</span>'
                                 f'<span class="change-old">{esc(str(changes["name"]["from"]))}</span>'
                                 f'<span class="change-arrow">&rarr;</span>'
                                 f'<span class="change-new">{esc(str(changes["name"]["to"]))}</span>'
                                 f'</div>')

            if 'details' in changes:
                for d in changes['details']:
                    old_v = esc(_format_val(d['from']))
                    new_v = esc(_format_val(d['to']))
                    changes_html += (f'<div class="change-item">'
                                     f'<span class="change-field">{esc(d["field"])}</span>'
                                     f'<span class="change-old">{old_v}</span>'
                                     f'<span class="change-arrow">&rarr;</span>'
                                     f'<span class="change-new">{new_v}</span>'
                                     f'</div>')

            if 'tags' in changes:
                tag_ch = changes['tags']
                for k, v in sorted(tag_ch.get('added', {}).items()):
                    changes_html += (f'<div class="change-item tag-added">'
                                     f'<span class="change-field">+ {esc(k)}</span>'
                                     f'<span class="change-new">{esc(str(v))}</span>'
                                     f'</div>')
                for k, v in sorted(tag_ch.get('changed', {}).items()):
                    changes_html += (f'<div class="change-item tag-changed">'
                                     f'<span class="change-field">~ {esc(k)}</span>'
                                     f'<span class="change-old">{esc(str(v["from"]))}</span>'
                                     f'<span class="change-arrow">&rarr;</span>'
                                     f'<span class="change-new">{esc(str(v["to"]))}</span>'
                                     f'</div>')
                for k, v in sorted(tag_ch.get('removed', {}).items()):
                    changes_html += (f'<div class="change-item tag-removed">'
                                     f'<span class="change-field">- {esc(k)}</span>'
                                     f'<span class="change-old">{esc(str(v))}</span>'
                                     f'</div>')

            changes_html += '</div>'

            colspan = 6 if multi_account else 5
            rows += f'''
                <tr class="diff-row modified" data-service="{svc}" data-region="{region}" onclick="toggleChanges(this)">
                    <td><span class="badge badge-modified">MODIFIED</span></td>
                    {_acct_cell(r)}
                    <td>{svc}/{esc(r.get('type', ''))}</td>
                    <td class="resource-id">{esc(r.get('id', ''))}</td>
                    <td>{esc(r.get('name') or '')}</td>
                    <td><span class="region-badge">{region}</span></td>
                </tr>
                <tr class="changes-row collapsed" data-service="{svc}" data-region="{region}">
                    <td colspan="{colspan}">{changes_html}</td>
                </tr>'''
        return rows

    added_rows = build_added_rows(added)
    removed_rows = build_removed_rows(removed)
    modified_rows = build_modified_rows(modified)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>awsmap drift report - {esc(from_date)} to {esc(to_date)}</title>
    <style>
        :root {{
            --primary: #0972d3;
            --primary-dark: #033160;
            --accent: #ec7211;
            --bg: #f2f3f3;
            --card: #ffffff;
            --text: #000716;
            --text-muted: #5f6b7a;
            --border: #d1d5db;
            --header-bg: #232f3e;
            --added-bg: #f0fdf4;
            --added-border: #22c55e;
            --added-text: #166534;
            --removed-bg: #fef2f2;
            --removed-border: #ef4444;
            --removed-text: #991b1b;
            --modified-bg: #fffbeb;
            --modified-border: #f59e0b;
            --modified-text: #92400e;
        }}

        .dark {{
            --bg: #0f1b2a;
            --card: #192534;
            --text: #d1d5db;
            --text-muted: #8d99ae;
            --border: #414d5c;
            --header-bg: #0f1b2a;
            --added-bg: #052e16;
            --added-border: #22c55e;
            --added-text: #86efac;
            --removed-bg: #450a0a;
            --removed-border: #ef4444;
            --removed-text: #fca5a5;
            --modified-bg: #451a03;
            --modified-border: #f59e0b;
            --modified-text: #fcd34d;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            font-size: 14px;
            line-height: 1.43;
        }}

        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

        header {{
            background: var(--header-bg);
            color: white;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        header h1 {{ font-size: 18px; font-weight: 600; }}
        header .meta {{ font-size: 13px; opacity: 0.8; }}

        .theme-toggle {{
            background: none; border: 1px solid rgba(255,255,255,0.3);
            color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer;
            font-size: 13px;
        }}
        .theme-toggle:hover {{ background: rgba(255,255,255,0.1); }}

        /* Summary cards */
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-top: 4px solid var(--border);
        }}
        .summary-card.added {{ border-top-color: var(--added-border); }}
        .summary-card.removed {{ border-top-color: var(--removed-border); }}
        .summary-card.modified {{ border-top-color: var(--modified-border); }}
        .summary-card.unchanged {{ border-top-color: #9ca3af; }}
        .summary-card .count {{
            font-size: 32px; font-weight: 700; margin-bottom: 4px;
        }}
        .summary-card.added .count {{ color: var(--added-border); }}
        .summary-card.removed .count {{ color: var(--removed-border); }}
        .summary-card.modified .count {{ color: var(--modified-border); }}
        .summary-card .label {{ font-size: 13px; color: var(--text-muted); text-transform: uppercase; }}

        /* Service breakdown */
        .breakdown {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .breakdown h3 {{ margin-bottom: 12px; font-size: 14px; color: var(--text-muted); }}
        .svc-bar-row {{ display: flex; align-items: center; margin: 6px 0; }}
        .svc-bar-label {{ width: 120px; font-size: 12px; font-weight: 600; text-transform: uppercase; }}
        .svc-bar-track {{
            flex: 1; height: 16px; display: flex;
            background: var(--bg); border-radius: 3px; overflow: hidden;
        }}
        .svc-bar {{ height: 100%; min-width: 1px; }}
        .svc-bar.added {{ background: var(--added-border); }}
        .svc-bar.removed {{ background: var(--removed-border); }}
        .svc-bar.modified {{ background: var(--modified-border); }}
        .svc-bar-count {{ width: 50px; text-align: right; font-size: 12px; color: var(--text-muted); }}

        /* Filters */
        .filters {{
            display: flex; gap: 12px; margin: 20px 0; flex-wrap: wrap; align-items: center;
        }}
        .filters select, .filters input {{
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 4px;
            background: var(--card);
            color: var(--text);
            font-size: 13px;
        }}
        .filters input {{ flex: 1; min-width: 200px; }}
        .filter-checks {{ display: flex; gap: 12px; }}
        .filter-checks label {{
            font-size: 13px; display: flex; align-items: center; gap: 4px; cursor: pointer;
        }}

        /* Resource table */
        .diff-table {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            margin: 20px 0;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            background: var(--bg); text-align: left; padding: 10px 12px;
            font-size: 12px; text-transform: uppercase; color: var(--text-muted);
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 10px 12px; border-bottom: 1px solid var(--border);
            font-size: 13px; vertical-align: top;
        }}
        tr.diff-row {{ cursor: default; }}
        tr.diff-row.modified {{ cursor: pointer; }}
        tr.diff-row:hover {{ background: var(--bg); }}

        .badge {{
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 11px; font-weight: 600; letter-spacing: 0.5px;
        }}
        .badge-added {{ background: var(--added-bg); color: var(--added-text); border: 1px solid var(--added-border); }}
        .badge-removed {{ background: var(--removed-bg); color: var(--removed-text); border: 1px solid var(--removed-border); }}
        .badge-modified {{ background: var(--modified-bg); color: var(--modified-text); border: 1px solid var(--modified-border); }}

        .resource-id {{ font-family: monospace; font-size: 12px; }}
        .region-badge {{
            display: inline-block; padding: 2px 6px; border-radius: 3px;
            background: var(--bg); font-size: 11px;
        }}

        /* Changes detail */
        .changes-row {{ background: var(--card); }}
        .changes-row.collapsed {{ display: none; }}
        .changes-detail {{ padding: 8px 12px 8px 40px; }}
        .change-item {{
            display: flex; align-items: center; gap: 8px;
            padding: 4px 0; font-size: 13px;
        }}
        .change-field {{ font-weight: 600; min-width: 140px; font-family: monospace; font-size: 12px; }}
        .change-old {{ color: var(--removed-text); text-decoration: line-through; }}
        .change-arrow {{ color: var(--text-muted); }}
        .change-new {{ color: var(--added-text); font-weight: 500; }}
        .tag-added .change-field {{ color: var(--added-text); }}
        .tag-removed .change-field {{ color: var(--removed-text); }}
        .tag-changed .change-field {{ color: var(--modified-text); }}

        /* Footer */
        footer {{
            text-align: center; padding: 20px; font-size: 12px; color: var(--text-muted);
        }}
        footer a {{ color: var(--primary); text-decoration: none; }}

        @media (max-width: 768px) {{
            .summary-cards {{ grid-template-columns: repeat(2, 1fr); }}
            .filters {{ flex-direction: column; }}
        }}
    </style>
</head>
<body>
    <header>
        <div>
            <h1>awsmap drift report</h1>
            <div class="meta">
                {esc(from_date)} &rarr; {esc(to_date)}
                {(' &middot; ' + esc(account_label)) if account_label else ''}
            </div>
        </div>
        <button class="theme-toggle" onclick="toggleTheme()">Toggle Dark Mode</button>
    </header>

    <div class="container">
        <!-- Summary cards -->
        <div class="summary-cards">
            {'<div class="summary-card added"><div class="count">+' + str(summary['added']) + '</div><div class="label">Added</div></div>' if change_type in ('all', 'added') else ''}
            {'<div class="summary-card removed"><div class="count">-' + str(summary['removed']) + '</div><div class="label">Removed</div></div>' if change_type in ('all', 'removed') else ''}
            {'<div class="summary-card modified"><div class="count">~' + str(summary['modified']) + '</div><div class="label">Modified</div></div>' if change_type in ('all', 'modified') else ''}
            <div class="summary-card unchanged">
                <div class="count">{summary['unchanged']:,}</div>
                <div class="label">Unchanged</div>
            </div>
        </div>

        <!-- Service breakdown -->
        <div class="breakdown">
            <h3>Changes by Service</h3>
            {service_bars if service_bars else '<p style="color:var(--text-muted)">No changes</p>'}
        </div>

        <!-- Filters -->
        <div class="filters">
            <div class="filter-checks">
                {'<label><input type="checkbox" checked onchange="filterRows()" class="filter-type" value="added"> Added</label>' if change_type in ('all', 'added') else ''}
                {'<label><input type="checkbox" checked onchange="filterRows()" class="filter-type" value="removed"> Removed</label>' if change_type in ('all', 'removed') else ''}
                {'<label><input type="checkbox" checked onchange="filterRows()" class="filter-type" value="modified"> Modified</label>' if change_type in ('all', 'modified') else ''}
            </div>
            <select onchange="filterRows()" id="serviceFilter">
                <option value="">All Services</option>
                {service_options}
            </select>
            <select onchange="filterRows()" id="regionFilter">
                <option value="">All Regions</option>
                {region_options}
            </select>
            <input type="text" placeholder="Search resources..." oninput="filterRows()" id="searchInput">
        </div>

        <!-- Resource table -->
        <div class="diff-table">
            <table>
                <thead>
                    <tr>
                        <th style="width:90px">Status</th>
                        {'<th>Account</th>' if multi_account else ''}
                        <th>Service / Type</th>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Region</th>
                    </tr>
                </thead>
                <tbody>
                    {added_rows}
                    {removed_rows}
                    {modified_rows}
                </tbody>
            </table>
        </div>
    </div>

    <footer>
        Generated by <a href="https://github.com/TocConsulting/awsmap">awsmap</a> &middot; {esc(total)} resources compared
    </footer>

    <script>
        function toggleChanges(row) {{
            const next = row.nextElementSibling;
            if (next && next.classList.contains('changes-row')) {{
                next.classList.toggle('collapsed');
            }}
        }}

        function toggleTheme() {{
            document.body.classList.toggle('dark');
            localStorage.setItem('awsmap-dark', document.body.classList.contains('dark'));
        }}
        if (localStorage.getItem('awsmap-dark') === 'true') {{
            document.body.classList.add('dark');
        }}

        function filterRows() {{
            const types = Array.from(document.querySelectorAll('.filter-type:checked')).map(c => c.value);
            const service = document.getElementById('serviceFilter').value;
            const region = document.getElementById('regionFilter').value;
            const search = document.getElementById('searchInput').value.toLowerCase();

            document.querySelectorAll('tr.diff-row').forEach(row => {{
                let show = true;

                // Type filter
                const rowType = row.classList.contains('added') ? 'added' :
                                row.classList.contains('removed') ? 'removed' : 'modified';
                if (!types.includes(rowType)) show = false;

                // Service filter
                if (service && row.dataset.service !== service) show = false;

                // Region filter
                if (region && row.dataset.region !== region) show = false;

                // Search filter
                if (search) {{
                    const text = row.textContent.toLowerCase();
                    if (!text.includes(search)) show = false;
                }}

                row.style.display = show ? '' : 'none';

                // Also hide associated changes row
                const next = row.nextElementSibling;
                if (next && next.classList.contains('changes-row')) {{
                    next.style.display = show ? '' : 'none';
                    if (!show) next.classList.add('collapsed');
                }}
            }});
        }}
    </script>
</body>
</html>'''

    return html
