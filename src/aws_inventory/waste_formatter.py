"""
Output formatters for `awsmap waste` - table, JSON, HTML.
"""

import json

from aws_inventory.report_style import esc, base_css, theme_script, row_filter_script


def _display_str(display):
    parts = [f"{k}={v}" for k, v in display.items() if v is not None]
    return ", ".join(parts)


def format_waste_table(result, metadata, summary_only=False):
    """Format waste findings as terminal output."""
    lines = []
    lines.append("")
    lines.append("Waste Report")
    lines.append("=" * 60)
    if metadata.get("account_label"):
        lines.append(f"  Account:  {metadata['account_label']}")
    lines.append(f"  Snapshot: current (is_current)")
    lines.append("")
    n_rules = sum(1 for k in result["summary"] if result["summary"][k] > 0)
    lines.append(f"  Summary:  {result['total']:,} findings across {n_rules} rule(s)")
    lines.append("=" * 60)

    by_rule = result["summary"]
    rules = result["rules"]
    if rules:
        lines.append("")
        lines.append("  By rule:")
        key_width = max(len(r["key"]) for r in rules)
        for r in rules:
            lines.append(f"    {r['key']:<{key_width}}  {by_rule[r['key']]:>5}   {r['title']}")

    if summary_only:
        lines.append("")
        return "\n".join(lines)

    if result["total"] == 0:
        lines.append("")
        lines.append("  No waste detected.")
        lines.append("")
        return "\n".join(lines)

    for r in rules:
        items = result["findings"][r["key"]]
        if not items:
            continue
        lines.append("")
        lines.append(f"{r['title'].upper()} ({len(items)})")
        if r["note"]:
            lines.append(f"  note: {r['note']}")
        lines.append("-" * 60)
        for item in items[:200]:
            region = item.get("region") or "global"
            extra = _display_str(item["display"])
            extra = f"  ({extra})" if extra else ""
            lines.append(f"  {item['service']}/{item['type']}  {item['id']}  "
                         f"{item.get('name') or ''}  {region}{extra}")
        if len(items) > 200:
            lines.append(f"  (... and {len(items) - 200} more)")
    lines.append("")
    return "\n".join(lines)


def format_waste_json(result, metadata):
    """Format waste findings as JSON."""
    out = {
        "metadata": {
            "account": metadata.get("account_label"),
            "min_age_days": result["min_age_days"],
            "include_defaults": bool(metadata.get("include_defaults")),
        },
        "summary": result["summary"],
        "total": result["total"],
        "findings": result["findings"],
    }
    return json.dumps(out, indent=2, default=str)


def format_waste_html(result, metadata):
    """Format waste findings as an HTML report."""
    account_label = metadata.get("account_label", "")

    cards = ""
    for r in result["rules"]:
        count = result["summary"][r["key"]]
        cls = "bad" if count else "good"
        cards += (f'<div class="summary-card {cls}"><div class="count">{count}</div>'
                  f'<div class="label">{esc(r["key"])}</div></div>')

    rule_options = "\n".join(
        f'<option value="{esc(r["key"])}">{esc(r["title"])}</option>'
        for r in result["rules"] if result["summary"][r["key"]] > 0)

    rows = ""
    for r in result["rules"]:
        for item in result["findings"][r["key"]]:
            region = esc(item.get("region") or "global")
            extra = esc(_display_str(item["display"]))
            rows += f'''
                <tr class="data-row" data-rule="{esc(r['key'])}">
                    <td><span class="badge">{esc(r['key'])}</span></td>
                    <td>{esc(item['service'])}/{esc(item['type'])}</td>
                    <td class="resource-id">{esc(item['id'])}</td>
                    <td>{esc(item.get('name') or '')}</td>
                    <td><span class="region-badge">{region}</span></td>
                    <td>{extra}</td>
                </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>awsmap waste report</title>
    <style>{base_css()}</style>
</head>
<body>
    <header>
        <div>
            <h1>awsmap waste report</h1>
            <div class="meta">{result['total']} findings{(' &middot; ' + esc(account_label)) if account_label else ''}</div>
        </div>
        <button class="theme-toggle" onclick="toggleTheme()">Toggle Dark Mode</button>
    </header>
    <div class="container">
        <div class="summary-cards">{cards}</div>
        <div class="filters">
            <select class="row-filter" data-key="rule" onchange="filterRows()">
                <option value="">All Rules</option>
                {rule_options}
            </select>
            <input type="text" id="searchInput" placeholder="Search resources..." oninput="filterRows()">
        </div>
        <div class="report-table">
            <table>
                <thead>
                    <tr><th>Rule</th><th>Service / Type</th><th>ID</th><th>Name</th><th>Region</th><th>Detail</th></tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="6" style="color:var(--text-muted)">No waste detected</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    <footer>
        Generated by <a href="https://github.com/TocConsulting/awsmap">awsmap</a>
    </footer>
    <script>
        {theme_script()}
        {row_filter_script()}
    </script>
</body>
</html>'''
    return html
