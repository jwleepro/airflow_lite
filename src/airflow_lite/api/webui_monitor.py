"""Monitor home and pipeline list page renderers."""

from __future__ import annotations

from airflow_lite.api.paths import (
    MONITOR_ADMIN_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_PATH,
    MONITOR_PIPELINES_PATH,
    PIPELINES_PATH,
)
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import build_url, cfg, fmt, t
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


def _latest_finish(pipeline_rows: list[dict]) -> str | None:
    return max(
        (
            (row.get("latest_run") or {}).get("finished_at")
            for row in pipeline_rows
            if (row.get("latest_run") or {}).get("finished_at")
        ),
        default=None,
    )


def _build_first_failed_errors(
    pipeline_rows: list[dict],
    *,
    error_message_max_length: int,
) -> dict[str, str]:
    first_failed_errors: dict[str, str] = {}
    for row in pipeline_rows:
        if latest_run_status(row) == "failed":
            err = _first_failed_step_error(
                row.get("latest_run") or {},
                max_length=error_message_max_length,
            )
            if err:
                first_failed_errors[row["name"]] = err
    return first_failed_errors


def _build_monitor_notice(
    pipeline_rows: list[dict],
    *,
    language: str,
    monitor_refresh_seconds: int,
) -> str:
    return t(
        language,
        "webui.monitor.inventory.refresh_notice",
        latest_finish=fmt(_latest_finish(pipeline_rows), fallback=t(language, "webui.monitor.inventory.none")),
        seconds=monitor_refresh_seconds,
    )


def _filter_pipeline_rows(
    pipeline_rows: list[dict],
    *,
    search_query: str = "",
    state: str = "all",
) -> list[dict]:
    query = search_query.strip().lower()

    def _matches_query(row: dict) -> bool:
        if not query:
            return True
        haystack = " ".join(
            str(row.get(key) or "").lower()
            for key in ("name", "table", "strategy", "schedule")
        )
        return query in haystack

    def _matches_state(row: dict) -> bool:
        if state not in {"ok", "warn", "bad"}:
            return True
        return latest_run_status(row) in {
            status
            for status, tone in (
                ("success", "ok"),
                ("completed", "ok"),
                ("running", "warn"),
                ("pending", "warn"),
                ("queued", "warn"),
                ("failed", "bad"),
            )
            if tone == state
        }

    return [
        row for row in pipeline_rows
        if _matches_query(row) and _matches_state(row)
    ]


def _recent_activity_rows(pipeline_rows: list[dict], *, limit: int) -> list[dict]:
    recent_rows: list[dict] = []
    for row in pipeline_rows:
        for run in row.get("recent_runs") or []:
            recent_rows.append(
                {
                    "pipeline_name": row["name"],
                    "table": row.get("table"),
                    "run_id": run.get("id"),
                    "execution_date": run.get("execution_date"),
                    "status": run.get("status"),
                    "trigger_type": run.get("trigger_type"),
                    "started_at": run.get("started_at"),
                    "finished_at": run.get("finished_at"),
                }
            )

    recent_rows.sort(
        key=lambda item: item.get("finished_at") or item.get("started_at") or item.get("execution_date") or "",
        reverse=True,
    )
    return recent_rows[:limit]


