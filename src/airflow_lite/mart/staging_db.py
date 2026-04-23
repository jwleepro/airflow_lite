"""Staging DB 준비, 스키마 생성, 소스 로딩 전담 모듈.

DuckDBMartExecutor 에서 파일/스키마/DML 책임을 분리한다.
"""

from __future__ import annotations

from pathlib import Path
from datetime import date, datetime
import shutil

from dataclasses import dataclass

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


class StagingDBPreparer:
    """Staging DuckDB 파일을 생성하거나 current DB 로부터 복사한다."""

    def prepare(self, plan: MartBuildPlan) -> Path:
        plan.paths.staging_db_path.parent.mkdir(parents=True, exist_ok=True)
        if plan.paths.staging_db_path.exists():
            plan.paths.staging_db_path.unlink()

        if plan.paths.current_db_path.exists():
            shutil.copy2(plan.paths.current_db_path, plan.paths.staging_db_path)

        return plan.paths.staging_db_path


class MetadataSchemaCreator:
    """MART 메타데이터 테이블 DDL 생성."""

    _TABLES = (
        """\
CREATE TABLE IF NOT EXISTS mart_dataset_files (
    dataset_name VARCHAR,
    source_name VARCHAR,
    partition_start DATE,
    file_path VARCHAR,
    row_count BIGINT,
    last_build_id VARCHAR
)""",
        """\
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
)""",
        """\
CREATE TABLE IF NOT EXISTS mart_datasets (
    dataset_name VARCHAR,
    source_count BIGINT,
    total_rows BIGINT,
    total_files BIGINT,
    min_partition_start DATE,
    max_partition_start DATE,
    last_refreshed_at TIMESTAMP
)""",
    )

    def create_schema(self, connection) -> None:
        for ddl in self._TABLES:
            connection.execute(ddl)


class ParquetSourceLoader:
    """Parquet 파일을 raw 테이블로 적재하고 메타데이터를 갱신한다."""

    def load(
        self,
        connection,
        plan: MartBuildPlan,
        raw_table_name: str,
        source_name: str,
        source_files: tuple[MartSourceFileStat, ...],
        total_rows: int,
        now: datetime,
    ) -> MartBuildResult:
        dataset_name = plan.request.dataset_name

        quoted_table = _quote_identifier(raw_table_name)
        connection.execute(f"DROP TABLE IF EXISTS {quoted_table}")
        connection.execute(
            f"CREATE TABLE {quoted_table} AS SELECT * FROM read_parquet(?)",
            [[file.path.as_posix() for file in source_files]],
        )

        MetadataSchemaCreator().create_schema(connection)

        connection.execute(
            "DELETE FROM mart_dataset_files WHERE dataset_name = ? AND source_name = ?",
            [dataset_name, source_name],
        )
        connection.executemany(
            """
            INSERT INTO mart_dataset_files (
                dataset_name, source_name, partition_start,
                file_path, row_count, last_build_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                [
                    dataset_name, source_name,
                    file.partition_start, file.path.as_posix(),
                    file.row_count, plan.request.build_id,
                ]
                for file in source_files
            ],
        )

        connection.execute(
            "DELETE FROM mart_dataset_sources WHERE dataset_name = ? AND source_name = ?",
            [dataset_name, source_name],
        )
        connection.execute(
            """
            INSERT INTO mart_dataset_sources (
                dataset_name, source_name, raw_table_name, source_root,
                row_count, file_count,
                min_partition_start, max_partition_start,
                last_build_id, refresh_mode, last_refreshed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                dataset_name, source_name, raw_table_name,
                _source_root(plan).as_posix(),
                total_rows, len(source_files),
                min(file.partition_start for file in source_files),
                max(file.partition_start for file in source_files),
                plan.request.build_id,
                "full" if plan.request.full_refresh else "incremental",
                now,
            ],
        )

        connection.execute(
            "DELETE FROM mart_datasets WHERE dataset_name = ?",
            [dataset_name],
        )
        connection.execute(
            """
            INSERT INTO mart_datasets (
                dataset_name, source_count, total_rows, total_files,
                min_partition_start, max_partition_start, last_refreshed_at
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
            [dataset_name],
        )

        return MartBuildResult(
            plan=plan,
            dataset_name=dataset_name,
            source_name=source_name,
            raw_table_name=raw_table_name,
            source_files=source_files,
            row_count=total_rows,
            file_count=len(source_files),
        )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _source_root(plan: MartBuildPlan) -> Path:
    first_path = plan.request.source_paths[0]
    return first_path.parents[2]
