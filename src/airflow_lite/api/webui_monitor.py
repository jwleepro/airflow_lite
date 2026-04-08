from __future__ import annotations

from html import escape

from airflow_lite.api.paths import (
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_PATH,
    PIPELINES_PATH,
    monitor_pipeline_run_detail_path,
)
from airflow_lite.api.webui_helpers import (
    cfg,
    fmt,
    fmt_duration,
    render_layout,
    status_tone,
    summary_tile,
    t,
    with_language_query,
)
from airflow_lite.i18n import DEFAULT_LANGUAGE


def _run_status_block(status: str | None, *, language: str, title: str = "") -> str:
    tone = status_tone(status or "")
    tip = escape(title) if title else escape(status or t(language, "webui.run.no_run"))
    return f'<span class="run-block {tone}" title="{tip}"></span>'


def _run_status_grid(runs: list[dict], *, language: str) -> str:
    if not runs:
        return f'<span class="run-grid-empty">{escape(t(language, "webui.run.no_run"))}</span>'
    blocks = "".join(
        _run_status_block(
            run.get("status"),
            language=language,
            title=f"{run.get('execution_date', '')} · {run.get('status', '')}",
        )
        for run in reversed(runs)
    )
    return f'<div class="run-grid">{blocks}</div>'


def _first_failed_step_error(run: dict, *, max_length: int = 120) -> str | None:
    for step in run.get("steps", []):
        if step.get("status") == "failed" and step.get("error_message"):
            name = step.get("step_name", "")
            msg = str(step["error_message"])
            if len(msg) > max_length:
                msg = msg[:max_length] + "\u2026"
            return f"[{name}] {msg}"
    return None


def render_monitor_page(
    pipeline_rows: list[dict],
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    monitor_refresh_seconds = cfg(webui_config, "monitor_refresh_seconds", 30)
    error_message_max_length = cfg(webui_config, "error_message_max_length", 120)
    total_pipelines = len(pipeline_rows)
    active_runs = sum(
        1 for row in pipeline_rows
        if (row.get("latest_run") or {}).get("status", "").lower() in {"running", "queued", "pending"}
    )
    healthy_runs = sum(
        1 for row in pipeline_rows
        if (row.get("latest_run") or {}).get("status", "").lower() in {"success", "completed"}
    )
    failed_runs = sum(
        1 for row in pipeline_rows
        if (row.get("latest_run") or {}).get("status", "").lower() == "failed"
    )
    latest_finish = max(
        (
            row.get("latest_run", {}).get("finished_at")
            for row in pipeline_rows
            if row.get("latest_run", {}).get("finished_at")
        ),
        default=None,
    )

    summary_html = "".join([
        summary_tile(
            t(language, "webui.monitor.summary.configured_pipelines.label"),
            str(total_pipelines),
            t(language, "webui.monitor.summary.configured_pipelines.detail"),
        ),
        summary_tile(
            t(language, "webui.monitor.summary.healthy_last_run.label"),
            str(healthy_runs),
            t(language, "webui.monitor.summary.healthy_last_run.detail"),
            tone="ok",
        ),
        summary_tile(
            t(language, "webui.monitor.summary.active_runs.label"),
            str(active_runs),
            t(language, "webui.monitor.summary.active_runs.detail"),
            tone="warn" if active_runs else "neutral",
        ),
        summary_tile(
            t(language, "webui.monitor.summary.failed_last_run.label"),
            str(failed_runs),
            t(language, "webui.monitor.summary.failed_last_run.detail"),
            tone="bad" if failed_runs else "neutral",
        ),
    ])

    inventory_rows: list[str] = []
    for row in pipeline_rows:
        latest = row.get("latest_run") or {}
        latest_status = latest.get("status", "never-run")
        latest_status_tone = status_tone(latest_status)
        recent_runs = row.get("recent_runs", [])
        next_run = row.get("next_run")
        duration = fmt_duration(latest.get("started_at"), latest.get("finished_at"))
        run_id = latest.get("id", "")

        error_html = ""
        if latest_status == "failed":
            err = _first_failed_step_error(latest, max_length=error_message_max_length)
            if err:
                error_html = f'<div class="error-inline">{escape(err)}</div>'

        pulse_cls = " pulse" if latest_status in {"running", "queued", "pending"} else ""

        detail_link = (
            f'<a href="{escape(with_language_query(monitor_pipeline_run_detail_path(row["name"], run_id), language))}">{escape(t(language, "webui.monitor.detail_link"))}</a>'
            if run_id
            else "-"
        )

        inventory_rows.append(f"""
            <tr>
              <td>
                <div class="dense-cell">
                  <strong>{fmt(row["name"])}</strong>
                  <span>{fmt(row["table"])}</span>
                </div>
              </td>
              <td>{_run_status_grid(recent_runs, language=language)}</td>
              <td>
                <span class="status {latest_status_tone}{pulse_cls}">{fmt(latest_status)}</span>
                {error_html}
              </td>
              <td>{fmt(latest.get("trigger_type"))}</td>
              <td>{fmt(duration)}</td>
              <td>{fmt(latest.get("finished_at") or latest.get("started_at"))}</td>
              <td>{fmt(next_run, fallback="\u2014")}</td>
              <td>{fmt(row["schedule"])}</td>
              <td>{detail_link}</td>
            </tr>
        """)

    inventory_html = (
        "".join(inventory_rows)
        or f'<tr><td colspan="9" class="empty">{escape(t(language, "webui.monitor.empty.no_pipelines"))}</td></tr>'
    )

    monitor_notice = t(
        language,
        "webui.monitor.inventory.refresh_notice",
        latest_finish=fmt(latest_finish, fallback=t(language, "webui.monitor.inventory.none")),
        seconds=monitor_refresh_seconds,
    )

    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">{escape(t(language, "webui.monitor.inventory.eyebrow"))}</p>
          <h2>{escape(t(language, "webui.monitor.inventory.title"))}</h2>
        </div>
        <span class="muted refresh-notice">{escape(monitor_notice)}</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{escape(t(language, "webui.monitor.table.pipeline_table"))}</th>
              <th>{escape(t(language, "webui.monitor.table.recent_runs"))}</th>
              <th>{escape(t(language, "webui.monitor.table.status"))}</th>
              <th>{escape(t(language, "webui.monitor.table.trigger"))}</th>
              <th>{escape(t(language, "webui.monitor.table.duration"))}</th>
              <th>{escape(t(language, "webui.monitor.table.last_run"))}</th>
              <th>{escape(t(language, "webui.monitor.table.next_run"))}</th>
              <th>{escape(t(language, "webui.monitor.table.schedule"))}</th>
              <th>{escape(t(language, "webui.monitor.table.detail"))}</th>
            </tr>
          </thead>
          <tbody>{inventory_html}</tbody>
        </table>
      </div>
    </section>
    """
    return render_layout(
        title=t(language, "webui.monitor.title"),
        subtitle=t(language, "webui.monitor.subtitle"),
        active_path=MONITOR_PATH,
        hero_links=[
            (t(language, "webui.monitor.hero.pipelines_api"), PIPELINES_PATH),
            (t(language, "webui.monitor.hero.analytics"), MONITOR_ANALYTICS_PATH),
            (t(language, "webui.monitor.hero.exports"), MONITOR_EXPORTS_PATH),
        ],
        content_html=content_html,
        auto_refresh_seconds=monitor_refresh_seconds,
        language=language,
    )
