"""RunStateManager — step run 상태 전이 전담 모듈.

PipelineRunner 에서 _mark_* 메서드들을 분리한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from airflow_lite.engine.state_machine import StageStateMachine
from airflow_lite.engine.stage import StageState
from airflow_lite.storage.models import StepRun
from airflow_lite.storage.repository import StepRunRepository


class RunStateManager:
    """step run 의 상태 전이와 영속화를 담당한다."""

    def __init__(
        self,
        state_machine: StageStateMachine,
        step_repo: StepRunRepository,
        clock: Callable[[], datetime] | None = None,
    ):
        self._state_machine = state_machine
        self._step_repo = step_repo
        self._clock = clock or datetime.now

    def mark_skipped(self, step_run: StepRun) -> None:
        self._state_machine.transition(step_run, StageState.SKIPPED)
        self._step_repo.update_status(
            step_run.id,
            StageState.SKIPPED.value,
            finished_at=self._clock(),
        )

    def mark_running(self, step_run: StepRun) -> None:
        self._state_machine.transition(step_run, StageState.RUNNING)
        self._step_repo.update_status(
            step_run.id,
            StageState.RUNNING.value,
            started_at=self._clock(),
        )

    def mark_success(self, step_run: StepRun, *, records_processed: int) -> None:
        self._state_machine.transition(step_run, StageState.SUCCESS)
        self._step_repo.update_status(
            step_run.id,
            StageState.SUCCESS.value,
            finished_at=self._clock(),
            records_processed=records_processed,
        )

    def mark_failed(self, step_run: StepRun, *, error_message: str, retry_count: int) -> None:
        self._state_machine.transition(step_run, StageState.FAILED)
        self._step_repo.update_status(
            step_run.id,
            StageState.FAILED.value,
            finished_at=self._clock(),
            error_message=error_message,
            retry_count=retry_count,
        )

    def mark_retry(self, step_run: StepRun, *, attempt_number: int) -> None:
        self._step_repo.update_status(
            step_run.id,
            StageState.RUNNING.value,
            retry_count=attempt_number,
        )

    def create_step(self, step_run: StepRun) -> None:
        self._step_repo.create(step_run)
