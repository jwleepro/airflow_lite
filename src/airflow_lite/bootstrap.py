from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from airflow_lite.config.settings import Settings
from airflow_lite.engine.backfill import BackfillManager
from airflow_lite.executor.pipeline_local_executor import PipelineLocalExecutor
from airflow_lite.export import FilesystemAnalyticsExportService
from airflow_lite.query import DuckDBAnalyticsQueryService
from airflow_lite.runtime import create_runner_factory
from airflow_lite.service.dispatch_service import PipelineDispatchService
from airflow_lite.storage.database import Database
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository
from airflow_lite.storage.admin_repository import AdminRepository

DEFAULT_CONFIG_PATH = "config/pipelines.yaml"
CONFIG_PATH_ENV_VAR = "AIRFLOW_LITE_CONFIG_PATH"


@dataclass(frozen=True)
class RuntimeServices:
    settings: Settings
    run_repo: PipelineRunRepository
    step_repo: StepRunRepository
    admin_repo: AdminRepository
    runner_factory: Callable
    runner_map: dict[str, Callable]
    backfill_map: dict[str, Callable]
    analytics_query_service: DuckDBAnalyticsQueryService
    analytics_export_service: FilesystemAnalyticsExportService
    dispatch_executor: PipelineLocalExecutor
    dispatch_service: PipelineDispatchService

    def shutdown(self) -> None:
        """런타임 공용 리소스 정리. dispatcher 워커 종료 대기 포함."""
        self.dispatch_executor.shutdown(wait=True)


def resolve_config_path(cli_path: str | None = None) -> str:
    return cli_path or os.environ.get(CONFIG_PATH_ENV_VAR) or DEFAULT_CONFIG_PATH


def load_settings(config_path: str | None = None) -> tuple[str, Settings]:
    resolved_path = resolve_config_path(config_path)
    return resolved_path, Settings.load(resolved_path)


def get_mart_database_path(settings: Settings) -> Path:
    return Path(settings.mart.root_path) / "current" / settings.mart.database_filename


def get_api_bind(settings: Settings) -> tuple[str, int]:
    return settings.api.host, settings.api.port


def build_runtime_services(
    settings: Settings,
    config_path: str,
) -> RuntimeServices:
    db = Database(settings.storage.sqlite_path)
    db.initialize()
    run_repo = PipelineRunRepository(db)
    step_repo = StepRunRepository(db)
    admin_repo = AdminRepository(db, config_path, crypto=settings.crypto)
    runner_factory = create_runner_factory(settings, run_repo, step_repo)

    runner_map = {
        pipeline.name: (lambda pipeline_name=pipeline.name: runner_factory(pipeline_name))
        for pipeline in settings.pipelines
    }
    backfill_map = {
        pipeline.name: (
            lambda pipeline_name=pipeline.name: BackfillManager(
                pipeline_runner=runner_factory(pipeline_name),
                parquet_base_path=settings.storage.parquet_base_path,
            )
        )
        for pipeline in settings.pipelines
    }

    analytics_query_service = DuckDBAnalyticsQueryService(get_mart_database_path(settings))
    analytics_export_service = FilesystemAnalyticsExportService(
        root_path=settings.export.root_path,
        query_service=analytics_query_service,
        retention_hours=settings.export.retention_hours,
        max_workers=settings.export.max_workers,
        cleanup_cooldown_seconds=settings.export.cleanup_cooldown_seconds,
        rows_per_batch=settings.export.rows_per_batch,
        parquet_compression=settings.export.parquet_compression,
        zip_compression=settings.export.zip_compression,
    )

    dispatch_executor = PipelineLocalExecutor(
        max_workers=getattr(settings.scheduler, "dispatch_max_workers", 2),
    )
    dispatch_service = PipelineDispatchService(
        runner_map=runner_map,
        backfill_map=backfill_map,
        executor=dispatch_executor,
        run_repo=run_repo,
    )

    return RuntimeServices(
        settings=settings,
        run_repo=run_repo,
        step_repo=step_repo,
        admin_repo=admin_repo,
        runner_factory=runner_factory,
        runner_map=runner_map,
        backfill_map=backfill_map,
        analytics_query_service=analytics_query_service,
        analytics_export_service=analytics_export_service,
        dispatch_executor=dispatch_executor,
        dispatch_service=dispatch_service,
    )
