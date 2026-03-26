from abc import ABC, abstractmethod
from typing import Iterator
from datetime import date

import pandas as pd
import pyarrow as pa

from airflow_lite.engine.stage import StageContext, StageResult


def _build_select_columns(context: StageContext) -> str:
    columns = getattr(context.table_config, "columns", None)
    return ", ".join(columns) if columns else "*"


class MigrationStrategy(ABC):
    """마이그레이션 전략 추상 클래스"""

    @abstractmethod
    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        """Oracle에서 청크 단위로 데이터 추출"""

    @abstractmethod
    def transform(self, chunk: pd.DataFrame, context: StageContext) -> pa.Table:
        """DataFrame을 PyArrow Table로 변환"""

    @abstractmethod
    def load(self, table: pa.Table, context: StageContext) -> int:
        """Parquet 파일로 저장, 처리 건수 반환"""

    @abstractmethod
    def verify(self, context: StageContext) -> bool:
        """소스-타겟 건수 일치 검증"""


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

        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1

        selected_columns = _build_select_columns(context)
        return (
            f"SELECT {selected_columns} FROM {table} "
            f"WHERE {partition_col} >= DATE '{year:04d}-{month:02d}-01' "
            f"AND {partition_col} < DATE '{next_year:04d}-{next_month:02d}-01'"
        )

    def transform(self, chunk: pd.DataFrame, context: StageContext) -> pa.Table:
        return pa.Table.from_pandas(chunk, preserve_index=False)

    def load(self, table: pa.Table, context: StageContext) -> int:
        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table

        if self._is_first_chunk:
            # 기존 파일 .bak으로 백업 후 새 파일 생성
            self.parquet_writer.backup_existing(table_name, year, month)
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
        self._loaded_count = 0

    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        query = self._build_incremental_query(context)
        self.chunked_reader.connection = self.oracle_client.get_connection()
        self.chunked_reader.chunk_size = context.chunk_size
        self._loaded_count = 0
        return self.chunked_reader.read_chunks(query)

    def _build_incremental_query(self, context: StageContext) -> str:
        """incremental_key 기반 WHERE절 생성 (execution_date 당일 변경분)."""
        table = context.table_config.table
        incremental_key = context.table_config.incremental_key
        exec_date = context.execution_date

        year = exec_date.year
        month = exec_date.month
        day = exec_date.day

        if exec_date.month == 12 and exec_date.day == 31:
            next_date = date(year + 1, 1, 1)
        else:
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            if day == last_day:
                if month == 12:
                    next_date = date(year + 1, 1, 1)
                else:
                    next_date = date(year, month + 1, 1)
            else:
                next_date = date(year, month, day + 1)

        selected_columns = _build_select_columns(context)
        return (
            f"SELECT {selected_columns} FROM {table} "
            f"WHERE {incremental_key} >= DATE '{exec_date.strftime('%Y-%m-%d')}' "
            f"AND {incremental_key} < DATE '{next_date.strftime('%Y-%m-%d')}'"
        )

    def transform(self, chunk: pd.DataFrame, context: StageContext) -> pa.Table:
        return pa.Table.from_pandas(chunk, preserve_index=False)

    def load(self, table: pa.Table, context: StageContext) -> int:
        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table

        self.parquet_writer.write_chunk(table, table_name, year, month, append=True)
        count = len(table)
        self._loaded_count += count
        return count

    def verify(self, context: StageContext) -> bool:
        """추출 건수 vs 적재 건수 비교"""
        year = context.execution_date.year
        month = context.execution_date.month
        table_name = context.table_config.table
        parquet_count = self.parquet_writer.count_rows(table_name, year, month)
        return self._loaded_count <= parquet_count
