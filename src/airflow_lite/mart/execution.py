from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq

from airflow_lite.mart.builder import MartBuildPlan


@dataclass(frozen=True)
class MartSourceFileStat:
    path: Path
    partition_start: date
    row_count: int


@dataclass(frozen=True)
class MartBuildResult:
    plan: MartBuildPlan
    dataset_name: str
    source_name: str
    raw_table_name: str
    source_files: tuple[MartSourceFileStat, ...]
    row_count: int
    file_count: int


class DuckDBMartExecutor:
    """Build or refresh a dataset-scoped raw source table inside a staging DuckDB file."""

    def execute_build(self, plan: MartBuildPlan) -> MartBuildResult:
        source_name = self._resolve_source_name(plan)
        source_files = self._discover_source_files(plan)
        if not source_files:
            raise ValueError("source parquet files must not be empty")

        self._prepare_staging_database(plan)

        import duckdb

        raw_table_name = self._raw_table_name(plan.request.dataset_name, source_name)
        total_rows = sum(file.row_count for file in source_files)
        now = datetime.now()
        connection = duckdb.connect(str(plan.paths.staging_db_path))
        try:
            quoted_table = self._quote_identifier(raw_table_name)
            connection.execute(f"DROP TABLE IF EXISTS {quoted_table}")
            connection.execute(
                f"CREATE TABLE {quoted_table} AS SELECT * FROM read_parquet(?)",
                [[file.path.as_posix() for file in source_files]],
            )

            self._ensure_metadata_tables(connection)
            connection.execute(
                "DELETE FROM mart_dataset_files WHERE dataset_name = ? AND source_name = ?",
                [plan.request.dataset_name, source_name],
            )
            connection.executemany(
                """
                INSERT INTO mart_dataset_files (
                    dataset_name,
                    source_name,
                    partition_start,
                    file_path,
                    row_count,
                    last_build_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    [
                        plan.request.dataset_name,
                        source_name,
                        file.partition_start,
                        file.path.as_posix(),
                        file.row_count,
                        plan.request.build_id,
                    ]
                    for file in source_files
                ],
            )
            connection.execute(
                "DELETE FROM mart_dataset_sources WHERE dataset_name = ? AND source_name = ?",
                [plan.request.dataset_name, source_name],
            )
            connection.execute(
                """
                INSERT INTO mart_dataset_sources (
                    dataset_name,
                    source_name,
                    raw_table_name,
                    source_root,
                    row_count,
                    file_count,
                    min_partition_start,
                    max_partition_start,
                    last_build_id,
                    refresh_mode,
                    last_refreshed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    plan.request.dataset_name,
                    source_name,
                    raw_table_name,
                    self._source_root(plan).as_posix(),
                    total_rows,
                    len(source_files),
                    min(file.partition_start for file in source_files),
                    max(file.partition_start for file in source_files),
                    plan.request.build_id,
                    "full" if plan.request.full_refresh else "incremental",
                    now,
                ],
            )
            connection.execute(
                "DELETE FROM mart_datasets WHERE dataset_name = ?",
                [plan.request.dataset_name],
            )
            connection.execute(
                """
                INSERT INTO mart_datasets (
                    dataset_name,
                    source_count,
                    total_rows,
                    total_files,
                    min_partition_start,
                    max_partition_start,
                    last_refreshed_at
                )
                SELECT
                    dataset_name,
                    COUNT(DISTINCT source_name),
                    COALESCE(SUM(row_count), 0),
                    COALESCE(SUM(file_count), 0),
                    MIN(min_partition_start),
                    MAX(max_partition_start),
                    MAX(last_refreshed_at)
                FROM mart_dataset_sources
                WHERE dataset_name = ?
                GROUP BY dataset_name
                """,
                [plan.request.dataset_name],
            )
        finally:
            connection.close()

        return MartBuildResult(
            plan=plan,
            dataset_name=plan.request.dataset_name,
            source_name=source_name,
            raw_table_name=raw_table_name,
            source_files=source_files,
            row_count=total_rows,
            file_count=len(source_files),
        )

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

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

    def _prepare_staging_database(self, plan: MartBuildPlan) -> None:
        plan.paths.staging_db_path.parent.mkdir(parents=True, exist_ok=True)
        if plan.paths.staging_db_path.exists():
            plan.paths.staging_db_path.unlink()

        if plan.paths.current_db_path.exists():
            shutil.copy2(plan.paths.current_db_path, plan.paths.staging_db_path)

    def _source_root(self, plan: MartBuildPlan) -> Path:
        first_path = plan.request.source_paths[0]
        return first_path.parents[2]

    def _resolve_source_name(self, plan: MartBuildPlan) -> str:
        return self._source_root(plan).name

    def _discover_source_files(self, plan: MartBuildPlan) -> tuple[MartSourceFileStat, ...]:
        source_root = self._source_root(plan)
        parquet_files = sorted(
            path for path in source_root.glob("year=*/month=*/*.parquet") if path.is_file()
        )
        return tuple(self._collect_file_stat(path) for path in parquet_files)

    def _collect_file_stat(self, path: Path) -> MartSourceFileStat:
        year = int(path.parent.parent.name.split("=", maxsplit=1)[1])
        month = int(path.parent.name.split("=", maxsplit=1)[1])
        metadata = pq.read_metadata(str(path))
        return MartSourceFileStat(
            path=path,
            partition_start=date(year, month, 1),
            row_count=metadata.num_rows,
        )

    @staticmethod
    def _ensure_metadata_tables(connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mart_dataset_files (
                dataset_name VARCHAR,
                source_name VARCHAR,
                partition_start DATE,
                file_path VARCHAR,
                row_count BIGINT,
                last_build_id VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mart_dataset_sources (
                dataset_name VARCHAR,
                source_name VARCHAR,
                raw_table_name VARCHAR,
                source_root VARCHAR,
                row_count BIGINT,
                file_count BIGINT,
                min_partition_start DATE,
                max_partition_start DATE,
                last_build_id VARCHAR,
                refresh_mode VARCHAR,
                last_refreshed_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mart_datasets (
                dataset_name VARCHAR,
                source_count BIGINT,
                total_rows BIGINT,
                total_files BIGINT,
                min_partition_start DATE,
                max_partition_start DATE,
                last_refreshed_at TIMESTAMP
            )
            """
        )
