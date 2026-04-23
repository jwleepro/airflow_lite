"""Analytics dashboard & unavailable page renderers.

Delegate HTML production to `templates/analytics.html` and
`templates/unavailable.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import (
    ANALYTICS_FILTERS_PATH,
    MONITOR_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    dashboard_definition_path,
)
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import build_url, cfg, t
from airflow_lite.i18n import DEFAULT_LANGUAGE


def render_unavailable_page(
    title: str,
    message: str,
    *,
    active_path: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    chrome = PageChrome(
        title=title,
        subtitle=message,
        active_path=active_path,
        page_tag=t(language, "webui.layout.page_tag.service_status"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (title, None),
        ],
    )
    return render_page(
        "unavailable.html",
        chrome=chrome,
        language=language,
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
    reset_href_raw = build_url(
        MONITOR_ANALYTICS_PATH, dataset=dataset, dashboard_id=dashboard_id
    )
    dashboard_api_href_raw = build_url(
        dashboard_definition_path(dashboard_id), dataset=dataset
    )
    full_export_monitor_href_raw = build_url(MONITOR_EXPORTS_PATH, dataset=dataset)

    chrome = PageChrome(
        title=t(language, "webui.analytics.title"),
        subtitle=t(language, "webui.analytics.subtitle"),
        active_path=MONITOR_ANALYTICS_PATH,
        page_tag=t(language, "webui.layout.page_tag.analytics_workspace"),
        auto_refresh_seconds=analytics_refresh_seconds,
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, "webui.layout.nav.analytics"), None),
        ],
        hero_links=[
            (t(language, "webui.analytics.hero.dashboard_api"), dashboard_api_href_raw),
            (t(language, "webui.analytics.hero.filters_api"), build_url(ANALYTICS_FILTERS_PATH, dataset=dataset)),
            (t(language, "webui.analytics.hero.export_monitor"), full_export_monitor_href_raw),
        ],
    )
    return render_page(
        "analytics.html",
        chrome=chrome,
        language=language,
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
