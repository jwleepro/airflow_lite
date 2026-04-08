from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from airflow_lite.analytics import (
    DatasetSummaryStats,
    SUPPORTED_CHARTS,
    SUPPORTED_DASHBOARDS,
    build_dashboard_definition,
    build_dataset_summary_metrics,
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
    DetailColumnDefinition,
    DetailColumnType,
    DetailQueryRequest,
    DetailQueryResponse,
    DetailSortField,
    ExportCreateRequest,
    ExportFormat,
    FilterOption,
    SortDirection,
    SummaryQueryRequest,
    SummaryQueryResponse,
)
from airflow_lite.i18n import DEFAULT_LANGUAGE, translate


class AnalyticsQueryError(ValueError):
    pass


class AnalyticsDatasetNotFoundError(LookupError):
    pass


class AnalyticsDashboardNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class AnalyticsExportPlan:
    dataset: str
    action_key: str
    format: ExportFormat
    sql: str
    params: list
    file_stem: str


class DuckDBAnalyticsQueryService:
    """Serve read-only analytics responses from the promoted DuckDB mart."""

    SUPPORTED_FILTERS = frozenset({"source", "partition_month"})
    SUPPORTED_DETAILS = frozenset({"source-files"})
    DETAIL_COLUMN_SPECS = {
        "source-files": [
            ("source_name", DetailColumnType.STRING, "analytics.detail.column.source_name"),
            ("partition_month", DetailColumnType.DATE, "analytics.detail.column.partition_month"),
            ("file_path", DetailColumnType.STRING, "analytics.detail.column.file_path"),
            ("row_count", DetailColumnType.INTEGER, "analytics.detail.column.row_count"),
            ("last_build_id", DetailColumnType.STRING, "analytics.detail.column.last_build_id"),
        ]
    }
    DETAIL_SORT_FIELDS = {
        "source-files": {
            "source_name": "source_name",
            "partition_month": "partition_start",
            "file_path": "file_path",
            "row_count": "row_count",
            "last_build_id": "last_build_id",
        }
    }
    EXPORT_ACTIONS = {
        "csv_zip_export": ExportFormat.CSV_ZIP,
        "parquet_export": ExportFormat.PARQUET,
    }
    DEFAULT_DETAIL_SORT = {
        "source-files": [
            DetailSortField(field="partition_month", direction=SortDirection.DESC),
            DetailSortField(field="source_name", direction=SortDirection.ASC),
            DetailSortField(field="file_path", direction=SortDirection.ASC),
        ]
    }

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def query_summary(
        self,
        request: SummaryQueryRequest,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> SummaryQueryResponse:
        self._ensure_supported_filters(request.filters)
        self._ensure_dataset_exists(request.dataset)
        where_sql, params = self._build_file_filters(
            dataset=request.dataset,
            filters=request.filters,
            start=request.window.start if request.window else None,
            end=request.window.end if request.window else None,
        )

        with self._connect(read_only=True) as connection:
            total_rows, total_files, source_tables, min_partition_start, max_partition_start = connection.execute(
                f"""
                SELECT
                    COALESCE(SUM(row_count), 0),
                    COUNT(*),
                    COUNT(DISTINCT source_name),
                    MIN(partition_start),
                    MAX(partition_start)
                FROM mart_dataset_files
                WHERE {where_sql}
                """,
                params,
            ).fetchone()

        stats = DatasetSummaryStats(
            total_rows=int(total_rows),
            total_files=int(total_files),
            source_tables=int(source_tables),
            min_partition_start=min_partition_start,
            max_partition_start=max_partition_start,
        )

        return SummaryQueryResponse(
            dataset=request.dataset,
            generated_at=datetime.now(),
            filters_applied=request.filters,
            metrics=build_dataset_summary_metrics(
                request.dataset,
                stats,
                language=language,
            ),
            warnings=[],
        )

    def query_chart(
        self,
        request: ChartQueryRequest,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> ChartQueryResponse:
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
                    warnings.append(
                        translate("analytics.chart.rows_by_month.granularity_normalized", language)
                    )
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
                series = [
                    ChartSeries(
                        key="rows",
                        label=translate("analytics.chart.series.rows", language),
                        points=points,
                    )
                ]
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
                series = [
                    ChartSeries(
                        key="files",
                        label=translate("analytics.chart.series.files", language),
                        points=points,
                    )
                ]

        return ChartQueryResponse(
            dataset=request.dataset,
            chart_id=request.chart_id,
            title=translate(SUPPORTED_CHARTS[request.chart_id], language),
            granularity=response_granularity,
            filters_applied=request.filters,
            series=series,
            warnings=warnings,
        )

    def query_detail(
        self,
        request: DetailQueryRequest,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> DetailQueryResponse:
        self._ensure_supported_filters(request.filters)
        self._ensure_dataset_exists(request.dataset)
        detail_sql = self._build_detail_select_sql(request.detail_key)
        where_sql, params = self._build_file_filters(
            dataset=request.dataset,
            filters=request.filters,
            start=None,
            end=None,
        )
        sort_fields = request.sort or self.DEFAULT_DETAIL_SORT[request.detail_key]
        order_sql = self._build_detail_sort_sql(request.detail_key, sort_fields)
        offset = (request.page - 1) * request.page_size

        with self._connect(read_only=True) as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM ({detail_sql} WHERE {where_sql}) detail_rows",
                params,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                {detail_sql}
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT ?
                OFFSET ?
                """,
                [*params, request.page_size, offset],
            ).fetchall()

        return DetailQueryResponse(
            dataset=request.dataset,
            detail_key=request.detail_key,
            columns=self._build_detail_columns(request.detail_key, language),
            rows=[
                {
                    "source_name": source_name,
                    "partition_month": partition_month.isoformat() if partition_month else None,
                    "file_path": file_path,
                    "row_count": int(row_count),
                    "last_build_id": last_build_id,
                }
                for source_name, partition_month, file_path, row_count, last_build_id in rows
            ],
            page=request.page,
            page_size=request.page_size,
            total=int(total),
            sort=sort_fields,
            warnings=[],
        )

    def build_export_plan(self, request: ExportCreateRequest) -> AnalyticsExportPlan:
        self._ensure_supported_filters(request.filters)
        self._ensure_dataset_exists(request.dataset)
        expected_format = self.EXPORT_ACTIONS.get(request.action_key)
        if expected_format is None:
            raise AnalyticsQueryError(f"unsupported export action_key: {request.action_key}")
        if request.format != expected_format:
            raise AnalyticsQueryError(
                f"format {request.format.value} does not match action {request.action_key}"
            )

        detail_key = "source-files"
        detail_sql = self._build_detail_select_sql(detail_key)
        where_sql, params = self._build_file_filters(
            dataset=request.dataset,
            filters=request.filters,
            start=None,
            end=None,
        )
        order_sql = self._build_detail_sort_sql(detail_key, self.DEFAULT_DETAIL_SORT[detail_key])

        return AnalyticsExportPlan(
            dataset=request.dataset,
            action_key=request.action_key,
            format=request.format,
            sql=f"{detail_sql} WHERE {where_sql} ORDER BY {order_sql}",
            params=params,
            file_stem=f"{request.dataset}-{detail_key}-{request.action_key}",
        )

    def get_filter_metadata(
        self,
        dataset: str,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> AnalyticsFilterMetadataResponse:
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
            filters=build_filter_definitions(source_options, month_options, language=language),
        )

    def get_dashboard_definition(
        self,
        dashboard_id: str,
        dataset: str,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> DashboardDefinitionResponse:
        self._ensure_dataset_exists(dataset)
        if dashboard_id not in SUPPORTED_DASHBOARDS:
            raise AnalyticsDashboardNotFoundError(f"dashboard not found: {dashboard_id}")

        filter_metadata = self.get_filter_metadata(dataset, language=language)
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
            language=language,
        )

    def _build_detail_columns(self, detail_key: str, language: str) -> list[DetailColumnDefinition]:
        return [
            DetailColumnDefinition(
                key=key,
                label=translate(label_key, language),
                type=column_type,
            )
            for key, column_type, label_key in self.DETAIL_COLUMN_SPECS[detail_key]
        ]

    def _build_detail_select_sql(self, detail_key: str) -> str:
        if detail_key not in self.SUPPORTED_DETAILS:
            raise AnalyticsQueryError(f"unsupported detail_key: {detail_key}")
        return """
            SELECT
                source_name,
                partition_start AS partition_month,
                file_path,
                row_count,
                last_build_id
            FROM mart_dataset_files
        """

    def _build_detail_sort_sql(self, detail_key: str, sort_fields: list[DetailSortField]) -> str:
        allowed_fields = self.DETAIL_SORT_FIELDS.get(detail_key)
        if allowed_fields is None:
            raise AnalyticsQueryError(f"unsupported detail_key: {detail_key}")

        order_terms: list[str] = []
        for sort_field in sort_fields:
            column_name = allowed_fields.get(sort_field.field)
            if column_name is None:
                raise AnalyticsQueryError(
                    f"unsupported sort field for {detail_key}: {sort_field.field}"
                )
            direction = "DESC" if sort_field.direction is SortDirection.DESC else "ASC"
            order_terms.append(f"{column_name} {direction}")

        return ", ".join(order_terms)

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
