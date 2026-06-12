"""
Shared HTML styling for awsmap report commands (waste, tags).

Keeps a single stylesheet and theme/filter script so the report commands share
one consistent look with light and dark modes.
"""


def esc(s):
    """Escape a value for safe HTML output."""
    if s is None:
        return ''
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def base_css():
    """Return the shared stylesheet."""
    return """
        :root {
            --primary: #0972d3;
            --accent: #ec7211;
            --bg: #f2f3f3;
            --card: #ffffff;
            --text: #000716;
            --text-muted: #5f6b7a;
            --border: #d1d5db;
            --header-bg: #232f3e;
            --good: #22c55e;
            --warn: #f59e0b;
            --bad: #ef4444;
            --bar-track: #e5e7eb;
        }
        .dark {
            --bg: #0f1b2a;
            --card: #192534;
            --text: #d1d5db;
            --text-muted: #8d99ae;
            --border: #414d5c;
            --header-bg: #0f1b2a;
            --bar-track: #2b3a4d;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.43;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            background: var(--header-bg); color: white; padding: 16px 24px;
            display: flex; justify-content: space-between; align-items: center;
        }
        header h1 { font-size: 18px; font-weight: 600; }
        header .meta { font-size: 13px; opacity: 0.8; }
        .theme-toggle {
            background: none; border: 1px solid rgba(255,255,255,0.3);
            color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;
        }
        .theme-toggle:hover { background: rgba(255,255,255,0.1); }
        .summary-cards {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px; margin: 20px 0;
        }
        .summary-card {
            background: var(--card); border: 1px solid var(--border); border-radius: 8px;
            padding: 20px; text-align: center; border-top: 4px solid var(--border);
        }
        .summary-card .count { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
        .summary-card .label { font-size: 13px; color: var(--text-muted); text-transform: uppercase; }
        .summary-card.good { border-top-color: var(--good); }
        .summary-card.warn { border-top-color: var(--warn); }
        .summary-card.bad { border-top-color: var(--bad); }
        .panel {
            background: var(--card); border: 1px solid var(--border); border-radius: 8px;
            padding: 20px; margin: 20px 0;
        }
        .panel h3 { margin-bottom: 12px; font-size: 14px; color: var(--text-muted); }
        .bar-row { display: flex; align-items: center; margin: 6px 0; }
        .bar-label { width: 200px; font-size: 12px; font-weight: 600; }
        .bar-track {
            flex: 1; height: 16px; background: var(--bar-track);
            border-radius: 3px; overflow: hidden;
        }
        .bar-fill { height: 100%; min-width: 1px; background: var(--good); }
        .bar-fill.warn { background: var(--warn); }
        .bar-fill.bad { background: var(--bad); }
        .bar-count { width: 90px; text-align: right; font-size: 12px; color: var(--text-muted); }
        .filters { display: flex; gap: 12px; margin: 20px 0; flex-wrap: wrap; align-items: center; }
        .filters select, .filters input {
            padding: 8px 12px; border: 1px solid var(--border); border-radius: 4px;
            background: var(--card); color: var(--text); font-size: 13px;
        }
        .filters input { flex: 1; min-width: 200px; }
        .report-table {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 8px; overflow: hidden; margin: 20px 0;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: var(--bg); text-align: left; padding: 10px 12px; font-size: 12px;
            text-transform: uppercase; color: var(--text-muted); border-bottom: 1px solid var(--border);
        }
        td { padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: top; }
        tr.data-row:hover { background: var(--bg); }
        .resource-id { font-family: monospace; font-size: 12px; }
        .region-badge, .pill {
            display: inline-block; padding: 2px 6px; border-radius: 3px; background: var(--bg); font-size: 11px;
        }
        .pill.bad { background: var(--bad); color: #fff; }
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 11px; font-weight: 600; letter-spacing: 0.5px;
            background: var(--bg); color: var(--text-muted); border: 1px solid var(--border);
        }
        footer { text-align: center; padding: 20px; font-size: 12px; color: var(--text-muted); }
        footer a { color: var(--primary); text-decoration: none; }
        @media (max-width: 768px) { .filters { flex-direction: column; } }
"""


def theme_script():
    """Return the dark-mode toggle script (shared by all reports)."""
    return """
        function toggleTheme() {
            document.body.classList.toggle('dark');
            localStorage.setItem('awsmap-dark', document.body.classList.contains('dark'));
        }
        if (localStorage.getItem('awsmap-dark') === 'true') {
            document.body.classList.add('dark');
        }
"""


def row_filter_script():
    """Return a generic table-row text/select filter script.

    Expects a search input #searchInput and optional selects with class
    'row-filter' whose value matches a data-<id> attribute named by the select's
    data-key. Rows carry class 'data-row'.
    """
    return """
        function filterRows() {
            const search = (document.getElementById('searchInput') || {}).value || '';
            const q = search.toLowerCase();
            const selects = Array.from(document.querySelectorAll('select.row-filter'));
            document.querySelectorAll('tr.data-row').forEach(row => {
                let show = true;
                selects.forEach(sel => {
                    const want = sel.value;
                    if (want && row.dataset[sel.dataset.key] !== want) show = false;
                });
                if (q && !row.textContent.toLowerCase().includes(q)) show = false;
                row.style.display = show ? '' : 'none';
            });
        }
"""
