from __future__ import annotations

from airflow_lite.api.analytics_contracts import (
    AnalyticsFilterType,
    FilterDefinition,
    FilterOption,
)

SUPPORTED_CHARTS = {
    "rows_by_month": "Rows by Month",
    "files_by_source": "Files by Source",
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
