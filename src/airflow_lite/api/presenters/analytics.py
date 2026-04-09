"""Assemble data for the analytics dashboard page."""

from __future__ import annotations

from airflow_lite.api.analytics_contracts import (
    ChartQueryRequest,
    DetailQueryRequest,
    SummaryQueryRequest,
)


def extract_selected_filters(source, filter_definitions: list[dict]) -> dict[str, list[str]]:
    getter = source.getlist if hasattr(source, "getlist") else lambda key: source.get(key, [])
    filters: dict[str, list[str]] = {}
    for filter_definition in filter_definitions:
        key = filter_definition["key"]
        values = [value for value in getter(key) if value]
        if values:
            filters[key] = values
    return filters


def extract_detail_key(endpoint: str | None) -> str | None:
    if not endpoint:
        return None
    parts = endpoint.strip("/").split("/")
    try:
        detail_index = parts.index("details")
    except ValueError:
        return None
    if detail_index + 1 >= len(parts):
        return None
    return parts[detail_index + 1]


def build_dashboard_data(
    query_service,
    export_service,
    *,
    dataset: str,
    dashboard_id: str,
    selected_filters_source,
    detail_preview_page_size: int,
    export_jobs_limit: int,
    language: str,
) -> dict:
    """Assemble every payload the analytics dashboard page needs."""
    dashboard = query_service.get_dashboard_definition(
        dashboard_id=dashboard_id,
        dataset=dataset,
        language=language,
    ).model_dump(mode="json")
    selected_filters = extract_selected_filters(selected_filters_source, dashboard["filters"])
    summary = query_service.query_summary(
        SummaryQueryRequest(dataset=dataset, filters=selected_filters),
        language=language,
    ).model_dump(mode="json")

    charts: dict[str, dict] = {}
    for chart_definition in dashboard["charts"]:
        charts[chart_definition["chart_id"]] = query_service.query_chart(
            ChartQueryRequest(
                dataset=dataset,
                chart_id=chart_definition["chart_id"],
                granularity=chart_definition["default_granularity"],
                limit=chart_definition["limit"],
                filters=selected_filters,
            ),
            language=language,
        ).model_dump(mode="json")

    detail_preview = None
    for drilldown_action in dashboard["drilldown_actions"]:
        if drilldown_action["status"] != "available":
            continue
        detail_key = extract_detail_key(drilldown_action.get("endpoint"))
        if not detail_key:
            continue
        detail_preview = query_service.query_detail(
            DetailQueryRequest(
                dataset=dataset,
                detail_key=detail_key,
                filters=selected_filters,
                page=1,
                page_size=detail_preview_page_size,
            ),
            language=language,
        ).model_dump(mode="json")
        break

    export_jobs: list[dict] = []
    if export_service is not None:
        export_jobs = [
            job.model_dump(mode="json")
            for job in export_service.list_jobs(dataset=dataset, limit=export_jobs_limit)
        ]

    return {
        "dashboard": dashboard,
        "summary": summary,
        "charts": charts,
        "detail_preview": detail_preview,
        "filters_applied": selected_filters,
        "export_jobs": export_jobs,
    }
