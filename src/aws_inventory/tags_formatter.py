"""
Output formatters for `awsmap tags` - table, JSON, HTML.
"""

import json

from aws_inventory.report_style import esc, base_css, theme_script, row_filter_script


def _bar_class(pct):
    if pct >= 80:
        return ""
    if pct >= 50:
        return "warn"
    return "bad"


def format_tags_table(result, metadata, summary_only=False,
                      untagged_only=False, noncompliant_only=False):
    """Format a tag-compliance audit as terminal output."""
    lines = []
    overall = result["overall"]
    required = result["required"]

    lines.append("")
    lines.append("Tag Compliance Report")
    lines.append("=" * 60)
    if metadata.get("account_label"):
        lines.append(f"  Account:   {metadata['account_label']}")
    req_label = ", ".join(required) if required else "(any tag)"
    lines.append(f"  Required:  {req_label}")
    scope_note = "is_default included" if metadata.get("include_defaults") else "is_default excluded"
    lines.append(f"  Scope:     {result['scope_count']:,} resources ({scope_note})")
    lines.append("")
    lines.append(f"  Overall compliance:  {overall['pct']}%  "
                 f"({overall['compliant']:,} / {overall['total']:,})")
    lines.append("=" * 60)

    if result["scope_count"] == 0:
        lines.append("")
        lines.append("  No resources in scope.")
        lines.append("")
        return "\n".join(lines)

    if required and result["per_tag"]:
        lines.append("")
        lines.append("  Required tag coverage:")
        key_width = max(len(k) for k in required)
        for k in required:
            pt = result["per_tag"][k]
            lines.append(f"    {k:<{key_width}}  {pt['pct']:>3}%   "
                         f"({pt['present']:,}/{result['scope_count']:,})")

    by_service = result["by_service"]
    if by_service:
        lines.append("")
        lines.append("  By service:")
        svc_width = max((len(s) for s in by_service), default=7)
        svc_width = max(svc_width, 7)
        lines.append(f"    {'service':<{svc_width}}  {'compliant':>9}  {'total':>5}  {'coverage':>8}")
        lines.append(f"    {'-' * svc_width}  {'-' * 9}  {'-' * 5}  {'-' * 8}")
        for svc, c in by_service.items():
            lines.append(f"    {svc:<{svc_width}}  {c['compliant']:>9}  "
                         f"{c['total']:>5}  {str(c['pct']) + '%':>8}")

    if summary_only:
        lines.append("")
        return "\n".join(lines)

    listing = _filter_listing(result["noncompliant"], untagged_only, noncompliant_only)
    title = "UNTAGGED RESOURCES" if untagged_only else "NON-COMPLIANT RESOURCES"
    lines.append("")
    lines.append(f"{title} ({len(listing)})")
    lines.append("-" * 60)
    if not listing:
        lines.append("  None.")
    else:
        for r in listing[:200]:
            region = r.get("region") or "global"
            missing = ", ".join(r["missing"])
            lines.append(f"  {r['service']}/{r['type']}  {r['id']}  "
                         f"{r.get('name') or ''}  {region}  [missing: {missing}]")
        if len(listing) > 200:
            lines.append(f"  (... and {len(listing) - 200} more)")
    lines.append("")
    return "\n".join(lines)


def _filter_listing(noncompliant, untagged_only, noncompliant_only):
    if untagged_only:
        return [r for r in noncompliant if r.get("untagged")]
    return noncompliant


def format_tags_json(result, metadata, untagged_only=False, noncompliant_only=False):
    """Format a tag-compliance audit as JSON."""
    listing = _filter_listing(result["noncompliant"], untagged_only, noncompliant_only)
    out = {
        "metadata": {
            "account": metadata.get("account_label"),
            "required": result["required"],
            "scope_count": result["scope_count"],
            "include_defaults": bool(metadata.get("include_defaults")),
        },
        "overall": result["overall"],
        "per_tag": result["per_tag"],
        "by_service": result["by_service"],
        "noncompliant": listing,
    }
    return json.dumps(out, indent=2, default=str)


