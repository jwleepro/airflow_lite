"""Analytics dashboard & unavailable page renderers.

Delegate HTML production to `templates/analytics.html` and
`templates/unavailable.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import (
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    dashboard_definition_path,
)
from airflow_lite.api.template_env import render
from airflow_lite.api.webui_helpers import cfg, t
from airflow_lite.i18n import DEFAULT_LANGUAGE


def render_unavailable_page(
    title: str,
    message: str,
    *,
    active_path: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    return render(
        "unavailable.html",
        language=language,
        title=title,
        subtitle=message,
        active_path=active_path,
        hero_links=[],
        page_tag=t(language, "webui.layout.page_tag.service_status"),
        auto_refresh_seconds=None,
        message=message,
    )


def render_analytics_dashboard_page(
    page: dict,
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    analytics_refresh_seconds = cfg(webui_config, "analytics_refresh_seconds", 60)
    dashboard = page["dashboard"]
    summary = page["summary"]
    charts = page["charts"]
    detail_preview = page["detail_preview"]
    filters_applied = page["filters_applied"]
    export_jobs = page["export_jobs"]
    dashboard_id = dashboard["dashboard_id"]
    dataset = dashboard["dataset"]

    filter_key_map = {item["key"]: item["label"] for item in dashboard["filters"]}
    metric_map = {m["key"]: m for m in summary["metrics"]}
    active_filter_count = sum(len(v) for v in filters_applied.values())

    analytics_refresh_notice = t(
        language,
        "webui.analytics.metadata.refresh_notice",
        seconds=analytics_refresh_seconds,
    )
    reset_href_raw = f"{MONITOR_ANALYTICS_PATH}?dataset={dataset}&dashboard_id={dashboard_id}"
    dashboard_api_href_raw = f"{dashboard_definition_path(dashboard_id)}?dataset={dataset}"
    full_export_monitor_href_raw = f"{MONITOR_EXPORTS_PATH}?dataset={dataset}"

    return render(
        "analytics.html",
        language=language,
        title=t(language, "webui.analytics.title"),
        subtitle=t(language, "webui.analytics.subtitle"),
        active_path=MONITOR_ANALYTICS_PATH,
        hero_links=[],
        page_tag=t(language, "webui.layout.page_tag.analytics_workspace"),
        auto_refresh_seconds=analytics_refresh_seconds,
        dashboard=dashboard,
        dashboard_id=dashboard_id,
        dataset=dataset,
        charts=charts,
        detail_preview=detail_preview,
        filters_applied=filters_applied,
        filter_key_map=filter_key_map,
        metric_map=metric_map,
        export_jobs=export_jobs,
        active_filter_count=active_filter_count,
        analytics_refresh_notice=analytics_refresh_notice,
        reset_href_raw=reset_href_raw,
        dashboard_api_href_raw=dashboard_api_href_raw,
        full_export_monitor_href_raw=full_export_monitor_href_raw,
    )
