from __future__ import annotations

from typing import Protocol, runtime_checkable

from airflow_lite.query.contracts import ExportCreateRequest
from airflow_lite.query.service import AnalyticsExportPlan


@runtime_checkable
class ExportQueryProvider(Protocol):
    """Export 서비스가 쿼리 서비스에 요구하는 최소 인터페이스.

    DuckDBAnalyticsQueryService가 이를 암묵적으로 만족하므로
    기존 코드 변경 없이 주입 가능하다.
    """

    def build_export_plan(self, request: ExportCreateRequest) -> AnalyticsExportPlan: ...

    def execute_export_batches(self, sql: str, params: list, rows_per_batch: int): ...
