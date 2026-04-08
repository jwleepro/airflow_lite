from __future__ import annotations

from airflow_lite.api.paths import (
    ANALYTICS_EXPORTS_PATH,
    chart_query_path,
    detail_query_path,
)
from airflow_lite.api.analytics_contracts import (
    AnalyticsFilterType,
    DashboardActionScope,
    DashboardActionStatus,
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
from airflow_lite.i18n import DEFAULT_LANGUAGE, translate

SUPPORTED_CHARTS = {
    "rows_by_month": "analytics.chart.rows_by_month.title",
    "files_by_source": "analytics.chart.files_by_source.title",
}

SUPPORTED_DASHBOARDS = {
    "operations_overview": "analytics.dashboard.operations_overview.title",
}

COMMON_FILTER_KEYS = ["source", "partition_month"]


def build_filter_definitions(
    source_options: list[FilterOption],
    month_options: list[FilterOption],
    *,
    language: str = DEFAULT_LANGUAGE,
) -> list[FilterDefinition]:
    return [
        FilterDefinition(
            key="source",
            label=translate("analytics.filter.source.label", language),
            type=AnalyticsFilterType.MULTI_SELECT,
            supports_multiple=True,
            options=source_options,
        ),
        FilterDefinition(
            key="partition_month",
            label=translate("analytics.filter.partition_month.label", language),
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
    *,
    language: str = DEFAULT_LANGUAGE,
) -> DashboardDefinitionResponse:
    if dashboard_id != "operations_overview":
        raise KeyError(dashboard_id)

    return DashboardDefinitionResponse(
        dashboard_id=dashboard_id,
        title=translate(SUPPORTED_DASHBOARDS[dashboard_id], language),
        description=translate("analytics.dashboard.operations_overview.description", language),
        dataset=dataset,
        last_refreshed_at=last_refreshed_at,
        filters=filters,
        cards=[
            DashboardCardDefinition(
                key="rows_loaded",
                label=translate("analytics.dashboard.card.rows_loaded.label", language),
                metric_key="rows_loaded",
                description=translate("analytics.dashboard.card.rows_loaded.description", language),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="source_files",
                label=translate("analytics.dashboard.card.source_files.label", language),
                metric_key="source_files",
                description=translate("analytics.dashboard.card.source_files.description", language),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="source_tables",
                label=translate("analytics.dashboard.card.source_tables.label", language),
                metric_key="source_tables",
                description=translate("analytics.dashboard.card.source_tables.description", language),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="covered_months",
                label=translate("analytics.dashboard.card.covered_months.label", language),
                metric_key="covered_months",
                description=translate("analytics.dashboard.card.covered_months.description", language),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
            DashboardCardDefinition(
                key="avg_rows_per_file",
                label=translate("analytics.dashboard.card.avg_rows_per_file.label", language),
                metric_key="avg_rows_per_file",
                description=translate("analytics.dashboard.card.avg_rows_per_file.description", language),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                span=DashboardLayoutSpan.SMALL,
            ),
        ],
        charts=[
            DashboardChartDefinition(
                chart_id="rows_by_month",
                title=translate(SUPPORTED_CHARTS["rows_by_month"], language),
                chart_type=DashboardChartType.LINE,
                default_granularity=ChartGranularity.MONTH,
                query_endpoint=chart_query_path("rows_by_month"),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                limit=12,
                span=DashboardLayoutSpan.LARGE,
            ),
            DashboardChartDefinition(
                chart_id="files_by_source",
                title=translate(SUPPORTED_CHARTS["files_by_source"], language),
                chart_type=DashboardChartType.BAR,
                default_granularity=ChartGranularity.MONTH,
                query_endpoint=chart_query_path("files_by_source"),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                limit=20,
                span=DashboardLayoutSpan.MEDIUM,
            ),
        ],
        drilldown_actions=[
            DashboardActionDefinition(
                key="source_file_detail",
                label=translate("analytics.action.source_file_detail.label", language),
                type=DashboardActionType.DRILLDOWN,
                status=DashboardActionStatus.AVAILABLE,
                description=translate("analytics.action.source_file_detail.description", language),
                scope=DashboardActionScope.CHART,
                target_key="files_by_source",
                endpoint=detail_query_path("source-files"),
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
            ),
        ],
        export_actions=[
            DashboardActionDefinition(
                key="csv_zip_export",
                label=translate("analytics.action.csv_zip_export.label", language),
                type=DashboardActionType.EXPORT,
                status=DashboardActionStatus.AVAILABLE,
                scope=DashboardActionScope.DASHBOARD,
                endpoint=ANALYTICS_EXPORTS_PATH,
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                format="csv.zip",
                description=translate("analytics.action.csv_zip_export.description", language),
            ),
            DashboardActionDefinition(
                key="parquet_export",
                label=translate("analytics.action.parquet_export.label", language),
                type=DashboardActionType.EXPORT,
                status=DashboardActionStatus.AVAILABLE,
                scope=DashboardActionScope.DASHBOARD,
                endpoint=ANALYTICS_EXPORTS_PATH,
                request_method=DashboardRequestMethod.POST,
                filter_keys=COMMON_FILTER_KEYS,
                format="parquet",
                description=translate("analytics.action.parquet_export.description", language),
            ),
        ],
        warnings=[],
    )
