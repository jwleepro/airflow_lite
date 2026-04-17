from datetime import date
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Iterator

import pandas as pd
import pyarrow as pa

from airflow_lite.engine.stage import StageContext
from airflow_lite.pipeline_config_validation import render_source_query


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


class OracleParquetMigrationStrategy(MigrationStrategy, ABC):
    def __init__(self, oracle_client, chunked_reader, parquet_writer):
        self.oracle_client = oracle_client
        self.chunked_reader = chunked_reader
        self.parquet_writer = parquet_writer

    def _configure_chunk_reader(self, context: StageContext) -> None:
        self.chunked_reader.connection = self.oracle_client.get_connection()
        self.chunked_reader.chunk_size = context.chunk_size

    @staticmethod
    def _partition_target(context: StageContext) -> tuple[str, int, int]:
        return (
            context.table_config.table,
            context.execution_date.year,
            context.execution_date.month,
        )

    @staticmethod
    def _select_prefix(context: StageContext) -> str:
        return f"SELECT {_build_select_columns(context)} FROM {context.table_config.table}"

    @staticmethod
    def _build_source_filter(context: StageContext) -> tuple[str | None, dict]:
        return render_source_query(
            getattr(context.table_config, "source_where_template", None),
            getattr(context.table_config, "source_bind_params", None),
            execution_date=context.execution_date,
        )

    def _compose_query(
        self,
        context: StageContext,
        extra_predicates: list[str] | tuple[str, ...] = (),
    ) -> tuple[str, dict]:
        """source_where_template 과 추가 predicate 을 AND 결합해 쿼리 생성.

        predicate 이 하나도 없을 경우 호출 측 계약 위반이므로 예외.
        """
        source_where, bind_params = self._build_source_filter(context)
        predicates: list[str] = []
        if source_where:
            predicates.append(f"({source_where})" if extra_predicates else source_where)
        predicates.extend(extra_predicates)
        if not predicates:
            raise ValueError("full 전략은 source_where_template 이 필요합니다.")
        return (
            f"{self._select_prefix(context)} WHERE {' AND '.join(predicates)}",
            bind_params,
        )


class FullMigrationStrategy(OracleParquetMigrationStrategy):
    """전체 이관: 월별 파티션 전체를 덮어쓰기.

    extract: source_where_template 기반 WHERE절로 해당 월 전체 데이터 추출
    load: 기존 Parquet 파일을 .bak으로 이동 후 새 파일 생성
    verify: Oracle 건수 vs Parquet 행 수 비교
    """

    def __init__(self, oracle_client, chunked_reader, parquet_writer):
        super().__init__(oracle_client, chunked_reader, parquet_writer)
        self._is_first_chunk = True
        self._had_backup = False

    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        query, params = self._build_full_query(context)
        self._configure_chunk_reader(context)
        self._is_first_chunk = True
        table_name, year, month = self._partition_target(context)
        self.parquet_writer.finalize_partition(table_name, year, month)

        def _iter_chunks() -> Iterator[pd.DataFrame]:
            try:
                yield from self.chunked_reader.read_chunks(query, params)
            finally:
                self.parquet_writer.finalize_partition(table_name, year, month)

        return _iter_chunks()

    def _build_full_query(self, context: StageContext) -> tuple[str, dict]:
        """월별 전체 이관 쿼리와 bind params 생성."""
        return self._compose_query(context)

    # transform()은 부모 MigrationStrategy의 기본 구현 사용

    def load(self, table: pa.Table, context: StageContext) -> int:
        table_name, year, month = self._partition_target(context)

        if self._is_first_chunk:
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
        source_query, bind_params = self._build_full_query(context)
        count_query = f"SELECT COUNT(*) FROM ({source_query})"
        conn = self.oracle_client.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(count_query, bind_params)
            oracle_count = cursor.fetchone()[0]
        finally:
            cursor.close()

        table_name, year, month = self._partition_target(context)
        parquet_count = self.parquet_writer.count_rows(table_name, year, month)
        return oracle_count == parquet_count

    def finalize_run(self, context: StageContext, succeeded: bool) -> None:
        table_name, year, month = self._partition_target(context)

        self.parquet_writer.finalize_partition(table_name, year, month)
        if succeeded:
            self.parquet_writer.remove_backups(table_name, year, month)
        elif self._had_backup:
            self.parquet_writer.restore_backups(table_name, year, month)
        else:
            self.parquet_writer.remove_partition_files(table_name, year, month)

        self._is_first_chunk = True
        self._had_backup = False


class IncrementalMigrationStrategy(OracleParquetMigrationStrategy):
    """증분 이관: 마지막 이관 이후 변경분만 처리.

    extract: incremental_key 기반 WHERE절로 변경분 추출
    load: 기존 Parquet에 append
    verify: 추출 건수 vs 적재 건수 비교
    """

    def __init__(self, oracle_client, chunked_reader, parquet_writer):
        super().__init__(oracle_client, chunked_reader, parquet_writer)
        self._extract_count = 0
        self._loaded_count = 0
        self._initial_partition_rows = 0
        self._written_files: list[str] = []

    def extract(self, context: StageContext) -> Iterator[pd.DataFrame]:
        query, params = self._build_incremental_query(context)
        self._configure_chunk_reader(context)
        self._extract_count = 0
        self._loaded_count = 0
        table_name, year, month = self._partition_target(context)
        self._initial_partition_rows = self.parquet_writer.count_rows(
            table_name,
            year,
            month,
        )
        self._written_files = []

        def _iter_chunks() -> Iterator[pd.DataFrame]:
            for chunk in self.chunked_reader.read_chunks(query, params):
                self._extract_count += len(chunk)
                yield chunk

        return _iter_chunks()

    def _build_incremental_query(self, context: StageContext) -> tuple[str, dict]:
        """incremental_key 기반 WHERE절 생성 (execution_date 당일 변경분)."""
        incremental_key = context.table_config.incremental_key
        exec_date = context.execution_date
        next_date = exec_date + timedelta(days=1)
        return self._compose_query(
            context,
            [
                f"{incremental_key} >= DATE '{exec_date.strftime('%Y-%m-%d')}'",
                f"{incremental_key} < DATE '{next_date.strftime('%Y-%m-%d')}'",
            ],
        )

    # transform()은 부모 MigrationStrategy의 기본 구현 사용

    def load(self, table: pa.Table, context: StageContext) -> int:
        table_name, year, month = self._partition_target(context)

        output_path = self.parquet_writer.write_chunk(table, table_name, year, month, append=True)
        self._written_files.append(str(output_path))
        count = len(table)
        self._loaded_count += count
        return count

    def verify(self, context: StageContext) -> bool:
        """추출 건수와 실제 파티션 증가분이 모두 기대값과 일치하는지 확인한다."""
        table_name, year, month = self._partition_target(context)
        current_partition_rows = self.parquet_writer.count_rows(table_name, year, month)
        expected_partition_rows = self._initial_partition_rows + self._loaded_count

        return (
            self._loaded_count == self._extract_count
            and current_partition_rows == expected_partition_rows
        )

    def finalize_run(self, context: StageContext, succeeded: bool) -> None:
        if not succeeded:
            for output_path in self._written_files:
                path = Path(output_path)
                if path.exists():
                    path.unlink()
        self._extract_count = 0
        self._loaded_count = 0
        self._initial_partition_rows = 0
        self._written_files = []
