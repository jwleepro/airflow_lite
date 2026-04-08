from html import escape


def _fmt(value, fallback: str = "-") -> str:
    if value in (None, ""):
        return fallback
    return escape(str(value))


def _status_tone(status: str | None) -> str:
    tone_map = {
        "success": "ok",
        "completed": "ok",
        "running": "warn",
        "pending": "warn",
        "queued": "warn",
        "failed": "bad",
    }
    return tone_map.get((status or "").lower(), "neutral")


def _nav_link(label: str, href: str, active_path: str) -> str:
    active_class = " active" if href == active_path else ""
    return f'<a class="nav-link{active_class}" href="{escape(href)}">{escape(label)}</a>'


def _link_group(links: list[tuple[str, str]] | None) -> str:
    if not links:
        return ""
    return "".join(
        f'<a href="{escape(href)}" target="_blank" rel="noreferrer">{escape(label)}</a>'
        for label, href in links
    )


def _summary_tile(label: str, value: str, detail: str, *, tone: str = "neutral") -> str:
    return f"""
    <article class="summary-tile {escape(tone)}">
      <p class="summary-label">{escape(label)}</p>
      <div class="summary-value">{escape(value)}</div>
      <p class="summary-detail">{escape(detail)}</p>
    </article>
    """


def _render_layout(
    *,
    title: str,
    subtitle: str,
    active_path: str,
    content_html: str,
    hero_links: list[tuple[str, str]] | None = None,
    page_tag: str = "Operations Console",
) -> str:
    hero_links_html = _link_group(hero_links)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)}</title>
    <style>
      :root {{
        color-scheme: light; --bg:#f4f7fb; --bg-strong:#e9eef6; --panel:#fff; --panel-soft:#f8fbff;
        --ink:#1f2937; --muted:#667085; --line:#d6deea; --line-strong:#bfcade; --topbar:#12263f;
        --topbar-strong:#0d1c30; --brand:#00a7e1; --accent:#017cee; --accent-soft:rgba(1,124,238,.08);
        --ok:#0f9d58; --warn:#f79009; --bad:#d92d20; --neutral:#7a8699; --shadow:0 12px 34px rgba(15,23,42,.08);
      }}
      * {{ box-sizing:border-box; }} body {{ margin:0; font-family:"Segoe UI","Malgun Gothic",sans-serif; color:var(--ink);
        background:linear-gradient(180deg,var(--bg-strong) 0,var(--bg) 200px,var(--bg) 100%); }}
      a {{ color:var(--accent); }}
      .masthead {{ color:#fff; border-bottom:1px solid rgba(255,255,255,.08);
        background:linear-gradient(135deg,rgba(0,167,225,.16),transparent 28%),linear-gradient(180deg,var(--topbar) 0,var(--topbar-strong) 100%); }}
      .masthead-shell,.page-shell {{ max-width:1400px; margin:0 auto; padding-left:20px; padding-right:20px; }}
      .masthead-shell {{ padding-top:18px; padding-bottom:18px; }} .page-shell {{ padding-top:20px; padding-bottom:40px; }}
      .utility-bar,.nav-row,.header-card-row,.panel-head {{ display:flex; justify-content:space-between; gap:16px; }}
      .utility-bar,.header-card-row {{ align-items:center; }} .nav-row,.panel-head {{ align-items:flex-start; }}
      .brand-lockup {{ display:flex; align-items:center; gap:12px; }} .brand-mark {{ width:12px; height:12px; border-radius:999px;
        background:linear-gradient(135deg,#00a7e1,#5ad8ff); box-shadow:0 0 0 5px rgba(90,216,255,.16); }}
      .brand-copy {{ display:grid; gap:2px; }} .brand-copy strong {{ font-size:.98rem; letter-spacing:.04em; text-transform:uppercase; }}
      .brand-copy span,.page-kicker,.eyebrow,th,dt,.summary-label,.filter-field span {{ color:rgba(255,255,255,.68); font-size:.76rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; }}
      .utility-links,.header-links,.nav-tabs,.actions,.chip-list {{ display:flex; flex-wrap:wrap; gap:10px; }} .nav-tabs {{ gap:4px; align-self:stretch; }}
      .utility-links a,.header-links a,.button-link,button {{ text-decoration:none; padding:9px 14px; border-radius:10px; border:1px solid transparent; font-weight:600; cursor:pointer; }}
      .utility-links a {{ color:rgba(255,255,255,.88); background:rgba(255,255,255,.08); border-color:rgba(255,255,255,.12); }}
      .page-title {{ margin:0; font-size:clamp(1.8rem,4vw,2.8rem); line-height:1; }} .page-subtitle {{ margin:10px 0 0; max-width:860px; color:rgba(255,255,255,.72); }}
      .nav-link {{ color:rgba(255,255,255,.68); text-decoration:none; padding:14px 16px 12px; border-bottom:3px solid transparent; font-weight:700; }}
      .nav-link.active {{ color:#fff; border-bottom-color:var(--brand); }}
      .header-card,.panel,.subpanel,.summary-tile {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; box-shadow:var(--shadow); }}
      .header-card,.panel {{ padding:18px 20px; }} .subpanel,.summary-tile {{ padding:16px 18px; }}
      .header-tag,.chip {{ display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px; font-size:.82rem; font-weight:700; }}
      .header-tag {{ background:var(--accent-soft); color:var(--accent); text-transform:uppercase; }} .chip {{ background:var(--accent-soft); color:var(--accent); }}
      .header-links a,.button-link,button {{ color:var(--accent); background:var(--panel-soft); border-color:var(--line); }} button.primary {{ color:#fff; background:var(--accent); border-color:var(--accent); }}
      .stack,.section-list,.filter-form,.filter-field,.dense-cell,.brand-copy {{ display:grid; }} .stack,.section-list,.filter-form,.dense-cell {{ gap:14px; }}
      .grid-2 {{ display:grid; grid-template-columns:minmax(0,1.35fr) minmax(320px,.85fr); gap:16px; }}
      .grid-3 {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }}
      .summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; }}
      .summary-tile {{ border-top:4px solid var(--line-strong); }} .summary-tile.ok {{ border-top-color:var(--ok); }} .summary-tile.warn {{ border-top-color:var(--warn); }} .summary-tile.bad {{ border-top-color:var(--bad); }} .summary-tile.neutral {{ border-top-color:var(--neutral); }}
      .summary-label,.eyebrow,th,dt,.filter-field span {{ color:var(--muted); }} .summary-value {{ margin-top:12px; font-size:clamp(1.5rem,3vw,2.25rem); font-weight:800; line-height:1; }}
      .summary-detail,.muted,.dense-cell span {{ margin:8px 0 0; color:var(--muted); font-size:.92rem; }} h2 {{ margin:0; font-size:1.2rem; }}
      .meta-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }} .meta-grid div {{ padding:12px 14px; background:var(--panel-soft); border:1px solid var(--line); border-radius:12px; }}
      dd {{ margin:0; font-weight:700; }}
      .status {{ display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px; font-size:.8rem; font-weight:700; text-transform:capitalize; white-space:nowrap; background:rgba(122,134,153,.12); color:var(--neutral); }}
      .status::before,.chip::before {{ content:""; border-radius:999px; background:currentColor; }} .status::before {{ width:8px; height:8px; }} .chip::before {{ width:6px; height:6px; }}
      .status.ok {{ background:rgba(15,157,88,.12); color:var(--ok); }} .status.warn {{ background:rgba(247,144,9,.16); color:var(--warn); }} .status.bad {{ background:rgba(217,45,32,.12); color:var(--bad); }}
      .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:#fff; }}
      table {{ width:100%; border-collapse:collapse; min-width:720px; }} th,td {{ padding:11px 12px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; }}
      th {{ background:#f9fbfd; font-size:.78rem; letter-spacing:.05em; }} tbody tr:hover {{ background:rgba(1,124,238,.03); }} tbody tr:last-child td {{ border-bottom:none; }}
      .dense-cell strong {{ font-size:.95rem; }} .filter-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
      select {{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid var(--line); background:#fff; color:var(--ink); }}
      .chart-list {{ display:grid; gap:10px; }} .chart-row {{ display:grid; grid-template-columns:minmax(120px,200px) minmax(0,1fr) auto; gap:12px; align-items:center; }}
      .chart-bar {{ height:10px; border-radius:999px; background:rgba(1,124,238,.12); overflow:hidden; }} .chart-bar span {{ display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,#00a7e1,#017cee); }}
      .inline-form {{ display:inline-flex; }} .highlight {{ box-shadow:inset 3px 0 0 var(--accent); background:rgba(1,124,238,.04); }} .empty,.empty-page {{ color:var(--muted); }}
      @media (max-width:1080px) {{ .grid-2,.grid-3 {{ grid-template-columns:1fr; }} }}
      @media (max-width:760px) {{
        .masthead-shell,.page-shell {{ padding-left:14px; padding-right:14px; }}
        .utility-bar,.nav-row,.header-card-row,.panel-head {{ flex-direction:column; align-items:flex-start; }}
        .chart-row {{ grid-template-columns:1fr; }} .header-card,.panel,.subpanel {{ padding:16px; }}
      }}
    </style>
  </head>
  <body>
    <header class="masthead">
      <div class="masthead-shell">
        <div class="utility-bar">
          <div class="brand-lockup">
            <div class="brand-mark"></div>
            <div class="brand-copy">
              <strong>Airflow Lite</strong>
              <span>Read-only operations workspace</span>
            </div>
          </div>
          <div class="utility-links">
            <a href="/docs" target="_blank" rel="noreferrer">Swagger</a>
            <a href="/api/v1/pipelines" target="_blank" rel="noreferrer">Pipeline API</a>
          </div>
        </div>
        <div class="nav-row" style="margin-top:18px;">
          <div>
            <p class="page-kicker">{escape(page_tag)}</p>
            <h1 class="page-title">{escape(title)}</h1>
            <p class="page-subtitle">{escape(subtitle)}</p>
          </div>
          <nav class="nav-tabs">
            {_nav_link("Pipelines", "/monitor", active_path)}
            {_nav_link("Analytics", "/monitor/analytics", active_path)}
            {_nav_link("Exports", "/monitor/exports", active_path)}
          </nav>
        </div>
      </div>
    </header>
    <main class="page-shell">
      <section class="header-card">
        <div class="header-card-row">
          <span class="header-tag">Ops Console</span>
          <div class="header-links">{hero_links_html}</div>
        </div>
      </section>
      <div class="stack" style="margin-top:16px;">{content_html}</div>
    </main>
  </body>
</html>
"""


def render_monitor_page(pipeline_rows: list[dict]) -> str:
    total_pipelines = len(pipeline_rows)
    active_runs = sum(1 for row in pipeline_rows if (row.get("latest_run") or {}).get("status", "").lower() in {"running", "queued", "pending"})
    healthy_runs = sum(1 for row in pipeline_rows if (row.get("latest_run") or {}).get("status", "").lower() in {"success", "completed"})
    failed_runs = sum(1 for row in pipeline_rows if (row.get("latest_run") or {}).get("status", "").lower() == "failed")
    latest_finish = max((row.get("latest_run", {}).get("finished_at") for row in pipeline_rows if row.get("latest_run", {}).get("finished_at")), default=None)
    summary_html = "".join(
        [
            _summary_tile("Configured Pipelines", str(total_pipelines), "Inventory visible in one console view"),
            _summary_tile("Healthy Last Run", str(healthy_runs), "Most recent run completed successfully", tone="ok"),
            _summary_tile("Active Runs", str(active_runs), "Running, queued, or pending executions", tone="warn"),
            _summary_tile("Failed Last Run", str(failed_runs), "Pipelines requiring operator attention", tone="bad"),
        ]
    )

    inventory_rows = []
    history_sections = []
    for row in pipeline_rows:
        latest = row.get("latest_run") or {}
        latest_status = latest.get("status", "never-run")
        latest_status_tone = _status_tone(latest_status)
        inventory_rows.append(
            f"""
            <tr>
              <td><div class="dense-cell"><strong>{_fmt(row["name"])}</strong><span>Execution history and API route are linked below</span></div></td>
              <td>{_fmt(row["table"])}</td>
              <td>{_fmt(row["schedule"])}</td>
              <td>{_fmt(row["strategy"])}</td>
              <td><span class="status {latest_status_tone}">{_fmt(latest_status)}</span></td>
              <td>{_fmt(latest.get("trigger_type"))}</td>
              <td>{_fmt(latest.get("finished_at"), fallback=_fmt(latest.get("started_at")))}</td>
              <td><a href="/api/v1/pipelines/{escape(row["name"])}/runs" target="_blank" rel="noreferrer">Runs API</a></td>
            </tr>
            """
        )

        runs_html = "".join(
            f"""
            <tr>
              <td>{_fmt(run["execution_date"])}</td>
              <td><span class="status {_status_tone(run["status"])}">{_fmt(run["status"])}</span></td>
              <td>{_fmt(run["trigger_type"])}</td>
              <td>{_fmt(run["started_at"])}</td>
              <td>{_fmt(run["finished_at"])}</td>
            </tr>
            """
            for run in row.get("recent_runs", [])
        )
        if not runs_html:
            runs_html = '<tr><td colspan="5" class="empty">No runs recorded.</td></tr>'
        history_sections.append(
            f"""
            <section class="subpanel">
              <div class="panel-head">
                <div><p class="eyebrow">Recent Runs</p><h2>{_fmt(row["name"])}</h2></div>
                <span class="status {latest_status_tone}">{_fmt(latest_status)}</span>
              </div>
              <dl class="meta-grid" style="margin-bottom:14px;">
                <div><dt>Table</dt><dd>{_fmt(row["table"])}</dd></div>
                <div><dt>Schedule</dt><dd>{_fmt(row["schedule"])}</dd></div>
                <div><dt>Strategy</dt><dd>{_fmt(row["strategy"])}</dd></div>
                <div><dt>Last Finished</dt><dd>{_fmt(latest.get("finished_at"))}</dd></div>
              </dl>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Execution Date</th><th>Status</th><th>Trigger</th><th>Started</th><th>Finished</th></tr></thead>
                  <tbody>{runs_html}</tbody>
                </table>
              </div>
            </section>
            """
        )

    inventory_html = "".join(inventory_rows) or '<tr><td colspan="8" class="empty">No pipelines configured.</td></tr>'
    history_html = "".join(history_sections) or '<p class="empty-page">No pipeline history available.</p>'
    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Pipeline Inventory</p><h2>Airflow-style operator listing</h2></div>
        <span class="muted">Latest completed run: {_fmt(latest_finish, fallback="No completed runs yet")}</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Pipeline</th><th>Table</th><th>Schedule</th><th>Strategy</th><th>Status</th><th>Trigger</th><th>Last Run</th><th>API</th></tr></thead>
          <tbody>{inventory_html}</tbody>
        </table>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Execution History</p><h2>Recent runs by pipeline</h2></div>
        <span class="muted">Read-only history from the local SQLite metadata store</span>
      </div>
      <div class="section-list">{history_html}</div>
    </section>
    """
    return _render_layout(
        title="Airflow Lite Monitor",
        subtitle="Compact operator console for pipeline inventory, recent run status, and execution history without direct database access.",
        active_path="/monitor",
        hero_links=[("Pipelines API", "/api/v1/pipelines"), ("Analytics UI", "/monitor/analytics"), ("Export Jobs", "/monitor/exports")],
        content_html=content_html,
    )


def render_unavailable_page(title: str, message: str, *, active_path: str) -> str:
    content_html = f"""
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Unavailable</p><h2>Required service is not configured</h2></div>
        <span class="status bad">blocked</span>
      </div>
      <p class="muted">{escape(message)}</p>
      <p class="muted">Enable the analytics mart and export service wiring to use this screen.</p>
    </section>
    """
    return _render_layout(title=title, subtitle=message, active_path=active_path, hero_links=[("Pipelines", "/monitor"), ("Swagger", "/docs")], content_html=content_html, page_tag="Service Status")


def render_analytics_dashboard_page(page: dict) -> str:
    dashboard = page["dashboard"]
    summary = page["summary"]
    charts = page["charts"]
    detail_preview = page["detail_preview"]
    filters_applied = page["filters_applied"]
    export_jobs = page["export_jobs"]
    dashboard_id = dashboard["dashboard_id"]
    dataset = dashboard["dataset"]

    filter_controls = []
    for filter_definition in dashboard["filters"]:
        selected_values = set(filters_applied.get(filter_definition["key"], []))
        options_html = "".join(f'<option value="{escape(option["value"])}"{" selected" if option["value"] in selected_values else ""}>{escape(option["label"])}</option>' for option in filter_definition["options"])
        size = max(2, min(6, len(filter_definition["options"]) or 2))
        filter_controls.append(
            f"""
            <label class="filter-field">
              <span>{escape(filter_definition["label"])}</span>
              <select name="{escape(filter_definition["key"])}" multiple size="{size}">{options_html}</select>
            </label>
            """
        )
    filter_controls_html = "".join(filter_controls) or '<p class="empty">No dashboard filters defined.</p>'
    filter_chips_html = "".join(f'<span class="chip">{escape(key)}: {escape(value)}</span>' for key, values in filters_applied.items() for value in values) or '<span class="chip">No filters applied</span>'

    summary_tiles = "".join(
        [
            _summary_tile("Dashboard", dashboard["title"], "Contract-backed dashboard view"),
            _summary_tile("Charts", str(len(dashboard["charts"])), "Rendered from query endpoints"),
            _summary_tile("Active Filters", str(sum(len(values) for values in filters_applied.values())), "Current filter state in the URL"),
            _summary_tile("Recent Jobs", str(len(export_jobs)), "Latest exports for this dataset", tone="warn" if export_jobs else "neutral"),
        ]
    )

    metric_map = {metric["key"]: metric for metric in summary["metrics"]}
    metrics_html = "".join(
        f"""
        <article class="summary-tile neutral">
          <p class="summary-label">{escape(card["label"])}</p>
          <div class="summary-value">{_fmt(metric_map.get(card["metric_key"], {}).get("value"))}</div>
          <p class="summary-detail">{_fmt(metric_map.get(card["metric_key"], {}).get("unit"), fallback="No unit")} · {_fmt(card.get("description"), fallback="Dashboard summary metric")}</p>
        </article>
        """
        for card in dashboard["cards"]
    ) or '<p class="empty">No summary cards available.</p>'

    chart_sections = []
    for chart_definition in dashboard["charts"]:
        chart_response = charts.get(chart_definition["chart_id"])
        points = chart_response["series"][0]["points"] if chart_response and chart_response["series"] else []
        max_value = max((point["value"] for point in points), default=1)
        point_rows = "".join(
            f"""
            <div class="chart-row">
              <strong>{escape(point.get("label") or point["bucket"])}</strong>
              <div class="chart-bar"><span style="width: {max(6, int((point["value"] / max_value) * 100)) if max_value else 0}%"></span></div>
              <span>{_fmt(point["value"])}</span>
            </div>
            """
            for point in points
        ) or '<p class="empty">No chart points returned for the current filters.</p>'
        chart_sections.append(
            f"""
            <section class="subpanel">
              <div class="panel-head">
                <div><p class="eyebrow">Chart Query Output</p><h2>{escape(chart_definition["title"])}</h2></div>
                <a href="{escape(chart_definition["query_endpoint"])}" target="_blank" rel="noreferrer">Query API</a>
              </div>
              <div class="chart-list">{point_rows}</div>
            </section>
            """
        )
    charts_html = "".join(chart_sections) or '<p class="empty">No charts available.</p>'

    detail_table = '<p class="empty">No drilldown preview available.</p>'
    if detail_preview is not None:
        columns = detail_preview["columns"]
        rows = detail_preview["rows"]
        head_html = "".join(f"<th>{escape(column['label'])}</th>" for column in columns)
        body_html = "".join("<tr>" + "".join(f"<td>{_fmt(row.get(column['key']))}</td>" for column in columns) + "</tr>" for row in rows)
        if not body_html:
            body_html = f'<tr><td colspan="{len(columns)}" class="empty">No rows available.</td></tr>'
        detail_table = f'<div class="table-wrap"><table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>'

    hidden_filters_html = "".join(f'<input type="hidden" name="{escape(key)}" value="{escape(value)}">' for key, values in filters_applied.items() for value in values)
    export_forms_html = "".join(
        f"""
        <form class="inline-form" method="post" action="/monitor/analytics/exports">
          <input type="hidden" name="dataset" value="{escape(dataset)}">
          <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
          <input type="hidden" name="action_key" value="{escape(action["key"])}">
          <input type="hidden" name="format" value="{escape(action["format"] or "")}">
          {hidden_filters_html}
          <button type="submit">{escape(action["label"])}</button>
        </form>
        """
        for action in dashboard["export_actions"]
        if action["status"] == "available"
    ) or '<p class="empty">No export actions available.</p>'
    recent_jobs_rows = "".join(
        f"""
        <tr>
          <td>{escape(job["job_id"])}</td>
          <td><span class="status {_status_tone(job["status"])}">{escape(job["status"])}</span></td>
          <td>{escape(job["format"])}</td>
          <td>{_fmt(job["updated_at"])}</td>
        </tr>
        """
        for job in export_jobs
    ) or '<tr><td colspan="4" class="empty">No export jobs for this dataset yet.</td></tr>'

    content_html = f"""
    <section class="summary-grid">{summary_tiles}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Dashboard Metadata</p><h2>{escape(dashboard["title"])}</h2></div>
        <span class="muted">{_fmt(dashboard.get("description"), fallback="Dashboard metadata rendered from the analytics contract.")}</span>
      </div>
      <dl class="meta-grid">
        <div><dt>Dashboard ID</dt><dd>{escape(dashboard_id)}</dd></div>
        <div><dt>Dataset</dt><dd>{escape(dataset)}</dd></div>
        <div><dt>Last Refreshed</dt><dd>{_fmt(dashboard.get("last_refreshed_at"))}</dd></div>
        <div><dt>Contract</dt><dd>{escape(dashboard["contract_version"])}</dd></div>
      </dl>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Filter Bar</p><h2>Apply dashboard state</h2></div>
        <span class="muted">Read-only controls backed by the dashboard contract</span>
      </div>
      <form class="filter-form" method="get" action="/monitor/analytics">
        <input type="hidden" name="dataset" value="{escape(dataset)}">
        <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
        <div class="filter-grid">{filter_controls_html}</div>
        <div class="actions">
          <button class="primary" type="submit">Apply Filters</button>
          <a class="button-link" href="/monitor/analytics?dataset={escape(dataset)}&dashboard_id={escape(dashboard_id)}">Reset Filters</a>
          <a class="button-link" href="/api/v1/analytics/dashboards/{escape(dashboard_id)}?dataset={escape(dataset)}" target="_blank" rel="noreferrer">Dashboard API</a>
        </div>
      </form>
      <div class="chip-list">{filter_chips_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Dataset Overview</p><h2>Summary cards</h2></div>
        <span class="muted">The current filter state is reflected across every card and chart</span>
      </div>
      <div class="summary-grid">{metrics_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head"><div><p class="eyebrow">Charts</p><h2>Read-only query outputs</h2></div></div>
      <div class="grid-2">{charts_html}</div>
    </section>
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head">
          <div><p class="eyebrow">Drilldown Preview</p><h2>Source Files</h2></div>
          <span class="muted">Top rows from the current drilldown endpoint</span>
        </div>
        {detail_table}
      </section>
      <section class="stack">
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">Exports</p><h2>Queue Export</h2></div>
            <span class="muted">Submit jobs using declared dashboard actions</span>
          </div>
          <div class="actions">{export_forms_html}</div>
        </section>
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">Recent Jobs</p><h2>Latest export activity</h2></div>
            <a href="/monitor/exports?dataset={escape(dataset)}">Open full export monitor</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Job ID</th><th>Status</th><th>Format</th><th>Updated</th></tr></thead>
              <tbody>{recent_jobs_rows}</tbody>
            </table>
          </div>
        </section>
      </section>
    </div>
    """
    return _render_layout(
        title="Analytics Dashboard",
        subtitle="Airflow-inspired read-only dashboard workspace that consumes the operations contract, summary metrics, charts, drilldown preview, and export actions.",
        active_path="/monitor/analytics",
        hero_links=[("Dashboard API", f"/api/v1/analytics/dashboards/{dashboard_id}?dataset={dataset}"), ("Filters API", f"/api/v1/analytics/filters?dataset={dataset}"), ("Export Monitor", f"/monitor/exports?dataset={dataset}")],
        content_html=content_html,
        page_tag="Analytics Workspace",
    )


def render_export_jobs_page(page: dict) -> str:
    jobs = page["jobs"]
    selected_job_id = page.get("selected_job_id")
    counts = page["counts"]
    dataset = page.get("dataset")
    retention_hours = page["retention_hours"]
    summary_html = "".join(
        [
            _summary_tile("Queued", str(counts["queued"]), "Waiting for background worker pickup", tone="warn"),
            _summary_tile("Running", str(counts["running"]), "Artifacts currently being generated", tone="warn"),
            _summary_tile("Completed", str(counts["completed"]), "Available until retention expiry", tone="ok"),
            _summary_tile("Retention Window", str(retention_hours), "Hours before automatic cleanup"),
        ]
    )
    rows = []
    for job in jobs:
        download_cell = f'<a href="{escape(job["download_endpoint"])}">Download</a>' if job.get("download_endpoint") else '<span class="muted">Not ready</span>'
        highlight = " highlight" if selected_job_id and job["job_id"] == selected_job_id else ""
        rows.append(
            f"""
            <tr class="{highlight.strip()}">
              <td>{escape(job["job_id"])}</td><td>{escape(job["dataset"])}</td><td>{escape(job["action_key"])}</td>
              <td><span class="status {_status_tone(job["status"])}">{escape(job["status"])}</span></td>
              <td>{escape(job["format"])}</td><td>{_fmt(job.get("row_count"))}</td><td>{_fmt(job["created_at"])}</td>
              <td>{_fmt(job["updated_at"])}</td><td>{_fmt(job["expires_at"])}</td><td>{download_cell}</td><td>{_fmt(job.get("error_message"), fallback="")}</td>
            </tr>
            """
        )
    rows_html = "".join(rows) or '<tr><td colspan="11" class="empty">No export jobs recorded.</td></tr>'
    dataset_query = f"?dataset={escape(dataset)}" if dataset else ""
    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Retention</p><h2>Export Job Monitor</h2></div>
        <span class="muted">Filtered dataset: {_fmt(dataset, fallback="all datasets")}</span>
      </div>
      <p class="muted">Artifacts and job records are retained for {retention_hours} hour(s) before automatic cleanup.</p>
      <div class="actions">
        <a class="button-link" href="/monitor/exports">All datasets</a>
        <a class="button-link" href="/monitor/analytics{dataset_query if dataset else ''}">Back to analytics dashboard</a>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Job Inventory</p><h2>Airflow-style export listing</h2></div>
        <span class="muted">Selected job stays highlighted after redirect from the dashboard</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Job ID</th><th>Dataset</th><th>Action</th><th>Status</th><th>Format</th><th>Rows</th><th>Created</th><th>Updated</th><th>Expires</th><th>Download</th><th>Error</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </section>
    """
    return _render_layout(
        title="Export Jobs",
        subtitle="Airflow-inspired operator view over async analytics export jobs, retention, and artifact availability.",
        active_path="/monitor/exports",
        hero_links=[("Analytics Dashboard", f"/monitor/analytics{dataset_query}" if dataset else "/monitor/analytics"), ("Analytics Export API", "/api/v1/analytics/exports/{job_id}")],
        content_html=content_html,
        page_tag="Export Workspace",
    )
