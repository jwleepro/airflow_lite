import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING

from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from airflow_lite.engine.stage import (
    RETRYABLE_EXCEPTIONS,
    StageContext,
    StageDefinition,
    StageResult,
    StageState,
)
from airflow_lite.engine.state_machine import StageStateMachine
from airflow_lite.storage.models import PipelineRun, StepRun
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository

if TYPE_CHECKING:
    from airflow_lite.config.settings import PipelineConfig
    from airflow_lite.engine.strategy import MigrationStrategy

logger = logging.getLogger("airflow_lite.engine.pipeline")


@dataclass
class PipelineDefinition:
    name: str
    stages: list[StageDefinition]
    strategy: "MigrationStrategy | None"
    table_config: "PipelineConfig | None" = None
    chunk_size: int = 10000


class PipelineRunner:
    def __init__(
        self,
        pipeline: PipelineDefinition,
        run_repo: PipelineRunRepository,
        step_repo: StepRunRepository,
        state_machine: StageStateMachine,
    ):
        self.pipeline = pipeline
        self.run_repo = run_repo
        self.step_repo = step_repo
        self.state_machine = state_machine

    def run(self, execution_date: date, trigger_type: str = "scheduled") -> PipelineRun:
        """파이프라인 실행 메인 루프.

        1. 동일 execution_date 성공 실행이 있으면 그대로 반환 (멱등성, P2)
        2. PipelineRun 레코드 생성
        3. 각 StageDefinition을 순차 실행
        4. 단계 실패 시 후속 단계를 SKIPPED 처리 (실패 격리, P3)
        5. 모든 단계 완료 후 PipelineRun 상태 갱신
        """
        existing = self.run_repo.find_latest_success_by_execution_date(
            self.pipeline.name, execution_date
        )
        if existing:
            return existing

        pipeline_run = PipelineRun(
            pipeline_name=self.pipeline.name,
            execution_date=execution_date,
            status="running",
            started_at=datetime.now(),
            trigger_type=trigger_type,
        )
        self.run_repo.create(pipeline_run)

        context = StageContext(
            pipeline_name=self.pipeline.name,
            execution_date=execution_date,
            table_config=self.pipeline.table_config,
            run_id=pipeline_run.id,
            chunk_size=self.pipeline.chunk_size,
        )

        failed = False
        for stage in self.pipeline.stages:
            step_run = StepRun(
                pipeline_run_id=pipeline_run.id,
                step_name=stage.name,
                status="pending",
            )
            self.step_repo.create(step_run)

            if failed:
                self.state_machine.transition(step_run, StageState.SKIPPED)
                self.step_repo.update_status(
                    step_run.id,
                    StageState.SKIPPED.value,
                    finished_at=datetime.now(),
                )
                continue

            self.state_machine.transition(step_run, StageState.RUNNING)
            self.step_repo.update_status(
                step_run.id,
                StageState.RUNNING.value,
                started_at=datetime.now(),
            )

            try:
                result = self._execute_stage_with_retry(stage, context, step_run)
                self.state_machine.transition(step_run, StageState.SUCCESS)
                self.step_repo.update_status(
                    step_run.id,
                    StageState.SUCCESS.value,
                    finished_at=datetime.now(),
                    records_processed=result.records_processed,
                )
            except Exception as exc:
                # RetryError는 마지막 시도의 원본 예외로 언래핑
                original_exc = exc.last_attempt.exception() if isinstance(exc, RetryError) else exc
                failed = True
                self.state_machine.transition(step_run, StageState.FAILED)
                self.step_repo.update_status(
                    step_run.id,
                    StageState.FAILED.value,
                    finished_at=datetime.now(),
                    error_message=str(original_exc),
                )
                if stage.retry_config.on_failure_callback:
                    stage.retry_config.on_failure_callback(context, original_exc)

        final_status = "failed" if failed else "success"
        self.run_repo.update_status(
            pipeline_run.id, final_status, finished_at=datetime.now()
        )
        pipeline_run.status = final_status
        return pipeline_run

    def _execute_stage_with_retry(
        self, stage: StageDefinition, context: StageContext, step_run: StepRun
    ) -> StageResult:
        """Tenacity 재시도 데코레이터를 동적으로 적용하여 단계 실행.

        RetryConfig 기반으로 재시도 파라미터를 설정하고,
        재시도 직전 retry_count를 SQLite에 영속화한다.
        """
        def before_sleep(retry_state):
            before_sleep_log(logger, logging.WARNING)(retry_state)
            self.step_repo.update_status(
                step_run.id,
                StageState.RUNNING.value,
                retry_count=retry_state.attempt_number,
            )

        retrying = retry(
            stop=stop_after_attempt(stage.retry_config.max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=stage.retry_config.min_wait_seconds,
                max=stage.retry_config.max_wait_seconds,
            ),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep,
        )
        retryable_fn = retrying(stage.callable)
        return retryable_fn(context)