def format_tags_html(result, metadata, untagged_only=False, noncompliant_only=False):
    """Format a tag-compliance audit as an HTML report."""
    overall = result["overall"]
    required = result["required"]
    account_label = metadata.get("account_label", "")
    listing = _filter_listing(result["noncompliant"], untagged_only, noncompliant_only)

    overall_class = _bar_class(overall["pct"])
    card_cls = "good" if overall["pct"] >= 80 else ("warn" if overall["pct"] >= 50 else "bad")

    per_tag_bars = ""
    for k in required:
        pt = result["per_tag"][k]
        per_tag_bars += f'''
            <div class="bar-row">
                <span class="bar-label">{esc(k)}</span>
                <div class="bar-track"><div class="bar-fill {_bar_class(pt['pct'])}" style="width:{pt['pct']}%"></div></div>
                <span class="bar-count">{pt['pct']}% ({pt['present']})</span>
            </div>'''

    svc_bars = ""
    for svc, c in result["by_service"].items():
        svc_bars += f'''
            <div class="bar-row">
                <span class="bar-label">{esc(svc.upper())}</span>
                <div class="bar-track"><div class="bar-fill {_bar_class(c['pct'])}" style="width:{c['pct']}%"></div></div>
                <span class="bar-count">{c['pct']}% ({c['compliant']}/{c['total']})</span>
            </div>'''

    services = sorted({r["service"] for r in listing})
    service_options = "\n".join(
        f'<option value="{esc(s)}">{esc(s.upper())}</option>' for s in services)

    rows = ""
    for r in listing:
        region = esc(r.get("region") or "global")
        svc = esc(r["service"])
        missing = ", ".join(esc(m) for m in r["missing"])
        rows += f'''
            <tr class="data-row" data-service="{svc}">
                <td>{svc}/{esc(r['type'])}</td>
                <td class="resource-id">{esc(r['id'])}</td>
                <td>{esc(r.get('name') or '')}</td>
                <td><span class="region-badge">{region}</span></td>
                <td><span class="pill bad">{missing}</span></td>
            </tr>'''

    req_label = ", ".join(esc(k) for k in required) if required else "(any tag)"
    title = "Untagged resources" if untagged_only else "Non-compliant resources"

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>awsmap tag compliance</title>
    <style>{base_css()}</style>
</head>
<body>
    <header>
        <div>
            <h1>awsmap tag compliance</h1>
            <div class="meta">Required: {req_label}{(' &middot; ' + esc(account_label)) if account_label else ''}</div>
        </div>
        <button class="theme-toggle" onclick="toggleTheme()">Toggle Dark Mode</button>
    </header>
    <div class="container">
        <div class="summary-cards">
            <div class="summary-card {card_cls}">
                <div class="count">{overall['pct']}%</div>
                <div class="label">Compliant</div>
            </div>
            <div class="summary-card">
                <div class="count">{overall['compliant']:,}</div>
                <div class="label">Compliant resources</div>
            </div>
            <div class="summary-card">
                <div class="count">{overall['total']:,}</div>
                <div class="label">In scope</div>
            </div>
        </div>

        {('<div class="panel"><h3>Required tag coverage</h3>' + per_tag_bars + '</div>') if per_tag_bars else ''}

        <div class="panel"><h3>Coverage by service</h3>{svc_bars or '<p style="color:var(--text-muted)">No resources</p>'}</div>

        <div class="filters">
            <select class="row-filter" data-key="service" onchange="filterRows()">
                <option value="">All Services</option>
                {service_options}
            </select>
            <input type="text" id="searchInput" placeholder="Search resources..." oninput="filterRows()">
        </div>

        <div class="report-table">
            <table>
                <thead>
                    <tr>
                        <th>Service / Type</th><th>ID</th><th>Name</th><th>Region</th><th>Missing</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td colspan="5" style="color:var(--text-muted)">{esc(title)}: {len(listing)}</td></tr>
                    {rows}
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
