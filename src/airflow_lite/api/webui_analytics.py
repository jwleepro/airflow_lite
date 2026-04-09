from __future__ import annotations

from html import escape

from airflow_lite.api.paths import (
    ANALYTICS_EXPORTS_PATH,
    ANALYTICS_FILTERS_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_PATH,
    dashboard_definition_path,
)
from airflow_lite.api.webui_helpers import (
    cfg,
    fmt,
    render_layout,
    status_tone,
    summary_tile,
    t,
    with_language_query,
)
from airflow_lite.i18n import DEFAULT_LANGUAGE


def render_unavailable_page(
    title: str,
    message: str,
    *,
    active_path: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    content_html = f"""
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(t(language, "webui.unavailable.eyebrow"))}</p><h2>{escape(t(language, "webui.unavailable.title"))}</h2></div>
        <span class="status bad">{escape(t(language, "webui.unavailable.status"))}</span>
      </div>
      <p class="muted">{escape(message)}</p>
      <p class="muted">{escape(t(language, "webui.unavailable.enable_hint"))}</p>
    </section>
    """
    return render_layout(
        title=title,
        subtitle=message,
        active_path=active_path,
        hero_links=[],
        content_html=content_html,
        page_tag=t(language, "webui.layout.page_tag.service_status"),
        language=language,
    )


def render_analytics_dashboard_page(
    page: dict,
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    analytics_refresh_seconds = cfg(webui_config, "analytics_refresh_seconds", 60)
    dashboard = page["dashboard"]
    summary = page["summary"]
    charts = page["charts"]
    detail_preview = page["detail_preview"]
    filters_applied = page["filters_applied"]
    export_jobs = page["export_jobs"]
    dashboard_id = dashboard["dashboard_id"]
    dataset = dashboard["dataset"]

    filter_controls: list[str] = []
    for filter_def in dashboard["filters"]:
        selected_values = set(filters_applied.get(filter_def["key"], []))
        options_html = "".join(
            f'<option value="{escape(opt["value"])}"{" selected" if opt["value"] in selected_values else ""}>'
            f'{escape(opt["label"])}</option>'
            for opt in filter_def["options"]
        )
        size = max(2, min(6, len(filter_def["options"]) or 2))
        filter_controls.append(f"""
            <label class="filter-field">
              <span>{escape(filter_def["label"])}</span>
              <select name="{escape(filter_def["key"])}" multiple size="{size}">{options_html}</select>
            </label>
        """)
    filter_controls_html = "".join(filter_controls) or (
        f'<p class="empty">{escape(t(language, "webui.analytics.empty.no_dashboard_filters"))}</p>'
    )
    filter_key_map = {item["key"]: item["label"] for item in dashboard["filters"]}
    filter_chips_html = "".join(
        f'<span class="chip">{escape(filter_key_map.get(key, key))}: {escape(value)}</span>'
        for key, values in filters_applied.items()
        for value in values
    ) or f'<span class="chip">{escape(t(language, "webui.analytics.filters.none_applied"))}</span>'

    summary_tiles = "".join([
        summary_tile(
            t(language, "webui.analytics.summary.dashboard.label"),
            dashboard["title"],
            t(language, "webui.analytics.summary.dashboard.detail"),
        ),
        summary_tile(
            t(language, "webui.analytics.summary.charts.label"),
            str(len(dashboard["charts"])),
            t(language, "webui.analytics.summary.charts.detail"),
        ),
        summary_tile(
            t(language, "webui.analytics.summary.active_filters.label"),
            str(sum(len(v) for v in filters_applied.values())),
            t(language, "webui.analytics.summary.active_filters.detail"),
        ),
        summary_tile(
            t(language, "webui.analytics.summary.recent_jobs.label"),
            str(len(export_jobs)),
            t(language, "webui.analytics.summary.recent_jobs.detail"),
            tone="warn" if export_jobs else "neutral",
        ),
    ])

    metric_map = {m["key"]: m for m in summary["metrics"]}
    metrics_html = "".join(
        f"""
        <article class="summary-tile neutral">
          <p class="summary-label">{escape(card["label"])}</p>
          <div class="summary-value">{fmt(metric_map.get(card["metric_key"], {}).get("value"))}</div>
          <p class="summary-detail">
            {fmt(metric_map.get(card["metric_key"], {}).get("unit"), fallback=t(language, "webui.analytics.metric.no_unit"))} \u00b7
            {fmt(card.get("description"), fallback=t(language, "webui.analytics.metric.default_description"))}
          </p>
        </article>
        """
        for card in dashboard["cards"]
    ) or f'<p class="empty">{escape(t(language, "webui.analytics.empty.no_summary_cards"))}</p>'

    chart_sections: list[str] = []
    for chart_def in dashboard["charts"]:
        chart_response = charts.get(chart_def["chart_id"])
        points = (
            chart_response["series"][0]["points"]
            if chart_response and chart_response.get("series")
            else []
        )
        max_value = max((p["value"] for p in points), default=1)
        point_rows = "".join(f"""
            <div class="chart-row">
              <strong>{escape(p.get("label") or p["bucket"])}</strong>
              <div class="chart-bar"><span style="width:{max(6, int(p["value"] / max_value * 100)) if max_value else 0}%"></span></div>
              <span>{fmt(p["value"])}</span>
            </div>
        """ for p in points) or f'<p class="empty">{escape(t(language, "webui.analytics.empty.no_chart_data"))}</p>'
        chart_sections.append(f"""
            <section class="subpanel">
              <div class="panel-head">
                <div><p class="eyebrow">{escape(t(language, "webui.analytics.chart.eyebrow"))}</p><h2>{escape(chart_def["title"])}</h2></div>
                <a href="{escape(with_language_query(chart_def["query_endpoint"], language))}" target="_blank" rel="noreferrer">{escape(t(language, "webui.analytics.chart.query_api"))}</a>
              </div>
              <div class="chart-list">{point_rows}</div>
            </section>
        """)
    charts_html = "".join(chart_sections) or f'<p class="empty">{escape(t(language, "webui.analytics.empty.no_charts"))}</p>'

    detail_table = f'<p class="empty">{escape(t(language, "webui.analytics.empty.no_drilldown_preview"))}</p>'
    if detail_preview is not None:
        columns = detail_preview["columns"]
        rows = detail_preview["rows"]
        head_html = "".join(f"<th>{escape(col['label'])}</th>" for col in columns)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{fmt(row.get(col['key']))}</td>" for col in columns) + "</tr>"
            for row in rows
        )
        if not body_html:
            body_html = f'<tr><td colspan="{len(columns)}" class="empty">{escape(t(language, "webui.analytics.empty.no_rows"))}</td></tr>'
        detail_table = (
            f'<div class="table-wrap"><table><thead><tr>{head_html}</tr></thead>'
            f'<tbody>{body_html}</tbody></table></div>'
        )

    hidden_filters_html = "".join(
        f'<input type="hidden" name="{escape(key)}" value="{escape(value)}">'
        for key, values in filters_applied.items()
        for value in values
    )
    export_forms_html = "".join(f"""
        <form class="inline-form" method="post" action="{escape(with_language_query(f"{MONITOR_ANALYTICS_PATH}/exports", language))}">
          <input type="hidden" name="dataset" value="{escape(dataset)}">
          <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
          <input type="hidden" name="lang" value="{escape(language)}">
          <input type="hidden" name="action_key" value="{escape(action["key"])}">
          <input type="hidden" name="format" value="{escape(action["format"] or "")}">
          {hidden_filters_html}
          <button type="submit">{escape(action["label"])}</button>
        </form>
    """ for action in dashboard["export_actions"] if action["status"] == "available"
    ) or f'<p class="empty">{escape(t(language, "webui.analytics.empty.no_export_actions"))}</p>'

    recent_jobs_rows = "".join(f"""
        <tr>
          <td style="font-family:monospace;font-size:.82rem;">{escape(job["job_id"][:16])}\u2026</td>
          <td><span class="status {status_tone(job["status"])}">{escape(job["status"])}</span></td>
          <td>{escape(job["format"])}</td>
          <td>{fmt(job["updated_at"])}</td>
        </tr>
    """ for job in export_jobs
    ) or f'<tr><td colspan="4" class="empty">{escape(t(language, "webui.analytics.empty.no_export_jobs"))}</td></tr>'

    analytics_refresh_notice = t(
        language,
        "webui.analytics.metadata.refresh_notice",
        seconds=analytics_refresh_seconds,
    )
    reset_href = with_language_query(
        f"{MONITOR_ANALYTICS_PATH}?dataset={dataset}&dashboard_id={dashboard_id}",
        language,
    )
    dashboard_api_href = with_language_query(
        f"{dashboard_definition_path(dashboard_id)}?dataset={dataset}",
        language,
    )
    full_export_monitor_href = with_language_query(
        f"{MONITOR_EXPORTS_PATH}?dataset={dataset}",
        language,
    )

    content_html = f"""
    <section class="summary-grid">{summary_tiles}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(t(language, "webui.analytics.metadata.eyebrow"))}</p><h2>{escape(dashboard["title"])}</h2></div>
        <span class="muted refresh-notice">{escape(analytics_refresh_notice)}</span>
      </div>
      <dl class="meta-grid">
        <div><dt>{escape(t(language, "webui.analytics.metadata.dashboard_id"))}</dt><dd>{escape(dashboard_id)}</dd></div>
        <div><dt>{escape(t(language, "webui.analytics.metadata.dataset"))}</dt><dd>{escape(dataset)}</dd></div>
        <div><dt>{escape(t(language, "webui.analytics.metadata.last_refreshed"))}</dt><dd>{fmt(dashboard.get("last_refreshed_at"))}</dd></div>
        <div><dt>{escape(t(language, "webui.analytics.metadata.contract"))}</dt><dd>{escape(dashboard["contract_version"])}</dd></div>
      </dl>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(t(language, "webui.analytics.filter_bar.eyebrow"))}</p><h2>{escape(t(language, "webui.analytics.filter_bar.title"))}</h2></div>
        <span class="muted">{escape(t(language, "webui.analytics.filter_bar.readonly_hint"))}</span>
      </div>
      <form class="filter-form" method="get" action="{escape(with_language_query(MONITOR_ANALYTICS_PATH, language))}">
        <input type="hidden" name="dataset" value="{escape(dataset)}">
        <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
        <div class="filter-grid">{filter_controls_html}</div>
        <div class="actions">
          <button class="primary" type="submit">{escape(t(language, "webui.analytics.filter_bar.apply_filters"))}</button>
          <a class="button-link" href="{escape(reset_href)}">{escape(t(language, "webui.analytics.filter_bar.reset"))}</a>
          <a class="button-link" href="{escape(dashboard_api_href)}" target="_blank" rel="noreferrer">{escape(t(language, "webui.analytics.filter_bar.dashboard_api"))}</a>
        </div>
      </form>
      <div class="chip-list" style="margin-top:10px;">{filter_chips_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(t(language, "webui.analytics.dataset_overview.eyebrow"))}</p><h2>{escape(t(language, "webui.analytics.dataset_overview.title"))}</h2></div>
        <span class="muted">{escape(t(language, "webui.analytics.dataset_overview.hint"))}</span>
      </div>
      <div class="summary-grid">{metrics_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head"><div><p class="eyebrow">{escape(t(language, "webui.analytics.charts.eyebrow"))}</p><h2>{escape(t(language, "webui.analytics.charts.title"))}</h2></div></div>
      <div class="grid-2">{charts_html}</div>
    </section>
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head">
          <div><p class="eyebrow">{escape(t(language, "webui.analytics.drilldown.eyebrow"))}</p><h2>{escape(t(language, "webui.analytics.drilldown.title"))}</h2></div>
          <span class="muted">{escape(t(language, "webui.analytics.drilldown.hint"))}</span>
        </div>
        {detail_table}
      </section>
      <section class="stack">
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">{escape(t(language, "webui.analytics.exports.eyebrow"))}</p><h2>{escape(t(language, "webui.analytics.exports.title"))}</h2></div>
            <span class="muted">{escape(t(language, "webui.analytics.exports.hint"))}</span>
          </div>
          <div class="actions">{export_forms_html}</div>
        </section>
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">{escape(t(language, "webui.analytics.recent_jobs.eyebrow"))}</p><h2>{escape(t(language, "webui.analytics.recent_jobs.title"))}</h2></div>
            <a href="{escape(full_export_monitor_href)}">{escape(t(language, "webui.analytics.recent_jobs.full_monitor"))}</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>{escape(t(language, "webui.analytics.recent_jobs.table.job_id"))}</th><th>{escape(t(language, "webui.analytics.recent_jobs.table.status"))}</th><th>{escape(t(language, "webui.analytics.recent_jobs.table.format"))}</th><th>{escape(t(language, "webui.analytics.recent_jobs.table.updated"))}</th></tr></thead>
              <tbody>{recent_jobs_rows}</tbody>
            </table>
          </div>
        </section>
      </section>
    </div>
    """
    return render_layout(
        title=t(language, "webui.analytics.title"),
        subtitle=t(language, "webui.analytics.subtitle"),
        active_path=MONITOR_ANALYTICS_PATH,
        hero_links=[],
        content_html=content_html,
        page_tag=t(language, "webui.layout.page_tag.analytics_workspace"),
        auto_refresh_seconds=analytics_refresh_seconds,
        language=language,
    )
