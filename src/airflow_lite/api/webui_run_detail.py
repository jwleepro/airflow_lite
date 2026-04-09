"""Run detail (Gantt) page renderer.

Delegates HTML production to `templates/run_detail.html`.
"""

from __future__ import annotations

from datetime import datetime

from airflow_lite.api.paths import (
    MONITOR_PATH,
    pipeline_run_detail_path,
    pipeline_runs_path,
)
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import fmt_duration, t
from airflow_lite.api.webui_status import tone_of
from airflow_lite.i18n import DEFAULT_LANGUAGE


def _build_step_rows(steps: list[dict]) -> list[dict]:
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

    out: list[dict] = []
    for step in steps:
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

        records = step.get("records_processed", 0)
        out.append(
            {
                "name": step.get("step_name"),
                "status": step.get("status", "unknown"),
                "tone": tone_of(step.get("status", "")),
                "duration": fmt_duration(step.get("started_at"), step.get("finished_at")),
                "records_display": str(records) if records else None,
                "retries": step.get("retry_count", 0),
                "bar_left_pct": bar_left_pct,
                "bar_width_pct": bar_width_pct,
                "error_message": step.get("error_message"),
            }
        )
    return out


def render_run_detail_page(
    run: dict,
    pipeline_name: str,
    schedule: str,
    *,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    steps: list[dict] = run.get("steps", [])
    run_status = run.get("status", "unknown")

    chrome = PageChrome(
        title=t(language, "webui.run_detail.title", pipeline_name=pipeline_name),
        subtitle=t(
            language,
            "webui.run_detail.subtitle",
            execution_date=run.get("execution_date", ""),
            run_status=run_status,
        ),
        active_path=MONITOR_PATH,
        page_tag=t(language, "webui.layout.page_tag.run_timeline"),
        hero_links=[
            (t(language, "webui.run_detail.hero.all_runs_api"), pipeline_runs_path(pipeline_name)),
            (t(language, "webui.run_detail.hero.this_run_api"), pipeline_run_detail_path(pipeline_name, run.get("id", ""))),
        ],
    )
    return render_page(
        "run_detail.html",
        chrome=chrome,
        language=language,
        run=run,
        pipeline_name=pipeline_name,
        schedule=schedule,
        run_status=run_status,
        run_tone=tone_of(run_status),
        run_duration=fmt_duration(run.get("started_at"), run.get("finished_at")),
        steps=steps,
        step_rows=_build_step_rows(steps),
    )
