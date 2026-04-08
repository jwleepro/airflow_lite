import logging
from datetime import date, datetime
from pathlib import Path

from airflow_lite.alerting import AlertManager, AlertMessage, EmailAlertChannel, WebhookAlertChannel
from airflow_lite.config.settings import EmailChannelConfig, Settings, WebhookChannelConfig
from airflow_lite.engine.pipeline import PipelineDefinition, PipelineRunner
from airflow_lite.engine.stage import RetryConfig, StageDefinition, StageResult
from airflow_lite.engine.state_machine import StageStateMachine
from airflow_lite.engine.strategy import FullMigrationStrategy, IncrementalMigrationStrategy
from airflow_lite.extract.chunked_reader import ChunkedReader
from airflow_lite.extract.oracle_client import OracleClient
from airflow_lite.mart import (
    DuckDBMartBuilder,
    MartRefreshCoordinator,
    MartRefreshExecutor,
    MartRefreshPlanner,
    MartSnapshotLayout,
)
from airflow_lite.storage.database import Database
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository
from airflow_lite.transform.parquet_writer import ParquetWriter

logger = logging.getLogger("airflow_lite.runtime")


class VerificationFailedError(RuntimeError):
    """소스-타겟 검증 실패."""


def create_runner_factory(settings, run_repo, step_repo):
    """pipeline_name을 받아 PipelineRunner를 생성하는 팩토리 함수 반환.

    공유 인프라(OracleClient, ParquetWriter, StageStateMachine)는 한 번 생성하고,
    PipelineRunner는 호출마다 새 인스턴스를 반환한다.
    """
    oracle_client = OracleClient(settings.oracle)
    parquet_writer = ParquetWriter(
        base_path=settings.storage.parquet_base_path,
        compression=settings.defaults.parquet.compression,
    )
    state_machine = StageStateMachine(step_repo)
    pipeline_config_map = {p.name: p for p in settings.pipelines}

    alert_channels = []
    for ch_config in settings.alerting.channels:
        if isinstance(ch_config, EmailChannelConfig):
            alert_channels.append(
                EmailAlertChannel(
                    smtp_host=ch_config.smtp_host,
                    smtp_port=ch_config.smtp_port,
                    sender=ch_config.sender,
                    recipients=ch_config.recipients,
                )
            )
        elif isinstance(ch_config, WebhookChannelConfig):
            alert_channels.append(
                WebhookAlertChannel(
                    url=ch_config.url,
                    timeout=ch_config.timeout,
                )
            )
    alert_manager = AlertManager(
        channels=alert_channels,
        triggers={
            "on_failure": settings.alerting.triggers.on_failure,
            "on_success": settings.alerting.triggers.on_success,
        },
    )

    mart_refresh_coordinator = None
    mart_refresh_executor = None
    if settings.mart.enabled and settings.mart.refresh_on_success:
        mart_layout = MartSnapshotLayout(
            root_dir=Path(settings.mart.root_path),
            database_filename=settings.mart.database_filename,
        )
        mart_builder = DuckDBMartBuilder(mart_layout)
        mart_planner = MartRefreshPlanner(mart_builder)
        mart_refresh_coordinator = MartRefreshCoordinator(
            planner=mart_planner,
            parquet_root=Path(settings.storage.parquet_base_path),
            pipeline_datasets=settings.mart.pipeline_datasets,
        )
        mart_refresh_executor = MartRefreshExecutor(mart_builder)

    def _notify(status: str, context, exc: Exception | None = None) -> None:
        alert_manager.notify(
            AlertMessage(
                pipeline_name=context.pipeline_name,
                execution_date=context.execution_date,
                status=status,
                error_message=str(exc) if exc else None,
                timestamp=datetime.now(),
            )
        )

    def factory(pipeline_name: str) -> PipelineRunner:
        pipeline_config = pipeline_config_map[pipeline_name]
        chunk_size = pipeline_config.chunk_size or settings.defaults.chunk_size
        chunked_reader = ChunkedReader(connection=None, chunk_size=chunk_size)

        if pipeline_config.strategy == "full":
            strategy = FullMigrationStrategy(oracle_client, chunked_reader, parquet_writer)
        else:
            strategy = IncrementalMigrationStrategy(oracle_client, chunked_reader, parquet_writer)

        def on_failure_callback(context, exc):
            _notify("failed", context, exc)

        def on_success_callback(context):
            _notify("success", context)
            if mart_refresh_coordinator is None:
                return

            try:
                plan = mart_refresh_coordinator.plan_refresh(context)
            except Exception as plan_exc:
                logger.exception(
                    "Mart refresh planning failed: %s / %s",
                    context.pipeline_name,
                    context.execution_date,
                )
                _notify("failed", context, plan_exc)
                return

            if plan is None:
                return

            try:
                result = mart_refresh_executor.execute_refresh(plan)
            except Exception as mart_exc:
                logger.exception(
                    "Mart refresh execution failed: %s / %s",
                    context.pipeline_name,
                    context.execution_date,
                )
                _notify("failed", context, mart_exc)
                return

            if not result.validation_report.is_valid:
                issues = [issue.message for issue in result.validation_report.issues]
                logger.error(
                    "Mart refresh validation failed: dataset=%s issues=%s",
                    result.plan.request.dataset_name,
                    issues,
                )
                _notify("failed", context, RuntimeError(f"mart validation failed: {issues}"))
                return

            logger.info(
                "Mart refresh completed: dataset=%s mode=%s promoted=%s staging=%s current=%s snapshot=%s rows=%s files=%s",
                result.plan.request.dataset_name,
                result.plan.request.mode.value,
                result.promoted,
                result.plan.build_plan.paths.staging_db_path,
                result.plan.build_plan.paths.current_db_path,
                result.plan.build_plan.paths.snapshot_db_path,
                result.build_result.row_count,
                result.build_result.file_count,
            )

        retry_config = RetryConfig(
            max_attempts=settings.defaults.retry.max_attempts,
            min_wait_seconds=settings.defaults.retry.min_wait_seconds,
            max_wait_seconds=settings.defaults.retry.max_wait_seconds,
            on_failure_callback=on_failure_callback,
        )

        def etl_stage(context) -> StageResult:
            total = 0
            for chunk in strategy.extract(context):
                arrow_table = strategy.transform(chunk, context)
                total += strategy.load(arrow_table, context)
            return StageResult(records_processed=total)

        def verify_stage(context) -> StageResult:
            if not strategy.verify(context):
                raise VerificationFailedError(
                    f"검증 실패: {pipeline_name} / {context.execution_date.isoformat()}"
                )
            return StageResult()

        stages = [
            StageDefinition(
                name="extract_transform_load",
                callable=etl_stage,
                retry_config=retry_config,
            ),
            StageDefinition(
                name="verify",
                callable=verify_stage,
                retry_config=RetryConfig(
                    max_attempts=1,
                    on_failure_callback=on_failure_callback,
                ),
            ),
        ]

        return PipelineRunner(
            pipeline=PipelineDefinition(
                name=pipeline_name,
                stages=stages,
                strategy=strategy,
                table_config=pipeline_config,
                chunk_size=chunk_size,
            ),
            run_repo=run_repo,
            step_repo=step_repo,
            state_machine=state_machine,
            on_run_success=on_success_callback,
        )

    return factory


def run_scheduled_pipeline(config_path: str, pipeline_name: str) -> None:
    """APScheduler jobstore에 저장 가능한 형태로 파이프라인 실행.

    직렬화 가능한 인자만 받아 실행 시점에 설정과 repository, runner를 재구성한다.
    """
    settings = Settings.load(config_path)
    db = Database(settings.storage.sqlite_path)
    db.initialize()
    run_repo = PipelineRunRepository(db)
    step_repo = StepRunRepository(db)
    runner_factory = create_runner_factory(settings, run_repo, step_repo)
    runner = runner_factory(pipeline_name)
    runner.run(execution_date=date.today(), trigger_type="scheduled")
