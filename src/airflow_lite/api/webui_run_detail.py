"""Run detail (Dag Run view) page renderer."""

from __future__ import annotations

from datetime import datetime

from airflow_lite.api.paths import (
    MONITOR_PATH,
    MONITOR_PIPELINES_PATH,
    monitor_pipeline_detail_path,
    monitor_pipeline_trigger_path,
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
                "started_at": step.get("started_at"),
                "finished_at": step.get("finished_at"),
            }
        )
    return out


def _build_grid_data(grid_runs: list[dict]) -> dict:
    if not grid_runs:
        return {"step_names": [], "runs": []}

    step_names: list[str] = []
    seen: set[str] = set()
    for run in grid_runs:
        for step in run.get("steps", []):
            name = step.get("step_name", "unknown")
            if name not in seen:
                step_names.append(name)
                seen.add(name)

    runs_data = []
    for run in reversed(grid_runs):
        step_map = {
            s.get("step_name", ""): tone_of(s.get("status", ""))
            for s in run.get("steps", [])
        }
        runs_data.append(
            {
                "id": run.get("id", ""),
                "execution_date": run.get("execution_date", ""),
                "status": run.get("status", ""),
                "tone": tone_of(run.get("status", "")),
                "step_tones": [step_map.get(name, "neutral") for name in step_names],
            }
        )

    return {"step_names": step_names, "runs": runs_data}


def _build_events(run: dict, step_rows: list[dict]) -> list[dict]:
    events: list[dict] = []

    def _append(timestamp: str | None, tone: str, title: str, detail: str) -> None:
        if timestamp:
            events.append(
                {
                    "timestamp": timestamp,
                    "tone": tone,
                    "title": title,
                    "detail": detail,
                }
            )

    _append(
        str(run.get("started_at") or ""),
        "warn" if tone_of(run.get("status")) == "warn" else "neutral",
        "Run started",
        f"Trigger: {run.get('trigger_type', '-')}",
    )
    for step in step_rows:
        _append(
            str(step.get("started_at") or ""),
            "warn",
            f"Task started: {step['name']}",
            f"State: {step['status']}",
        )
        if step.get("finished_at"):
            _append(
                str(step.get("finished_at") or ""),
                step["tone"],
                f"Task finished: {step['name']}",
                step.get("error_message") or f"Duration: {step['duration']}",
            )

    _append(
        str(run.get("finished_at") or ""),
        tone_of(run.get("status")),
        "Run finished",
        f"Final state: {run.get('status', '-')}",
    )
    events.sort(key=lambda item: item["timestamp"] or "")
    return events


def _build_code_snapshot(pipeline_name: str, run: dict, pipeline_meta: dict) -> str:
    columns = pipeline_meta.get("columns") or ""
    columns_block = columns if columns else "-"
    return "\n".join(
        [
            "pipeline:",
            f"  name: {pipeline_name}",
            f"  table: {pipeline_meta.get('table') or '-'}",
            f"  partition_column: {pipeline_meta.get('partition_column') or '-'}",
            f"  strategy: {pipeline_meta.get('strategy') or '-'}",
            f"  schedule: {pipeline_meta.get('schedule') or '-'}",
            f"  chunk_size: {pipeline_meta.get('chunk_size') or '-'}",
            f"  incremental_key: {pipeline_meta.get('incremental_key') or '-'}",
            f"  columns: {columns_block}",
            "dag_run:",
            f"  run_id: {run.get('id') or '-'}",
            f"  execution_date: {run.get('execution_date') or '-'}",
            f"  trigger_type: {run.get('trigger_type') or '-'}",
            f"  status: {run.get('status') or '-'}",
        ]
    )


def render_run_detail_page(
    run: dict,
    pipeline_name: str,
    schedule: str,
    *,
    language: str = DEFAULT_LANGUAGE,
    grid_runs: list[dict] | None = None,
    pipeline_meta: dict | None = None,
    actions: dict | None = None,
    operation_notice: dict | None = None,
) -> str:
    steps: list[dict] = run.get("steps", [])
    run_status = run.get("status", "unknown")
    pipeline_meta = pipeline_meta or {}
    actions = actions or {}
    step_rows = _build_step_rows(steps)
    grid = _build_grid_data(grid_runs or [])
    events = _build_events(run, step_rows)

    step_counts = {"ok": 0, "bad": 0, "running": 0}
    for step in steps:
        tone = tone_of(step.get("status", ""))
        if tone == "ok":
            step_counts["ok"] += 1
        elif tone == "bad":
            step_counts["bad"] += 1
        elif tone == "warn":
            step_counts["running"] += 1

    chrome = PageChrome(
        title=t(language, "webui.run_detail.title", pipeline_name=pipeline_name),
        subtitle=t(
            language,
            "webui.run_detail.subtitle",
            execution_date=run.get("execution_date", ""),
            run_status=run_status,
        ),
        active_path=MONITOR_PIPELINES_PATH,
        page_tag=t(language, "webui.layout.page_tag.run_timeline"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, "webui.layout.nav.pipelines"), MONITOR_PIPELINES_PATH),
            (pipeline_name, monitor_pipeline_detail_path(pipeline_name)),
            (str(run.get("execution_date") or run.get("id") or ""), None),
        ],
        hero_links=[
            (t(language, "webui.run_detail.hero.dag_details"), monitor_pipeline_detail_path(pipeline_name)),
            (t(language, "webui.run_detail.hero.all_runs_api"), pipeline_runs_path(pipeline_name)),
            (t(language, "webui.run_detail.hero.this_run_api"), pipeline_run_detail_path(pipeline_name, run.get("id", ""))),
        ],
        hero_actions=(
            [
                {
                    "href": monitor_pipeline_trigger_path(pipeline_name),
                    "label": t(language, "webui.actions.rerun_this_date"),
                    "class_name": "btn-primary",
                    "fields": {
                        "execution_date": run.get("execution_date", ""),
                        "force": "true",
                    },
                }
            ]
            if actions.get("can_trigger") and run.get("execution_date")
            else []
        ),
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
        step_rows=step_rows,
        step_counts=step_counts,
        grid=grid,
        events=events,
        pipeline_meta=pipeline_meta,
        code_snapshot=_build_code_snapshot(pipeline_name, run, pipeline_meta),
        actions=actions,
        operation_notice=operation_notice,
    )
