"""Monitor (pipelines overview) page renderer.

Delegates HTML production to `templates/monitor.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import render
from airflow_lite.api.webui_helpers import cfg, fmt, t
from airflow_lite.i18n import DEFAULT_LANGUAGE


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

    first_failed_errors: dict[str, str] = {}
    for row in pipeline_rows:
        latest = row.get("latest_run") or {}
        if latest.get("status") == "failed":
            err = _first_failed_step_error(latest, max_length=error_message_max_length)
            if err:
                first_failed_errors[row["name"]] = err

    monitor_notice = t(
        language,
        "webui.monitor.inventory.refresh_notice",
        latest_finish=fmt(latest_finish, fallback=t(language, "webui.monitor.inventory.none")),
        seconds=monitor_refresh_seconds,
    )

    return render(
        "monitor.html",
        language=language,
        title=t(language, "webui.monitor.title"),
        subtitle=t(language, "webui.monitor.subtitle"),
        active_path=MONITOR_PATH,
        hero_links=[],
        page_tag=None,
        auto_refresh_seconds=monitor_refresh_seconds,
        pipeline_rows=pipeline_rows,
        total_pipelines=total_pipelines,
        active_runs=active_runs,
        healthy_runs=healthy_runs,
        failed_runs=failed_runs,
        monitor_notice=monitor_notice,
        first_failed_errors=first_failed_errors,
    )
