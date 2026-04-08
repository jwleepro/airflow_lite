"""Mart refresh 인프라 조립 팩토리.

Settings의 mart 설정에서 MartRefreshCoordinator와 MartRefreshExecutor를 생성한다.
runtime.py의 SRP 위반을 해소하기 위해 분리.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from airflow_lite.mart.builder import DuckDBMartBuilder
from airflow_lite.mart.orchestration import MartRefreshCoordinator
from airflow_lite.mart.refresh import MartRefreshExecutor, MartRefreshPlanner
from airflow_lite.mart.snapshot import MartSnapshotLayout


@dataclass(frozen=True)
class MartInfrastructure:
    """Mart 갱신에 필요한 인프라 객체 번들."""
    coordinator: MartRefreshCoordinator
    executor: MartRefreshExecutor


def build_mart_infrastructure(settings) -> MartInfrastructure | None:
    """mart 설정에서 MartRefreshCoordinator/Executor를 생성한다.

    mart가 비활성이거나 refresh_on_success=False이면 None을 반환한다.
    """
    if not settings.mart.enabled or not settings.mart.refresh_on_success:
        return None

    mart_layout = MartSnapshotLayout(
        root_dir=Path(settings.mart.root_path),
        database_filename=settings.mart.database_filename,
    )
    mart_builder = DuckDBMartBuilder(mart_layout)
    mart_planner = MartRefreshPlanner(mart_builder)
    coordinator = MartRefreshCoordinator(
        planner=mart_planner,
        parquet_root=Path(settings.storage.parquet_base_path),
        pipeline_datasets=settings.mart.pipeline_datasets,
    )
    executor = MartRefreshExecutor(mart_builder)
    return MartInfrastructure(coordinator=coordinator, executor=executor)
