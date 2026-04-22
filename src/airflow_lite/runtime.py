import logging
from datetime import date

from airflow_lite.alerting.factory import build_alert_manager
from airflow_lite.config.settings import Settings
from airflow_lite.engine.callbacks import PipelineCallbacks
from airflow_lite.engine.pipeline import PipelineDefinition, PipelineRunner
from airflow_lite.engine.run_state_manager import RunStateManager
from airflow_lite.engine.stage import RetryConfig, StageDefinition, StageResult
from airflow_lite.engine.state_machine import StageStateMachine
from airflow_lite.engine.strategy import (
    FullMigrationStrategy,
    IncrementalMigrationStrategy,
    MigrationStrategy,
)
from airflow_lite.extract.chunked_reader import ChunkedReader
from airflow_lite.extract.oracle_client import OracleClient
from airflow_lite.mart.factory import build_mart_infrastructure
from airflow_lite.storage.database import Database
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository
from airflow_lite.transform.parquet_writer import ParquetWriter

logger = logging.getLogger("airflow_lite.runtime")


_STRATEGY_BUILDERS: dict[str, type[MigrationStrategy]] = {
    "full": FullMigrationStrategy,
    "incremental": IncrementalMigrationStrategy,
}


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

    alert_manager = build_alert_manager(settings.alerting)
    mart_infra = build_mart_infrastructure(settings)
    callbacks = PipelineCallbacks(alert_manager, mart_infra)

    def factory(pipeline_name: str) -> PipelineRunner:
        pipeline_config = pipeline_config_map[pipeline_name]
        chunk_size = pipeline_config.chunk_size or settings.defaults.chunk_size
        chunked_reader = ChunkedReader(connection=None, chunk_size=chunk_size)

        strategy_cls = _STRATEGY_BUILDERS.get(pipeline_config.strategy)
        if strategy_cls is None:
            raise ValueError(f"unsupported migration strategy: {pipeline_config.strategy}")
        strategy = strategy_cls(oracle_client, chunked_reader, parquet_writer)

        retry_config = RetryConfig(
            max_attempts=settings.defaults.retry.max_attempts,
            min_wait_seconds=settings.defaults.retry.min_wait_seconds,
            max_wait_seconds=settings.defaults.retry.max_wait_seconds,
            on_failure_callback=callbacks.on_failure,
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
                    on_failure_callback=callbacks.on_failure,
                ),
            ),
        ]

        run_state_manager = RunStateManager(state_machine, step_repo)
        return PipelineRunner(
            pipeline=PipelineDefinition(
                name=pipeline_name,
                stages=stages,
                strategy=strategy,
                table_config=pipeline_config,
                chunk_size=chunk_size,
            ),
            run_repo=run_repo,
            run_state_manager=run_state_manager,
            on_run_success=callbacks.on_success,
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
