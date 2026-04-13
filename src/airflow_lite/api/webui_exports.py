"""Export jobs page renderer.

Delegates HTML production to `templates/exports.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import (
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
)
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import build_url, cfg, fmt, t
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
    analytics_href_raw = build_url(MONITOR_ANALYTICS_PATH, dataset=dataset)

    chrome = PageChrome(
        title=t(language, "webui.exports.title"),
        subtitle=t(language, "webui.exports.subtitle"),
        active_path=MONITOR_EXPORTS_PATH,
        page_tag=t(language, "webui.layout.page_tag.export_workspace"),
        auto_refresh_seconds=refresh_secs,
        hero_links=[
            (t(language, "webui.exports.hero.analytics"), analytics_href_raw),
            (t(language, "webui.exports.hero.export_api"), "/api/v1/analytics/exports"),
        ],
    )
    return render_page(
        "exports.html",
        chrome=chrome,
        language=language,
        jobs=jobs,
        selected_job_id=selected_job_id,
        counts=counts,
        dataset=dataset,
        retention_hours=retention_hours,
        refresh_notice=refresh_notice,
        retention_description=retention_description,
        analytics_href_raw=analytics_href_raw,
    )
