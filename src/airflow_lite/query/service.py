from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from airflow_lite.analytics import (
    DatasetSummaryStats,
    SUPPORTED_CHARTS,
    SUPPORTED_DASHBOARDS,
    build_dashboard_definition,
    build_dataset_summary_metrics,
    build_filter_definitions,
)
from airflow_lite.query.connection import DuckDBConnectionManager
from airflow_lite.query.contracts import (
    AnalyticsFilterMetadataResponse,
    ChartGranularity,
    ChartPoint,
    ChartQueryRequest,
    ChartQueryResponse,
    ChartSeries,
    DashboardDefinitionResponse,
    DetailQueryRequest,
    DetailQueryResponse,
    ExportCreateRequest,
    ExportFormat,
    FilterOption,
    SummaryQueryRequest,
    SummaryQueryResponse,
)
from airflow_lite.logging_config.decorators import log_execution
from airflow_lite.query.chart_handlers import CHART_HANDLERS
from airflow_lite.query.sql_builder import AnalyticsQueryError, AnalyticsSQLBuilder
from airflow_lite.i18n import DEFAULT_LANGUAGE, translate

logger = logging.getLogger("airflow_lite.query.service")


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
    """Serve read-only analytics responses from the promoted DuckDB mart.

    커넥션 관리는 DuckDBConnectionManager에, SQL 빌드는 AnalyticsSQLBuilder에 위임한다.
    이 클래스는 쿼리 오케스트레이션(검증→빌드→실행→응답조립) 역할만 담당한다.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        connection_manager: DuckDBConnectionManager | None = None,
        sql_builder: AnalyticsSQLBuilder | None = None,
    ):
        self.database_path = Path(database_path)
        self._conn = connection_manager or DuckDBConnectionManager(database_path)
        self._sql = sql_builder or AnalyticsSQLBuilder()

    @log_execution(log_args=True, level=logging.INFO)
    def query_summary(
        self,
        request: SummaryQueryRequest,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> SummaryQueryResponse:
        where_sql, params = self._prepare_file_query(
            request.dataset, request.filters,
            start=request.window.start if request.window else None,
            end=request.window.end if request.window else None,
        )

        with self._conn.connect(read_only=True) as connection:
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

    @log_execution(log_args=True, level=logging.INFO)
    def query_chart(
        self,
        request: ChartQueryRequest,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> ChartQueryResponse:
        if request.chart_id not in SUPPORTED_CHARTS:
            raise AnalyticsQueryError(f"unsupported chart_id: {request.chart_id}")

        handler = CHART_HANDLERS.get(request.chart_id)
        if handler is None:
            raise AnalyticsQueryError(
                f"no handler for chart_id: {request.chart_id}"
            )

        where_sql, params = self._prepare_file_query(
            request.dataset, request.filters,
            start=request.window.start if request.window else None,
            end=request.window.end if request.window else None,
        )

        with self._conn.connect(read_only=True) as connection:
            return handler.handle(request, connection, where_sql, params, language)

    @log_execution(log_args=True, level=logging.INFO)
    def query_detail(
        self,
        request: DetailQueryRequest,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> DetailQueryResponse:
        detail_sql = self._sql.build_detail_select_sql(request.detail_key)
        where_sql, params = self._prepare_file_query(request.dataset, request.filters)
        sort_fields = request.sort or self._sql.DEFAULT_DETAIL_SORT[request.detail_key]
        order_sql = self._sql.build_detail_sort_sql(request.detail_key, sort_fields)
        offset = (request.page - 1) * request.page_size

        with self._conn.connect(read_only=True) as connection:
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

        def _translate(key: str) -> str:
            return translate(key, language)

        return DetailQueryResponse(
            dataset=request.dataset,
            detail_key=request.detail_key,
            columns=self._sql.build_detail_columns(request.detail_key, _translate),
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

    @log_execution(log_args=True, level=logging.DEBUG)
    def build_export_plan(self, request: ExportCreateRequest) -> AnalyticsExportPlan:
        expected_format = self._sql.EXPORT_ACTIONS.get(request.action_key)
        if expected_format is None:
            raise AnalyticsQueryError(f"unsupported export action_key: {request.action_key}")
        if request.format != expected_format:
            raise AnalyticsQueryError(
                f"format {request.format.value} does not match action {request.action_key}"
            )

        detail_key = "source-files"
        detail_sql = self._sql.build_detail_select_sql(detail_key)
        where_sql, params = self._prepare_file_query(request.dataset, request.filters)
        order_sql = self._sql.build_detail_sort_sql(detail_key, self._sql.DEFAULT_DETAIL_SORT[detail_key])

        return AnalyticsExportPlan(
            dataset=request.dataset,
            action_key=request.action_key,
            format=request.format,
            sql=f"{detail_sql} WHERE {where_sql} ORDER BY {order_sql}",
            params=params,
            file_stem=f"{request.dataset}-{detail_key}-{request.action_key}",
        )

    @log_execution(log_args=True, level=logging.DEBUG)
    def get_filter_metadata(
        self,
        dataset: str,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> AnalyticsFilterMetadataResponse:
        self._ensure_dataset_exists(dataset)
        with self._conn.connect(read_only=True) as connection:
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
        with self._conn.connect(read_only=True) as connection:
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

    @contextmanager
    def execute_export_batches(self, sql: str, params: list, rows_per_batch: int):
        """Export용 record batch reader를 반환한다 (하위호환)."""
        with self._conn.execute_batches(sql, params, rows_per_batch=rows_per_batch) as reader:
            yield reader

    def _prepare_file_query(
        self,
        dataset: str,
        filters: dict[str, list[str]],
        start=None,
        end=None,
    ) -> tuple[str, list]:
        """공통 전처리: 필터 검증 → 데이터셋 확인 → WHERE 절 빌드."""
        self._sql.ensure_supported_filters(filters)
        self._ensure_dataset_exists(dataset)
        return self._sql.build_file_filters(
            dataset=dataset, filters=filters, start=start, end=end,
        )

    def _ensure_dataset_exists(self, dataset: str) -> None:
        if not self._conn.exists():
            raise AnalyticsDatasetNotFoundError(f"mart database is missing: {self.database_path}")

        with self._conn.connect(read_only=True) as connection:
            dataset_exists = connection.execute(
                "SELECT COUNT(*) FROM mart_datasets WHERE dataset_name = ?",
                [dataset],
            ).fetchone()[0]
        if not dataset_exists:
            raise AnalyticsDatasetNotFoundError(f"dataset not found: {dataset}")
