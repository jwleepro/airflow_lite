"""Assemble data for the monitor (runs overview) page."""

from __future__ import annotations

from airflow_lite.api.schemas import build_run_response_with_steps


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
