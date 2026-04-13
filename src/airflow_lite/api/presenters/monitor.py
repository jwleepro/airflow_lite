"""Assemble data for the monitor (runs overview) page."""

from __future__ import annotations

from airflow_lite.api.schemas import build_run_response_with_steps
from airflow_lite.api.webui_helpers import fmt_duration
from airflow_lite.api.webui_status import tone_of


def calc_next_run(schedule_cron: str) -> str | None:
    """Compute the next scheduled run using APScheduler CronTrigger."""
    try:
        from datetime import datetime, timezone

        from apscheduler.triggers.cron import CronTrigger

        trigger = CronTrigger.from_crontab(schedule_cron)
        now = datetime.now(timezone.utc)
        next_time = trigger.get_next_fire_time(None, now)
        if next_time:
            local_dt = next_time.astimezone().replace(tzinfo=None)
            return local_dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return None


def build_pipeline_rows(settings, run_repo, step_repo) -> list[dict]:
    """Build the list-of-dicts consumed by `render_monitor_page`."""
    webui = settings.webui
    pipeline_rows: list[dict] = []
    for pipeline in settings.pipelines:
        recent_runs: list[dict] = []
        latest_run = None
        if run_repo is not None:
            runs = run_repo.find_by_pipeline(pipeline.name, limit=webui.recent_runs_limit)
            recent_runs = [
                build_run_response_with_steps(run, step_repo).model_dump(mode="json")
                for run in runs
            ]
            latest_run = recent_runs[0] if recent_runs else None

        pipeline_rows.append(
            {
                "name": pipeline.name,
                "table": pipeline.table,
                "strategy": pipeline.strategy,
                "schedule": pipeline.schedule,
                "next_run": calc_next_run(pipeline.schedule),
                "latest_run": latest_run,
                "recent_runs": recent_runs,
            }
        )
    return pipeline_rows


def build_run_detail_data(run_obj, step_repo, settings, pipeline_name: str) -> tuple[dict, str]:
    """Return (run_dict, schedule) for the run detail page."""
    run_dict = build_run_response_with_steps(run_obj, step_repo).model_dump(mode="json")
    pipeline_cfg = next((p for p in settings.pipelines if p.name == pipeline_name), None)
    schedule = pipeline_cfg.schedule if pipeline_cfg else "-"
    return run_dict, schedule


def _collect_step_names(runs: list[dict]) -> list[str]:
    step_names: list[str] = []
    seen: set[str] = set()
    for run in runs:
        for step in run.get("steps", []):
            name = step.get("step_name", "unknown")
            if name not in seen:
                step_names.append(name)
                seen.add(name)
    return step_names


def build_pipeline_detail_view_data(settings, run_repo, step_repo, pipeline_name: str) -> dict | None:
    pipeline_cfg = next((p for p in settings.pipelines if p.name == pipeline_name), None)
    if pipeline_cfg is None:
        return None

    recent_limit = getattr(settings.webui, "recent_runs_limit", 10)
    run_dicts: list[dict] = []
    if run_repo is not None:
        runs = run_repo.find_by_pipeline(pipeline_name, limit=recent_limit)
        run_dicts = [
            build_run_response_with_steps(run, step_repo).model_dump(mode="json")
            for run in runs
        ]

    latest_run = run_dicts[0] if run_dicts else None
    step_names = _collect_step_names(run_dicts)
    latest_step_map = {
        step.get("step_name", "unknown"): step
        for step in (latest_run or {}).get("steps", [])
    }

    grid_runs = []
    for run in reversed(run_dicts):
        step_map = {
            step.get("step_name", ""): tone_of(step.get("status", ""))
            for step in run.get("steps", [])
        }
        grid_runs.append(
            {
                "id": run.get("id", ""),
                "execution_date": run.get("execution_date", ""),
                "status": run.get("status", ""),
                "tone": tone_of(run.get("status", "")),
                "step_tones": [step_map.get(name, "neutral") for name in step_names],
            }
        )

    task_rows = []
    for name in step_names:
        instances = []
        for run in run_dicts:
            step = next((item for item in run.get("steps", []) if item.get("step_name") == name), None)
            if step:
                instances.append(step)

        task_rows.append(
            {
                "name": name,
                "latest_status": (instances[0].get("status") if instances else ""),
                "latest_tone": tone_of(instances[0].get("status", "") if instances else ""),
                "success_count": sum(1 for item in instances if tone_of(item.get("status")) == "ok"),
                "running_count": sum(1 for item in instances if tone_of(item.get("status")) == "warn"),
                "failed_count": sum(1 for item in instances if tone_of(item.get("status")) == "bad"),
                "latest_duration": fmt_duration(
                    (instances[0] if instances else {}).get("started_at"),
                    (instances[0] if instances else {}).get("finished_at"),
                ),
                "recent_tones": [next((run["step_tones"][idx] for idx, step_name in enumerate(step_names) if step_name == name), "neutral") for run in grid_runs],
            }
        )

    recent_failures = []
    for run in run_dicts:
        if tone_of(run.get("status", "")) != "bad":
            continue
        first_failed_step = next(
            (step for step in run.get("steps", []) if tone_of(step.get("status", "")) == "bad"),
            None,
        )
        recent_failures.append(
            {
                "run_id": run.get("id", ""),
                "execution_date": run.get("execution_date", ""),
                "status": run.get("status", ""),
                "step_name": (first_failed_step or {}).get("step_name"),
                "error_message": (first_failed_step or {}).get("error_message"),
            }
        )

    run_tones = [tone_of(run.get("status", "")) for run in run_dicts]
    summary = {
        "total_runs": len(run_dicts),
        "success_runs": sum(1 for tone in run_tones if tone == "ok"),
        "active_runs": sum(1 for tone in run_tones if tone == "warn"),
        "failed_runs": sum(1 for tone in run_tones if tone == "bad"),
        "task_count": len(step_names),
    }

    graph_nodes = []
    graph_order = [step.get("step_name", "unknown") for step in (latest_run or {}).get("steps", [])] or step_names
    seen_graph: set[str] = set()
    for name in graph_order:
        if name in seen_graph:
            continue
        seen_graph.add(name)
        step = latest_step_map.get(name, {})
        graph_nodes.append(
            {
                "name": name,
                "status": step.get("status", "unknown"),
                "tone": tone_of(step.get("status", "")),
                "duration": fmt_duration(step.get("started_at"), step.get("finished_at")),
            }
        )

    return {
        "pipeline": {
            "name": pipeline_cfg.name,
            "table": pipeline_cfg.table,
            "partition_column": pipeline_cfg.partition_column,
            "strategy": pipeline_cfg.strategy,
            "schedule": pipeline_cfg.schedule,
            "chunk_size": pipeline_cfg.chunk_size,
            "columns": pipeline_cfg.columns,
            "incremental_key": pipeline_cfg.incremental_key,
            "next_run": calc_next_run(pipeline_cfg.schedule),
        },
        "summary": summary,
        "latest_run": latest_run,
        "recent_failures": recent_failures[:5],
        "runs": run_dicts,
        "grid": {
            "step_names": step_names,
            "runs": grid_runs,
        },
        "task_rows": task_rows,
        "graph_nodes": graph_nodes,
    }
