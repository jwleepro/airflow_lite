from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from airflow_lite.analytics import (
    SUPPORTED_CHARTS,
    SUPPORTED_DASHBOARDS,
    build_dashboard_definition,
    build_filter_definitions,
)
from airflow_lite.api.analytics_contracts import (
    AnalyticsFilterMetadataResponse,
    ChartGranularity,
    ChartPoint,
    ChartQueryRequest,
    ChartQueryResponse,
    ChartSeries,
    DashboardDefinitionResponse,
    FilterOption,
    SummaryMetricCard,
    SummaryPrecision,
    SummaryQueryRequest,
    SummaryQueryResponse,
)


class AnalyticsQueryError(ValueError):
    pass


class AnalyticsDatasetNotFoundError(LookupError):
    pass


class AnalyticsDashboardNotFoundError(LookupError):
    pass


class DuckDBAnalyticsQueryService:
    """Serve read-only analytics responses from the promoted DuckDB mart."""

    SUPPORTED_FILTERS = frozenset({"source", "partition_month"})

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def query_summary(self, request: SummaryQueryRequest) -> SummaryQueryResponse:
        self._ensure_supported_filters(request.filters)
        self._ensure_dataset_exists(request.dataset)
        where_sql, params = self._build_file_filters(
            dataset=request.dataset,
            filters=request.filters,
            start=request.window.start if request.window else None,
            end=request.window.end if request.window else None,
        )

        with self._connect(read_only=True) as connection:
            total_rows, total_files, source_tables, covered_months, average_rows = connection.execute(
                f"""
                SELECT
                    COALESCE(SUM(row_count), 0),
                    COUNT(*),
                    COUNT(DISTINCT source_name),
                    COUNT(DISTINCT partition_start),
                    COALESCE(AVG(row_count), 0)
                FROM mart_dataset_files
                WHERE {where_sql}
                """,
                params,
            ).fetchone()

        return SummaryQueryResponse(
            dataset=request.dataset,
            generated_at=datetime.now(),
            filters_applied=request.filters,
            metrics=[
                SummaryMetricCard(
                    key="rows_loaded",
                    label="Rows Loaded",
                    value=int(total_rows),
                    precision=SummaryPrecision.INTEGER,
                    unit="rows",
                ),
                SummaryMetricCard(
                    key="source_files",
                    label="Source Files",
                    value=int(total_files),
                    precision=SummaryPrecision.INTEGER,
                    unit="files",
                ),
                SummaryMetricCard(
                    key="source_tables",
                    label="Source Tables",
                    value=int(source_tables),
                    precision=SummaryPrecision.INTEGER,
                    unit="tables",
                ),
                SummaryMetricCard(
                    key="avg_rows_per_file",
                    label="Avg Rows per File",
                    value=round(float(average_rows), 2),
                    precision=SummaryPrecision.DECIMAL,
                    unit="rows",
                ),
                SummaryMetricCard(
                    key="covered_months",
                    label="Covered Months",
                    value=int(covered_months),
                    precision=SummaryPrecision.INTEGER,
                    unit="months",
                ),
            ],
            warnings=[],
        )

    def query_chart(self, request: ChartQueryRequest) -> ChartQueryResponse:
        self._ensure_supported_filters(request.filters)
        self._ensure_dataset_exists(request.dataset)
        if request.chart_id not in SUPPORTED_CHARTS:
            raise AnalyticsQueryError(f"unsupported chart_id: {request.chart_id}")

        where_sql, params = self._build_file_filters(
            dataset=request.dataset,
            filters=request.filters,
            start=request.window.start if request.window else None,
            end=request.window.end if request.window else None,
        )
        warnings: list[str] = []
        response_granularity = request.granularity
        with self._connect(read_only=True) as connection:
            if request.chart_id == "rows_by_month":
                if request.granularity.value != "month":
                    warnings.append("rows_by_month uses month buckets; granularity was normalized to month.")
                    response_granularity = ChartGranularity.MONTH
                rows = connection.execute(
                    f"""
                    SELECT
                        strftime(partition_start, '%Y-%m-01') AS bucket,
                        SUM(row_count) AS value
                    FROM mart_dataset_files
                    WHERE {where_sql}
                    GROUP BY partition_start
                    ORDER BY partition_start DESC
                    LIMIT ?
                    """,
                    [*params, request.limit],
                ).fetchall()
                points = [
                    ChartPoint(bucket=bucket, value=int(value))
                    for bucket, value in reversed(rows)
                ]
                series = [ChartSeries(key="rows", label="Rows Loaded", points=points)]
            else:
                rows = connection.execute(
                    f"""
                    SELECT source_name, COUNT(*) AS value
                    FROM mart_dataset_files
                    WHERE {where_sql}
                    GROUP BY source_name
                    ORDER BY value DESC, source_name ASC
                    LIMIT ?
                    """,
                    [*params, request.limit],
                ).fetchall()
                points = [
                    ChartPoint(bucket=source_name, value=int(value), label=source_name)
                    for source_name, value in rows
                ]
                series = [ChartSeries(key="files", label="Files", points=points)]

        return ChartQueryResponse(
            dataset=request.dataset,
            chart_id=request.chart_id,
            title=SUPPORTED_CHARTS[request.chart_id],
            granularity=response_granularity,
            filters_applied=request.filters,
            series=series,
            warnings=warnings,
        )

    def get_filter_metadata(self, dataset: str) -> AnalyticsFilterMetadataResponse:
        self._ensure_dataset_exists(dataset)
        with self._connect(read_only=True) as connection:
            source_rows = connection.execute(
                """
                SELECT DISTINCT source_name
                FROM mart_dataset_sources
                WHERE dataset_name = ?
                ORDER BY source_name
                """,
                [dataset],
            ).fetchall()
            month_rows = connection.execute(
                """
                SELECT DISTINCT strftime(partition_start, '%Y-%m')
                FROM mart_dataset_files
                WHERE dataset_name = ?
                ORDER BY 1 DESC
                """,
                [dataset],
            ).fetchall()

        source_options = [FilterOption(value=value, label=value) for (value,) in source_rows]
        month_options = [FilterOption(value=value, label=value) for (value,) in month_rows]
        return AnalyticsFilterMetadataResponse(
            dataset=dataset,
            filters=build_filter_definitions(source_options, month_options),
        )

    def get_dashboard_definition(self, dashboard_id: str, dataset: str) -> DashboardDefinitionResponse:
        self._ensure_dataset_exists(dataset)
        if dashboard_id not in SUPPORTED_DASHBOARDS:
            raise AnalyticsDashboardNotFoundError(f"dashboard not found: {dashboard_id}")

        filter_metadata = self.get_filter_metadata(dataset)
        with self._connect(read_only=True) as connection:
            last_refreshed_at = connection.execute(
                """
                SELECT last_refreshed_at
                FROM mart_datasets
                WHERE dataset_name = ?
                """,
                [dataset],
            ).fetchone()[0]

        return build_dashboard_definition(
            dashboard_id=dashboard_id,
            dataset=dataset,
            filters=filter_metadata.filters,
            last_refreshed_at=last_refreshed_at,
        )

    def _ensure_supported_filters(self, filters: dict[str, list[str]]) -> None:
        unsupported = sorted(set(filters) - self.SUPPORTED_FILTERS)
        if unsupported:
            raise AnalyticsQueryError(f"unsupported filters: {', '.join(unsupported)}")

    def _ensure_dataset_exists(self, dataset: str) -> None:
        if not self.database_path.exists():
            raise AnalyticsDatasetNotFoundError(f"mart database is missing: {self.database_path}")

        with self._connect(read_only=True) as connection:
            dataset_exists = connection.execute(
                "SELECT COUNT(*) FROM mart_datasets WHERE dataset_name = ?",
                [dataset],
            ).fetchone()[0]
        if not dataset_exists:
            raise AnalyticsDatasetNotFoundError(f"dataset not found: {dataset}")

    @contextmanager
    def _connect(self, read_only: bool):
        import duckdb

        connection = duckdb.connect(str(self.database_path), read_only=read_only)
        try:
            yield connection
        finally:
            connection.close()

    def _build_file_filters(
        self,
        dataset: str,
        filters: dict[str, list[str]],
        start: date | None,
        end: date | None,
    ) -> tuple[str, list]:
        conditions = ["dataset_name = ?"]
        params: list = [dataset]

        if start is not None:
            conditions.append("partition_start >= ?")
            params.append(date(start.year, start.month, 1))
        if end is not None:
            conditions.append("partition_start <= ?")
            params.append(date(end.year, end.month, 1))
        if filters.get("source"):
            placeholders = ", ".join("?" for _ in filters["source"])
            conditions.append(f"source_name IN ({placeholders})")
            params.extend(filters["source"])
        if filters.get("partition_month"):
            month_values = [self._parse_partition_month(value) for value in filters["partition_month"]]
            placeholders = ", ".join("?" for _ in month_values)
            conditions.append(f"partition_start IN ({placeholders})")
            params.extend(month_values)

        return " AND ".join(conditions), params

    @staticmethod
    def _parse_partition_month(value: str) -> date:
        try:
            year_text, month_text = value.split("-", maxsplit=1)
            return date(int(year_text), int(month_text), 1)
        except ValueError as exc:
            raise AnalyticsQueryError(f"invalid partition_month filter value: {value}") from exc
