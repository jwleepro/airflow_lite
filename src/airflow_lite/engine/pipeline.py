import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Callable

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
        on_run_success: Callable[[StageContext], None] | None = None,
    ):
        self.pipeline = pipeline
        self.run_repo = run_repo
        self.step_repo = step_repo
        self.state_machine = state_machine
        self.on_run_success = on_run_success

    def prepare_run(
        self,
        execution_date: date,
        trigger_type: str = "scheduled",
        force_rerun: bool = False,
    ) -> PipelineRun:
        """실행 엔트리를 DB에 queued 상태로 등록한다.

        중복 정책:
        - force_rerun=False 이고 동일 execution_date 성공 실행 존재 → 기존 반환
        - force_rerun=False 이고 동일 execution_date queued/running 존재 → 기존 반환
        - 그 외 → queued 상태로 신규 INSERT

        stage는 여기서 실행하지 않는다. 호출자가 execute_prepared_run을 호출해야 한다.
        """
        if not force_rerun:
            existing_success = self.run_repo.find_latest_success_by_execution_date(
                self.pipeline.name, execution_date
            )
            if existing_success:
                return existing_success
            existing_active = self.run_repo.find_active_by_execution_date(
                self.pipeline.name, execution_date
            )
            if existing_active:
                return existing_active

        pipeline_run = PipelineRun(
            pipeline_name=self.pipeline.name,
            execution_date=execution_date,
            status="queued",
            started_at=None,
            trigger_type=trigger_type,
        )
        self.run_repo.create(pipeline_run)
        return pipeline_run

    def execute_prepared_run(self, pipeline_run: PipelineRun) -> PipelineRun:
        """queued 상태인 run을 소비하여 running → success/failed로 전이시킨다.

        - running 전이 + started_at 갱신
        - 각 StageDefinition 순차 실행
        - 단계 실패 시 후속 단계 SKIPPED (실패 격리)
        - 예외가 stage 단위를 벗어나면 failed로 마감 후 재발생
        """
        if pipeline_run.status not in ("queued", "running"):
            # 이미 종결된 run(성공 재사용 케이스 등)이면 그대로 반환
            return pipeline_run

        started_at = datetime.now()
        self.run_repo.mark_running(pipeline_run.id, started_at=started_at)
        pipeline_run.status = "running"
        pipeline_run.started_at = started_at

        context = StageContext(
            pipeline_name=self.pipeline.name,
            execution_date=pipeline_run.execution_date,
            table_config=self.pipeline.table_config,
            run_id=pipeline_run.id,
            chunk_size=self.pipeline.chunk_size,
            trigger_type=pipeline_run.trigger_type,
        )

        failed = False
        try:
            for stage in self.pipeline.stages:
                step_run = StepRun(
                    pipeline_run_id=pipeline_run.id,
                    step_name=stage.name,
                    status="pending",
                )
                self.step_repo.create(step_run)

                if failed:
                    self._mark_skipped(step_run)
                    continue

                self._mark_running(step_run)

                try:
                    result = self._execute_stage_with_retry(stage, context, step_run)
                    self._mark_success(step_run, records_processed=result.records_processed)
                except Exception as exc:
                    original_exc = exc.last_attempt.exception() if isinstance(exc, RetryError) else exc
                    failed = True
                    self._mark_failed(
                        step_run,
                        error_message=str(original_exc),
                        retry_count=self._resolve_retry_count(exc),
                    )
                    if stage.retry_config.on_failure_callback:
                        stage.retry_config.on_failure_callback(context, original_exc)
        except BaseException:
            # stage 단위를 벗어나는 예외도 run 상태를 failed로 마감해야 DB가 running에 고립되지 않는다.
            self.run_repo.update_status(
                pipeline_run.id, "failed", finished_at=datetime.now()
            )
            pipeline_run.status = "failed"
            raise

        final_status = "failed" if failed else "success"
        self.run_repo.update_status(
            pipeline_run.id, final_status, finished_at=datetime.now()
        )
        pipeline_run.status = final_status

        if self.pipeline.strategy is not None:
            try:
                self.pipeline.strategy.finalize_run(context, succeeded=not failed)
            except Exception:
                logger.exception(
                    "파이프라인 후처리 실패: %s / %s",
                    self.pipeline.name,
                    pipeline_run.execution_date,
                )

        if not failed and self.on_run_success:
            self.on_run_success(context)

        return pipeline_run

    def run(
        self,
        execution_date: date,
        trigger_type: str = "scheduled",
        force_rerun: bool = False,
    ) -> PipelineRun:
        """prepare_run → execute_prepared_run 호환 래퍼.

        CLI / 기존 단위 테스트가 사용하던 동기 실행 진입점.
        비동기 경로(dispatcher)는 두 메서드를 직접 호출한다.
        """
        pipeline_run = self.prepare_run(execution_date, trigger_type, force_rerun)
        if pipeline_run.status in ("queued",):
            return self.execute_prepared_run(pipeline_run)
        return pipeline_run

    def _mark_skipped(self, step_run: StepRun) -> None:
        self.state_machine.transition(step_run, StageState.SKIPPED)
        self.step_repo.update_status(
            step_run.id,
            StageState.SKIPPED.value,
            finished_at=datetime.now(),
        )

    def _mark_running(self, step_run: StepRun) -> None:
        self.state_machine.transition(step_run, StageState.RUNNING)
        self.step_repo.update_status(
            step_run.id,
            StageState.RUNNING.value,
            started_at=datetime.now(),
        )

    def _mark_success(self, step_run: StepRun, *, records_processed: int) -> None:
        self.state_machine.transition(step_run, StageState.SUCCESS)
        self.step_repo.update_status(
            step_run.id,
            StageState.SUCCESS.value,
            finished_at=datetime.now(),
            records_processed=records_processed,
        )

    def _mark_failed(
        self, step_run: StepRun, *, error_message: str, retry_count: int
    ) -> None:
        self.state_machine.transition(step_run, StageState.FAILED)
        self.step_repo.update_status(
            step_run.id,
            StageState.FAILED.value,
            finished_at=datetime.now(),
            error_message=error_message,
            retry_count=retry_count,
        )

    def _mark_retry(self, step_run: StepRun, *, attempt_number: int) -> None:
        """재시도 직전 현재 시도 횟수만 영속화."""
        self.step_repo.update_status(
            step_run.id,
            StageState.RUNNING.value,
            retry_count=attempt_number,
        )

    @staticmethod
    def _resolve_retry_count(exc: Exception) -> int:
        if isinstance(exc, RetryError):
            return max(exc.last_attempt.attempt_number - 1, 0)
        return 0

    def _execute_stage_with_retry(
        self, stage: StageDefinition, context: StageContext, step_run: StepRun
    ) -> StageResult:
        """Tenacity 재시도 데코레이터를 동적으로 적용하여 단계 실행.

        RetryConfig 기반으로 재시도 파라미터를 설정하고,
        재시도 직전 retry_count를 SQLite에 영속화한다.
        """
        def before_sleep(retry_state):
            before_sleep_log(logger, logging.WARNING)(retry_state)
            self._mark_retry(step_run, attempt_number=retry_state.attempt_number)

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