def render_monitor_home_page(
    pipeline_rows: list[dict],
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
    health_checks: list[dict] | None = None,
) -> str:
    monitor_refresh_seconds = cfg(webui_config, "monitor_refresh_seconds", 30)
    recent_activity_limit = cfg(webui_config, "recent_runs_limit", 10)
    tone_counts = count_by_tone(pipeline_rows)

    chrome = PageChrome(
        title=t(language, "webui.monitor.home.title"),
        subtitle=t(language, "webui.monitor.home.subtitle"),
        active_path=MONITOR_PATH,
        page_tag=t(language, "webui.layout.header_tag.ops_console"),
        auto_refresh_seconds=monitor_refresh_seconds,
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), None),
        ],
        hero_links=[
            (t(language, "webui.layout.nav.pipelines"), MONITOR_PIPELINES_PATH),
            (t(language, "webui.monitor.hero.analytics"), MONITOR_ANALYTICS_PATH),
            (t(language, "webui.layout.nav.admin"), MONITOR_ADMIN_PATH),
        ],
    )
    return render_page(
        "home.html",
        chrome=chrome,
        language=language,
        total_pipelines=len(pipeline_rows),
        active_runs=tone_counts["warn"],
        healthy_runs=tone_counts["ok"],
        failed_runs=tone_counts["bad"],
        health_checks=health_checks or [],
        monitor_notice=_build_monitor_notice(
            pipeline_rows,
            language=language,
            monitor_refresh_seconds=monitor_refresh_seconds,
        ),
        quick_links=[
            {
                "label": t(language, "webui.monitor.home.quick_links.all"),
                "href": build_url(MONITOR_PIPELINES_PATH),
                "count": len(pipeline_rows),
                "tone": "neutral",
            },
            {
                "label": t(language, "webui.monitor.home.quick_links.failed"),
                "href": build_url(MONITOR_PIPELINES_PATH, state="bad"),
                "count": tone_counts["bad"],
                "tone": "bad",
            },
            {
                "label": t(language, "webui.monitor.home.quick_links.active"),
                "href": build_url(MONITOR_PIPELINES_PATH, state="warn"),
                "count": tone_counts["warn"],
                "tone": "warn",
            },
            {
                "label": t(language, "webui.monitor.home.quick_links.healthy"),
                "href": build_url(MONITOR_PIPELINES_PATH, state="ok"),
                "count": tone_counts["ok"],
                "tone": "ok",
            },
        ],
        recent_activity_rows=_recent_activity_rows(
            pipeline_rows,
            limit=recent_activity_limit,
        ),
    )


def render_pipeline_list_page(
    pipeline_rows: list[dict],
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
    search_query: str = "",
    state: str = "all",
    pipeline_actions: dict[str, dict] | None = None,
) -> str:
    monitor_refresh_seconds = cfg(webui_config, "monitor_refresh_seconds", 30)
    error_message_max_length = cfg(webui_config, "error_message_max_length", 120)
    filtered_rows = _filter_pipeline_rows(
        pipeline_rows,
        search_query=search_query,
        state=state,
    )

    chrome = PageChrome(
        title=t(language, "webui.monitor.list.title"),
        subtitle=t(language, "webui.monitor.list.subtitle"),
        active_path=MONITOR_PIPELINES_PATH,
        page_tag=t(language, "webui.layout.page_tag.pipelines"),
        auto_refresh_seconds=monitor_refresh_seconds,
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, "webui.layout.nav.pipelines"), None),
        ],
        hero_links=[
            (t(language, "webui.monitor.hero.pipelines_api"), PIPELINES_PATH),
            (t(language, "webui.monitor.hero.analytics"), MONITOR_ANALYTICS_PATH),
            (t(language, "webui.monitor.hero.exports"), MONITOR_EXPORTS_PATH),
        ],
    )
    return render_page(
        "monitor.html",
        chrome=chrome,
        language=language,
        pipeline_rows=filtered_rows,
        pipeline_actions=pipeline_actions or {},
        total_pipelines=len(filtered_rows),
        active_runs=count_by_tone(filtered_rows)["warn"],
        healthy_runs=count_by_tone(filtered_rows)["ok"],
        failed_runs=count_by_tone(filtered_rows)["bad"],
        monitor_notice=_build_monitor_notice(
            pipeline_rows,
            language=language,
            monitor_refresh_seconds=monitor_refresh_seconds,
        ),
        first_failed_errors=_build_first_failed_errors(
            filtered_rows,
            error_message_max_length=error_message_max_length,
        ),
        search_query=search_query,
        selected_state=state if state in {"ok", "warn", "bad"} else "all",
        filter_reset_href_raw=build_url(MONITOR_PIPELINES_PATH),
        filter_summary=t(
            language,
            "webui.monitor.list.filter.summary",
            count=len(filtered_rows),
        ),
    )
