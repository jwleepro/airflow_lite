from __future__ import annotations

from datetime import datetime
from html import escape

from airflow_lite.api.paths import (
    MONITOR_PATH,
    pipeline_run_detail_path,
    pipeline_runs_path,
)
from airflow_lite.api.webui_helpers import (
    fmt,
    fmt_duration,
    render_layout,
    status_tone,
    t,
    with_language_query,
)
from airflow_lite.i18n import DEFAULT_LANGUAGE


def render_run_detail_page(
    run: dict,
    pipeline_name: str,
    schedule: str,
    *,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Airflow Gantt view 스타일의 step 실행 타임라인 상세 페이지."""
    steps: list[dict] = run.get("steps", [])
    run_status = run.get("status", "unknown")
    run_tone = status_tone(run_status)
    run_duration = fmt_duration(run.get("started_at"), run.get("finished_at"))

    all_starts = [
        datetime.fromisoformat(str(s["started_at"]))
        for s in steps
        if s.get("started_at")
    ]
    all_ends = [
        datetime.fromisoformat(str(s["finished_at"]))
        for s in steps
        if s.get("finished_at")
    ]
    now = datetime.now()
    timeline_start = min(all_starts) if all_starts else now
    timeline_end = max(all_ends) if all_ends else now
    total_secs = max(1.0, (timeline_end - timeline_start).total_seconds())

    step_rows: list[str] = []
    for step in steps:
        step_status = step.get("status", "unknown")
        step_tone = status_tone(step_status)
        step_duration = fmt_duration(step.get("started_at"), step.get("finished_at"))
        records = step.get("records_processed", 0)
        retries = step.get("retry_count", 0)

        bar_left_pct = 0.0
        bar_width_pct = 100.0
        if step.get("started_at"):
            try:
                step_start = datetime.fromisoformat(str(step["started_at"]))
                step_end = (
                    datetime.fromisoformat(str(step["finished_at"]))
                    if step.get("finished_at")
                    else now
                )
                offset = (step_start - timeline_start).total_seconds()
                dur_s = max(0.0, (step_end - step_start).total_seconds())
                bar_left_pct = min(98.0, offset / total_secs * 100)
                bar_width_pct = max(1.5, dur_s / total_secs * 100)
                bar_width_pct = min(bar_width_pct, 100.0 - bar_left_pct)
            except (ValueError, TypeError):
                pass

        error_html = ""
        if step.get("error_message"):
            error_html = f'<div class="step-error">{escape(str(step["error_message"]))}</div>'

        step_rows.append(f"""
          <tr>
            <td>
              <strong>{fmt(step.get("step_name"))}</strong>
              {error_html}
            </td>
            <td><span class="status {step_tone}">{fmt(step_status)}</span></td>
            <td>
              <div class="gantt-track">
                <div class="gantt-bar {step_tone}"
                     style="left:{bar_left_pct:.1f}%;width:{bar_width_pct:.1f}%"
                     title="{escape(step_duration)}"></div>
              </div>
            </td>
            <td>{fmt(step_duration)}</td>
            <td>{fmt(str(records) if records else None)}</td>
            <td>{fmt(str(retries))}</td>
          </tr>
        """)

    steps_html = (
        "".join(step_rows)
        or f'<tr><td colspan="6" class="empty">{escape(t(language, "webui.run_detail.empty.no_step_records"))}</td></tr>'
    )

    timeline_title = t(language, "webui.run_detail.timeline.title", count=len(steps))

    content_html = f"""
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">{escape(t(language, "webui.run_detail.eyebrow"))}</p>
          <h2>{escape(pipeline_name)} &nbsp;&middot;&nbsp; {fmt(run.get("execution_date"))}</h2>
        </div>
        <span class="status {run_tone}">{escape(run_status)}</span>
      </div>
      <dl class="meta-grid" style="margin-top:14px;">
        <div><dt>{escape(t(language, "webui.run_detail.meta.run_id"))}</dt><dd style="font-family:monospace;font-size:.85rem;">{fmt(run.get("id"))}</dd></div>
        <div><dt>{escape(t(language, "webui.run_detail.meta.trigger"))}</dt><dd>{fmt(run.get("trigger_type"))}</dd></div>
        <div><dt>{escape(t(language, "webui.run_detail.meta.duration"))}</dt><dd>{fmt(run_duration)}</dd></div>
        <div><dt>{escape(t(language, "webui.run_detail.meta.schedule"))}</dt><dd>{fmt(schedule)}</dd></div>
        <div><dt>{escape(t(language, "webui.run_detail.meta.started"))}</dt><dd>{fmt(run.get("started_at"))}</dd></div>
        <div><dt>{escape(t(language, "webui.run_detail.meta.finished"))}</dt><dd>{fmt(run.get("finished_at"))}</dd></div>
      </dl>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">{escape(t(language, "webui.run_detail.timeline.eyebrow"))}</p>
          <h2>{escape(timeline_title)}</h2>
        </div>
        <a class="button-link" href="{escape(with_language_query(MONITOR_PATH, language))}">{escape(t(language, "webui.run_detail.back_to_pipelines"))}</a>
      </div>
      <div class="table-wrap">
        <table class="gantt-table">
          <thead>
            <tr>
              <th style="min-width:180px;">{escape(t(language, "webui.run_detail.table.step"))}</th>
              <th>{escape(t(language, "webui.run_detail.table.status"))}</th>
              <th style="min-width:240px;">{escape(t(language, "webui.run_detail.table.timeline"))}</th>
              <th>{escape(t(language, "webui.run_detail.table.duration"))}</th>
              <th>{escape(t(language, "webui.run_detail.table.records"))}</th>
              <th>{escape(t(language, "webui.run_detail.table.retries"))}</th>
            </tr>
          </thead>
          <tbody>{steps_html}</tbody>
        </table>
      </div>
    </section>
    """
    return render_layout(
        title=t(language, "webui.run_detail.title", pipeline_name=pipeline_name),
        subtitle=t(
            language,
            "webui.run_detail.subtitle",
            execution_date=run.get("execution_date", ""),
            run_status=run_status,
        ),
        active_path=MONITOR_PATH,
        hero_links=[
            (t(language, "webui.run_detail.hero.all_runs_api"), pipeline_runs_path(pipeline_name)),
            (t(language, "webui.run_detail.hero.this_run_api"), pipeline_run_detail_path(pipeline_name, run.get("id", ""))),
        ],
        content_html=content_html,
        page_tag=t(language, "webui.layout.page_tag.run_timeline"),
        language=language,
    )
