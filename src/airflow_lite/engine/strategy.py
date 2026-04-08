from abc import ABC, abstractmethod
from typing import Iterator
from datetime import date

import pandas as pd
import pyarrow as pa

from airflow_lite.engine.stage import StageContext


def _next_month_start(year: int, month: int) -> tuple[int, int]:
    """다음 월의 (year, month) 반환."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _build_select_columns(context: StageContext) -> str:
    columns = getattr(context.table_config, "columns", None)
    return ", ".join(columns) if columns else "*"


class MigrationStrategy(ABC):
    """마이그레이션 전략 추상 클래스"""

    @abstractmethod
    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        """Oracle에서 청크 단위로 데이터 추출"""

    def transform(self, chunk: pd.DataFrame, context: StageContext) -> pa.Table:
        """DataFrame을 PyArrow Table로 변환. 기본 구현: pandas → PyArrow 직변환."""
        return pa.Table.from_pandas(chunk, preserve_index=False)

    @abstractmethod
    def load(self, table: pa.Table, context: StageContext) -> int:
        """Parquet 파일로 저장, 처리 건수 반환"""

    @abstractmethod
    def verify(self, context: StageContext) -> bool:
        """소스-타겟 건수 일치 검증"""

    def finalize_run(self, context: StageContext, succeeded: bool) -> None:
        """실행 완료 후 정리/복구 훅."""


class FullMigrationStrategy(MigrationStrategy):
    """전체 이관: 월별 파티션 전체를 덮어쓰기.

    extract: partition_column 기반 WHERE절로 해당 월 전체 데이터 추출
    load: 기존 Parquet 파일을 .bak으로 이동 후 새 파일 생성
    verify: Oracle 건수 vs Parquet 행 수 비교
    """

    def __init__(self, oracle_client, chunked_reader, parquet_writer):
        self.oracle_client = oracle_client
        self.chunked_reader = chunked_reader
        self.parquet_writer = parquet_writer
        self._is_first_chunk = True
        self._had_backup = False

    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        query = self._build_full_query(context)
        self.chunked_reader.connection = self.oracle_client.get_connection()
        self.chunked_reader.chunk_size = context.chunk_size
        self._is_first_chunk = True
        self.parquet_writer.finalize_partition(
            context.table_config.table,
            context.execution_date.year,
            context.execution_date.month,
        )

        def _iter_chunks() -> Iterator[pd.DataFrame]:
            try:
                yield from self.chunked_reader.read_chunks(query)
            finally:
                self.parquet_writer.finalize_partition(
                    context.table_config.table,
                    context.execution_date.year,
                    context.execution_date.month,
                )

        return _iter_chunks()

    def _build_full_query(self, context: StageContext) -> str:
        """월별 파티션 쿼리 생성.
        예: SELECT * FROM PRODUCTION_LOG
            WHERE LOG_DATE >= DATE '2026-03-01'
              AND LOG_DATE < DATE '2026-04-01'
        """
        table = context.table_config.table
        partition_col = context.table_config.partition_column
        year = context.execution_date.year
        month = context.execution_date.month

        next_year, next_month = _next_month_start(year, month)

        selected_columns = _build_select_columns(context)
        return (
            f"SELECT {selected_columns} FROM {table} "
            f"WHERE {partition_col} >= DATE '{year:04d}-{month:02d}-01' "
            f"AND {partition_col} < DATE '{next_year:04d}-{next_month:02d}-01'"
        )

    # transform()은 부모 MigrationStrategy의 기본 구현 사용

    def load(self, table: pa.Table, context: StageContext) -> int:
        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table

        if self._is_first_chunk:
            # 기존 파일 .bak으로 백업 후 새 파일 생성
            self._had_backup = self.parquet_writer.backup_existing(table_name, year, month)
            self._is_first_chunk = False
            append = False
        else:
            append = True

        self.parquet_writer.write_chunk(
            table,
            table_name,
            year,
            month,
            append=append,
            append_mode="single_file",
        )
        return len(table)

    def verify(self, context: StageContext) -> bool:
        """Oracle 건수 vs Parquet 행 수 비교"""
        count_query = f"SELECT COUNT(*) FROM ({self._build_full_query(context)})"
        conn = self.oracle_client.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(count_query)
            oracle_count = cursor.fetchone()[0]
        finally:
            cursor.close()

        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table
        parquet_count = self.parquet_writer.count_rows(table_name, year, month)
        return oracle_count == parquet_count

    def finalize_run(self, context: StageContext, succeeded: bool) -> None:
        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table

        self.parquet_writer.finalize_partition(table_name, year, month)
        if succeeded:
            self.parquet_writer.remove_backups(table_name, year, month)
        elif self._had_backup:
            self.parquet_writer.restore_backups(table_name, year, month)
        else:
            self.parquet_writer.remove_partition_files(table_name, year, month)

        self._is_first_chunk = True
        self._had_backup = False


class IncrementalMigrationStrategy(MigrationStrategy):
    """증분 이관: 마지막 이관 이후 변경분만 처리.

    extract: incremental_key 기반 WHERE절로 변경분 추출
    load: 기존 Parquet에 append
    verify: 추출 건수 vs 적재 건수 비교
    """

    def __init__(self, oracle_client, chunked_reader, parquet_writer):
        self.oracle_client = oracle_client
        self.chunked_reader = chunked_reader
        self.parquet_writer = parquet_writer
        self._extract_count = 0
        self._loaded_count = 0
        self._initial_partition_rows = 0
        self._written_files: list[str] = []

    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        query = self._build_incremental_query(context)
        self.chunked_reader.connection = self.oracle_client.get_connection()
        self.chunked_reader.chunk_size = context.chunk_size
        self._extract_count = 0
        self._loaded_count = 0
        self._initial_partition_rows = self.parquet_writer.count_rows(
            context.table_config.table,
            context.execution_date.year,
            context.execution_date.month,
        )
        self._written_files = []

        def _iter_chunks() -> Iterator[pd.DataFrame]:
            for chunk in self.chunked_reader.read_chunks(query):
                self._extract_count += len(chunk)
                yield chunk

        return _iter_chunks()

    def _build_incremental_query(self, context: StageContext) -> str:
        """incremental_key 기반 WHERE절 생성 (execution_date 당일 변경분)."""
        table = context.table_config.table
        incremental_key = context.table_config.incremental_key
        exec_date = context.execution_date

        from datetime import timedelta
        next_date = exec_date + timedelta(days=1)

        selected_columns = _build_select_columns(context)
        return (
            f"SELECT {selected_columns} FROM {table} "
            f"WHERE {incremental_key} >= DATE '{exec_date.strftime('%Y-%m-%d')}' "
            f"AND {incremental_key} < DATE '{next_date.strftime('%Y-%m-%d')}'"
        )

    # transform()은 부모 MigrationStrategy의 기본 구현 사용

    def load(self, table: pa.Table, context: StageContext) -> int:
        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table

        output_path = self.parquet_writer.write_chunk(table, table_name, year, month, append=True)
        self._written_files.append(str(output_path))
        count = len(table)
        self._loaded_count += count
        return count

    def verify(self, context: StageContext) -> bool:
        """추출 건수와 실제 파티션 증가분이 모두 기대값과 일치하는지 확인한다."""
        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table
        current_partition_rows = self.parquet_writer.count_rows(table_name, year, month)
        expected_partition_rows = self._initial_partition_rows + self._loaded_count

        return (
            self._loaded_count == self._extract_count
            and current_partition_rows == expected_partition_rows
        )

    def finalize_run(self, context: StageContext, succeeded: bool) -> None:
        if not succeeded:
            for output_path in self._written_files:
                from pathlib import Path

                path = Path(output_path)
                if path.exists():
                    path.unlink()
        self._extract_count = 0
        self._loaded_count = 0
        self._initial_partition_rows = 0
        self._written_files = []
