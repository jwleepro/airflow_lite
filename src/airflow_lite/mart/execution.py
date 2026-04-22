from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq

from airflow_lite.mart.builder import MartBuildPlan
from airflow_lite.mart.staging_db import (
    MartBuildResult,
    MartSourceFileStat,
    ParquetSourceLoader,
    StagingDBPreparer,
    _source_root,
)


class DuckDBMartExecutor:
    """Build or refresh a dataset-scoped raw source table inside a staging DuckDB file."""

    def execute_build(self, plan: MartBuildPlan) -> MartBuildResult:
        source_name = self._resolve_source_name(plan)
        source_files = self._discover_source_files(plan)
        if not source_files:
            raise ValueError("source parquet files must not be empty")

        StagingDBPreparer().prepare(plan)

        raw_table_name = self._raw_table_name(plan.request.dataset_name, source_name)
        total_rows = sum(file.row_count for file in source_files)
        now = datetime.now()

        import duckdb

        connection = duckdb.connect(str(plan.paths.staging_db_path))
        try:
            result = ParquetSourceLoader().load(
                connection, plan, raw_table_name, source_name, source_files, total_rows, now
            )
        finally:
            connection.close()

        return result

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_").lower()
        if not slug:
            return "dataset"
        if slug[0].isdigit():
            return f"t_{slug}"
        return slug

    def _raw_table_name(self, dataset_name: str, source_name: str) -> str:
        return f"raw__{self._slugify(dataset_name)}__{self._slugify(source_name)}"

    def _resolve_source_name(self, plan: MartBuildPlan) -> str:
        return _source_root(plan).name

    def _discover_source_files(self, plan: MartBuildPlan) -> tuple[MartSourceFileStat, ...]:
        source_root = _source_root(plan)
        parquet_files = sorted(
            path for path in source_root.glob("year=*/month=*/*.parquet") if path.is_file()
        )
        return tuple(MartExecutorFileStatCollector().collect(path) for path in parquet_files)


class MartExecutorFileStatCollector:
    """Parquet 파일의 partition 정보와 row count 를 수집."""

    def collect(self, path: Path) -> MartSourceFileStat:
        year = int(path.parent.parent.name.split("=", maxsplit=1)[1])
        month = int(path.parent.name.split("=", maxsplit=1)[1])
        metadata = pq.read_metadata(str(path))
        return MartSourceFileStat(
            path=path,
            partition_start=date(year, month, 1),
            row_count=metadata.num_rows,
        )
