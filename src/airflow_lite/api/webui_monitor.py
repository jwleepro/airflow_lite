"""Monitor (pipelines overview) page renderer.

Delegates HTML production to `templates/monitor.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import cfg, fmt, t
from airflow_lite.api.webui_status import count_by_tone, latest_run_status
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
    tone_counts = count_by_tone(pipeline_rows)
    active_runs = tone_counts["warn"]
    healthy_runs = tone_counts["ok"]
    failed_runs = tone_counts["bad"]

    latest_finish = max(
        (
            (row.get("latest_run") or {}).get("finished_at")
            for row in pipeline_rows
            if (row.get("latest_run") or {}).get("finished_at")
        ),
        default=None,
    )

    first_failed_errors: dict[str, str] = {}
    for row in pipeline_rows:
        if latest_run_status(row) == "failed":
            err = _first_failed_step_error(
                row.get("latest_run") or {},
                max_length=error_message_max_length,
            )
            if err:
                first_failed_errors[row["name"]] = err

    monitor_notice = t(
        language,
        "webui.monitor.inventory.refresh_notice",
        latest_finish=fmt(latest_finish, fallback=t(language, "webui.monitor.inventory.none")),
        seconds=monitor_refresh_seconds,
    )

    chrome = PageChrome(
        title=t(language, "webui.monitor.title"),
        subtitle=t(language, "webui.monitor.subtitle"),
        active_path=MONITOR_PATH,
        auto_refresh_seconds=monitor_refresh_seconds,
    )
    return render_page(
        "monitor.html",
        chrome=chrome,
        language=language,
        pipeline_rows=pipeline_rows,
        total_pipelines=total_pipelines,
        active_runs=active_runs,
        healthy_runs=healthy_runs,
        failed_runs=failed_runs,
        monitor_notice=monitor_notice,
        first_failed_errors=first_failed_errors,
    )
