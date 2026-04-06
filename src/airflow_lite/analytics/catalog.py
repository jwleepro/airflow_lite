from __future__ import annotations

from airflow_lite.api.analytics_contracts import (
    AnalyticsFilterType,
    DashboardActionScope,
    ChartGranularity,
    DashboardActionDefinition,
    DashboardActionType,
    DashboardChartDefinition,
    DashboardChartType,
    DashboardDefinitionResponse,
    DashboardCardDefinition,
    DashboardLayoutSpan,
    DashboardRequestMethod,
    FilterDefinition,
    FilterOption,
)

SUPPORTED_CHARTS = {
    "rows_by_month": "Rows by Month",
    "files_by_source": "Files by Source",
}

SUPPORTED_DASHBOARDS = {
    "operations_overview": "MES Operations Overview",
}

COMMON_FILTER_KEYS = ["source", "partition_month"]


def build_filter_definitions(
    source_options: list[FilterOption],
    month_options: list[FilterOption],
) -> list[FilterDefinition]:
    return [
        FilterDefinition(
            key="source",
            label="Source Table",
            type=AnalyticsFilterType.MULTI_SELECT,
            supports_multiple=True,
            options=source_options,
        ),
        FilterDefinition(
            key="partition_month",
            label="Partition Month",
            type=AnalyticsFilterType.MULTI_SELECT,
            supports_multiple=True,
            options=month_options,
        ),
    ]


def build_dashboard_definition(
    dashboard_id: str,
    dataset: str,
    filters: list[FilterDefinition],
    last_refreshed_at,
) -> DashboardDefinitionResponse:
    if dashboard_id != "operations_overview":
        raise KeyError(dashboard_id)

    return DashboardDefinitionResponse(
        dashboard_id=dashboard_id,
        title=SUPPORTED_DASHBOARDS[dashboard_id],
        description="Promoted mart coverage and refresh health view for MES datasets.",
        dataset=dataset,
        last_refreshed_at=last_refreshed_at,
        filters=filters,
        cards=[
            DashboardCardDefinition(
                key="rows_loaded",
                label="Rows Loaded",
                metric_key="rows_loaded",
                description="Total rows covered by the current mart selection.",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="source_files",
                label="Source Files",
                metric_key="source_files",
                description="Parquet file count backing the selected view.",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="source_tables",
                label="Source Tables",
                metric_key="source_tables",
                description="Distinct raw sources currently represented in the mart.",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="covered_months",
                label="Covered Months",
                metric_key="covered_months",
                description="Number of month partitions included in the response window.",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
        ],
        charts=[
            DashboardChartDefinition(
                chart_id="rows_by_month",
                title=SUPPORTED_CHARTS["rows_by_month"],
                chart_type=DashboardChartType.LINE,
                default_granularity=ChartGranularity.MONTH,
                query_endpoint="/api/v1/analytics/charts/rows_by_month/query",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                limit=12,
                span=DashboardLayoutSpan.LARGE,
            ),
            DashboardChartDefinition(
                chart_id="files_by_source",
                title=SUPPORTED_CHARTS["files_by_source"],
                chart_type=DashboardChartType.BAR,
                default_granularity=ChartGranularity.MONTH,
                query_endpoint="/api/v1/analytics/charts/files_by_source/query",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                limit=20,
                span=DashboardLayoutSpan.MEDIUM,
            ),
        ],
        drilldown_actions=[
            DashboardActionDefinition(
                key="source_file_detail",
                label="Source File Detail",
                type=DashboardActionType.DRILLDOWN,
                description="Planned detail grid for source-level file records and partition slices.",
                scope=DashboardActionScope.CHART,
                target_key="files_by_source",
                endpoint="/api/v1/analytics/details/source-files/query",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                status_reason="Requires the paginated detail API and chart-to-filter drilldown wiring.",
            ),
        ],
        export_actions=[
            DashboardActionDefinition(
                key="csv_zip_export",
                label="CSV Zip Export",
                type=DashboardActionType.EXPORT,
                scope=DashboardActionScope.DASHBOARD,
                endpoint="/api/v1/analytics/exports",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                format="csv.zip",
                description="Planned large-result export workflow for downstream analysis.",
                status_reason="Requires asynchronous export job creation, polling, and download endpoints.",
            ),
            DashboardActionDefinition(
                key="parquet_export",
                label="Parquet Export",
                type=DashboardActionType.EXPORT,
                scope=DashboardActionScope.DASHBOARD,
                endpoint="/api/v1/analytics/exports",
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                format="parquet",
                description="Planned raw-compatible export for bulk data reuse.",
                status_reason="Requires asynchronous export job creation, polling, and download endpoints.",
            ),
        ],
        warnings=[
            "Planned drilldown and export actions advertise their future endpoints, but the backing APIs are not implemented yet.",
        ],
    )
