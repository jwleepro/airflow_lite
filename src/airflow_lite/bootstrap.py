from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from airflow_lite.config.settings import Settings
from airflow_lite.engine.backfill import BackfillManager
from airflow_lite.export import FilesystemAnalyticsExportService
from airflow_lite.query import DuckDBAnalyticsQueryService
from airflow_lite.runtime import create_runner_factory
from airflow_lite.storage.database import Database
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository

DEFAULT_CONFIG_PATH = "config/pipelines.yaml"
CONFIG_PATH_ENV_VAR = "AIRFLOW_LITE_CONFIG_PATH"


@dataclass(frozen=True)
class RuntimeServices:
    settings: Settings
    run_repo: PipelineRunRepository
    step_repo: StepRunRepository
    runner_factory: Callable
    runner_map: dict[str, Callable]
    backfill_map: dict[str, Callable]
    analytics_query_service: DuckDBAnalyticsQueryService
    analytics_export_service: FilesystemAnalyticsExportService


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
    *,
    runner_factory_builder=None,
) -> RuntimeServices:
    db = Database(settings.storage.sqlite_path)
    db.initialize()
    run_repo = PipelineRunRepository(db)
    step_repo = StepRunRepository(db)
    if runner_factory_builder is None:
        runner_factory = create_runner_factory(settings, run_repo, step_repo)
    else:
        runner_factory = runner_factory_builder(settings, run_repo, step_repo)

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

    return RuntimeServices(
        settings=settings,
        run_repo=run_repo,
        step_repo=step_repo,
        runner_factory=runner_factory,
        runner_map=runner_map,
        backfill_map=backfill_map,
        analytics_query_service=analytics_query_service,
        analytics_export_service=analytics_export_service,
    )
