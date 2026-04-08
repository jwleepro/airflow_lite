from __future__ import annotations

from html import escape

from airflow_lite.api.paths import (
    ANALYTICS_EXPORTS_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_EXPORT_DELETE_COMPLETED_PATH,
    MONITOR_EXPORT_DELETE_JOB_PATH,
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


def render_export_jobs_page(
    page: dict,
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    jobs = page["jobs"]
    selected_job_id = page.get("selected_job_id")
    counts = page["counts"]
    dataset = page.get("dataset")
    retention_hours = page["retention_hours"]
    active_refresh_seconds = cfg(webui_config, "exports_active_refresh_seconds", 10)
    idle_refresh_seconds = cfg(webui_config, "exports_idle_refresh_seconds", 30)

    summary_html = "".join([
        summary_tile(
            t(language, "webui.exports.summary.queued.label"),
            str(counts["queued"]),
            t(language, "webui.exports.summary.queued.detail"),
            tone="warn" if counts["queued"] else "neutral",
        ),
        summary_tile(
            t(language, "webui.exports.summary.running.label"),
            str(counts["running"]),
            t(language, "webui.exports.summary.running.detail"),
            tone="warn" if counts["running"] else "neutral",
        ),
        summary_tile(
            t(language, "webui.exports.summary.completed.label"),
            str(counts["completed"]),
            t(language, "webui.exports.summary.completed.detail"),
            tone="ok" if counts["completed"] else "neutral",
        ),
        summary_tile(
            t(language, "webui.exports.summary.retention.label"),
            f"{retention_hours}h",
            t(language, "webui.exports.summary.retention.detail"),
        ),
    ])

    rows: list[str] = []
    for job in jobs:
        download_cell = (
            f'<a href="{escape(with_language_query(job["download_endpoint"], language))}">{escape(t(language, "webui.exports.download"))}</a>'
            if job.get("download_endpoint")
            else f'<span class="muted">{escape(t(language, "webui.exports.not_ready"))}</span>'
        )
        highlight = " highlight" if selected_job_id and job["job_id"] == selected_job_id else ""
        is_active = job["status"] in {"running", "queued"}
        pulse_cls = " pulse" if is_active else ""
        dataset_hidden = f'<input type="hidden" name="dataset" value="{escape(dataset)}">' if dataset else ""
        lang_hidden = f'<input type="hidden" name="lang" value="{escape(language)}">'
        delete_cell = (
            f'<form method="post" action="{escape(with_language_query(MONITOR_EXPORT_DELETE_JOB_PATH, language))}" style="display:inline">'
            f'<input type="hidden" name="job_id" value="{escape(job["job_id"])}">'
            f'{dataset_hidden}'
            f'{lang_hidden}'
            f'<button type="submit" class="btn-delete" onclick="return confirm(\'{escape(t(language, "webui.exports.confirm.delete_job"))}\')">{escape(t(language, "webui.exports.delete"))}</button>'
            f'</form>'
        ) if not is_active else '<span class="muted">-</span>'

        rows.append(f"""
            <tr class="{highlight.strip()}">
              <td style="font-family:monospace;font-size:.82rem;">{escape(job["job_id"][:20])}…</td>
              <td>{escape(job["dataset"])}</td>
              <td>{escape(job["action_key"])}</td>
              <td><span class="status {status_tone(job["status"])}{pulse_cls}">{escape(job["status"])}</span></td>
              <td>{escape(job["format"])}</td>
              <td>{fmt(job.get("row_count"))}</td>
              <td>{fmt(job["created_at"])}</td>
              <td>{fmt(job["updated_at"])}</td>
              <td>{fmt(job["expires_at"])}</td>
              <td>{download_cell}</td>
              <td>{fmt(job.get("error_message"), fallback="")}</td>
              <td>{delete_cell}</td>
            </tr>
        """)

    rows_html = (
        "".join(rows)
        or f'<tr><td colspan="12" class="empty">{escape(t(language, "webui.exports.empty.no_jobs"))}</td></tr>'
    )
    dataset_query = f"?dataset={dataset}" if dataset else ""

    has_active = counts["queued"] + counts["running"] > 0
    refresh_secs = active_refresh_seconds if has_active else idle_refresh_seconds

    refresh_notice = t(
        language,
        "webui.exports.retention.refresh_notice",
        dataset=fmt(dataset, fallback=t(language, "webui.exports.retention.all_datasets")),
        seconds=refresh_secs,
    )
    retention_description = t(
        language,
        "webui.exports.retention.description",
        hours=retention_hours,
    )
    all_datasets_href = with_language_query(MONITOR_EXPORTS_PATH, language)
    analytics_href = with_language_query(
        f"{MONITOR_ANALYTICS_PATH}{dataset_query if dataset else ''}",
        language,
    )
    delete_completed_action = with_language_query(MONITOR_EXPORT_DELETE_COMPLETED_PATH, language)

    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(t(language, "webui.exports.retention.eyebrow"))}</p><h2>{escape(t(language, "webui.exports.retention.title"))}</h2></div>
        <span class="muted refresh-notice">{escape(refresh_notice)}</span>
      </div>
      <p class="muted">{escape(retention_description)}</p>
      <div class="actions">
        <a class="button-link" href="{escape(all_datasets_href)}">{escape(t(language, "webui.exports.actions.all_datasets"))}</a>
        <a class="button-link" href="{escape(analytics_href)}">{escape(t(language, "webui.exports.actions.analytics"))}</a>
        <form method="post" action="{escape(delete_completed_action)}" style="display:inline">
          {'<input type="hidden" name="dataset" value="' + escape(dataset) + '">' if dataset else ''}
          <input type="hidden" name="lang" value="{escape(language)}">
          <button type="submit" class="btn-delete" onclick="return confirm('{escape(t(language, "webui.exports.confirm.delete_all_completed"))}')">{escape(t(language, "webui.exports.actions.delete_all_completed"))}</button>
        </form>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(t(language, "webui.exports.inventory.eyebrow"))}</p><h2>{escape(t(language, "webui.exports.inventory.title"))}</h2></div>
        <span class="muted">{escape(t(language, "webui.exports.inventory.hint"))}</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{escape(t(language, "webui.exports.table.job_id"))}</th><th>{escape(t(language, "webui.exports.table.dataset"))}</th><th>{escape(t(language, "webui.exports.table.action"))}</th><th>{escape(t(language, "webui.exports.table.status"))}</th>
              <th>{escape(t(language, "webui.exports.table.format"))}</th><th>{escape(t(language, "webui.exports.table.rows"))}</th><th>{escape(t(language, "webui.exports.table.created"))}</th><th>{escape(t(language, "webui.exports.table.updated"))}</th>
              <th>{escape(t(language, "webui.exports.table.expires"))}</th><th>{escape(t(language, "webui.exports.table.download"))}</th><th>{escape(t(language, "webui.exports.table.error"))}</th><th>{escape(t(language, "webui.exports.table.admin"))}</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </section>
    """
    return render_layout(
        title=t(language, "webui.exports.title"),
        subtitle=t(language, "webui.exports.subtitle"),
        active_path=MONITOR_EXPORTS_PATH,
        hero_links=[
            (
                t(language, "webui.exports.hero.analytics"),
                f"{MONITOR_ANALYTICS_PATH}{dataset_query}" if dataset else MONITOR_ANALYTICS_PATH,
            ),
            (t(language, "webui.exports.hero.export_api"), ANALYTICS_EXPORTS_PATH),
        ],
        content_html=content_html,
        page_tag=t(language, "webui.layout.page_tag.export_workspace"),
        auto_refresh_seconds=refresh_secs,
        language=language,
    )
