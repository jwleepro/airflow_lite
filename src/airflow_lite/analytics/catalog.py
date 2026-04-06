from __future__ import annotations

from airflow_lite.api.analytics_contracts import (
    AnalyticsFilterType,
    ChartGranularity,
    DashboardActionDefinition,
    DashboardActionType,
    DashboardChartDefinition,
    DashboardChartType,
    DashboardDefinitionResponse,
    DashboardCardDefinition,
    DashboardLayoutSpan,
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
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="source_files",
                label="Source Files",
                metric_key="source_files",
                description="Parquet file count backing the selected view.",
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="source_tables",
                label="Source Tables",
                metric_key="source_tables",
                description="Distinct raw sources currently represented in the mart.",
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="covered_months",
                label="Covered Months",
                metric_key="covered_months",
                description="Number of month partitions included in the response window.",
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
                limit=12,
                span=DashboardLayoutSpan.LARGE,
            ),
            DashboardChartDefinition(
                chart_id="files_by_source",
                title=SUPPORTED_CHARTS["files_by_source"],
                chart_type=DashboardChartType.BAR,
                default_granularity=ChartGranularity.MONTH,
                query_endpoint="/api/v1/analytics/charts/files_by_source/query",
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
            ),
        ],
        export_actions=[
            DashboardActionDefinition(
                key="csv_zip_export",
                label="CSV Zip Export",
                type=DashboardActionType.EXPORT,
                format="csv.zip",
                description="Planned large-result export workflow for downstream analysis.",
            ),
            DashboardActionDefinition(
                key="parquet_export",
                label="Parquet Export",
                type=DashboardActionType.EXPORT,
                format="parquet",
                description="Planned raw-compatible export for bulk data reuse.",
            ),
        ],
        warnings=[
            "Detail drilldown and export jobs are planned follow-up work and are not executable yet.",
        ],
    )
