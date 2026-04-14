"""차트 쿼리 핸들러.

차트 타입별 쿼리 로직을 핸들러 클래스로 분리해 새 차트 추가 시
서비스 코드를 고치지 않아도 되도록 한다 (OCP).

핸들러 공통 흐름은 :meth:`ChartHandler.handle` 가 Template Method 로 관장하고,
서브클래스는 SQL/매핑/시리즈 빌드만 제공한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from airflow_lite.analytics import SUPPORTED_CHARTS
from airflow_lite.i18n import translate
from airflow_lite.query.contracts import (
    ChartGranularity,
    ChartPoint,
    ChartQueryRequest,
    ChartQueryResponse,
    ChartSeries,
)

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


__all__ = [
    "ChartHandler",
    "RowsByMonthHandler",
    "FilesBySourceHandler",
    "CHART_HANDLERS",
]


class ChartHandler(ABC):
    """차트 핸들러 추상 클래스 (Template Method)."""

    chart_id: ClassVar[str]

    def handle(
        self,
        request: ChartQueryRequest,
        connection: "DuckDBPyConnection",
        where_sql: str,
        params: list,
        language: str,
    ) -> ChartQueryResponse:
        granularity, warnings = self._resolve_granularity(request, language)
        sql, extra_params = self._build_sql(request, where_sql)
        rows = connection.execute(sql, [*params, *extra_params]).fetchall()
        points = self._map_points(rows)
        series = self._build_series(points, language)

        return ChartQueryResponse(
            dataset=request.dataset,
            chart_id=self.chart_id,
            title=translate(SUPPORTED_CHARTS[self.chart_id], language),
            granularity=granularity,
            filters_applied=request.filters,
            series=[series],
            warnings=warnings,
        )

    def _resolve_granularity(
        self, request: ChartQueryRequest, language: str
    ) -> tuple[ChartGranularity, list[str]]:
        """차트 기본 granularity 와 경고 목록. 기본은 request 값 그대로."""
        return request.granularity, []

    @abstractmethod
    def _build_sql(
        self, request: ChartQueryRequest, where_sql: str
    ) -> tuple[str, list]:
        """(SQL, 추가 파라미터) 반환. 공통 params 뒤에 extra_params 가 이어진다."""

    @abstractmethod
    def _map_points(self, rows: list) -> list[ChartPoint]:
        """DuckDB row 결과를 ChartPoint 리스트로 변환."""

    @abstractmethod
    def _build_series(
        self, points: list[ChartPoint], language: str
    ) -> ChartSeries:
        """차트 시리즈 구성."""


class RowsByMonthHandler(ChartHandler):
    chart_id = "rows_by_month"

    def _resolve_granularity(
        self, request: ChartQueryRequest, language: str
    ) -> tuple[ChartGranularity, list[str]]:
        if request.granularity is not ChartGranularity.MONTH:
            return ChartGranularity.MONTH, [
                translate(
                    "analytics.chart.rows_by_month.granularity_normalized",
                    language,
                )
            ]
        return ChartGranularity.MONTH, []

    def _build_sql(
        self, request: ChartQueryRequest, where_sql: str
    ) -> tuple[str, list]:
        sql = f"""
            SELECT
                strftime(partition_start, '%Y-%m-01') AS bucket,
                SUM(row_count) AS value
            FROM mart_dataset_files
            WHERE {where_sql}
            GROUP BY partition_start
            ORDER BY partition_start DESC
            LIMIT ?
        """
        return sql, [request.limit]

    def _map_points(self, rows: list) -> list[ChartPoint]:
        return [
            ChartPoint(bucket=bucket, value=int(value))
            for bucket, value in reversed(rows)
        ]

    def _build_series(
        self, points: list[ChartPoint], language: str
    ) -> ChartSeries:
        return ChartSeries(
            key="rows",
            label=translate("analytics.chart.series.rows", language),
            points=points,
        )


class FilesBySourceHandler(ChartHandler):
    chart_id = "files_by_source"

    def _build_sql(
        self, request: ChartQueryRequest, where_sql: str
    ) -> tuple[str, list]:
        sql = f"""
            SELECT source_name, COUNT(*) AS value
            FROM mart_dataset_files
            WHERE {where_sql}
            GROUP BY source_name
            ORDER BY value DESC, source_name ASC
            LIMIT ?
        """
        return sql, [request.limit]

    def _map_points(self, rows: list) -> list[ChartPoint]:
        return [
            ChartPoint(bucket=source_name, value=int(value), label=source_name)
            for source_name, value in rows
        ]

    def _build_series(
        self, points: list[ChartPoint], language: str
    ) -> ChartSeries:
        return ChartSeries(
            key="files",
            label=translate("analytics.chart.series.files", language),
            points=points,
        )


CHART_HANDLERS: dict[str, ChartHandler] = {
    handler.chart_id: handler
    for handler in (RowsByMonthHandler(), FilesBySourceHandler())
}
