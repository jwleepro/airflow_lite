from airflow_lite.engine.stage import StageState
from airflow_lite.storage.models import StepRun
from airflow_lite.storage.repository import StepRunRepository


class InvalidTransitionError(Exception):
    """유효하지 않은 상태 전이 시 발생."""


class StageStateMachine:
    """유한 상태 머신으로 단계 상태를 관리한다.
    모든 전이는 이 클래스를 통해서만 수행되며, 전이 즉시 SQLite에 영속화."""

    VALID_TRANSITIONS: dict[StageState, set[StageState]] = {
        StageState.PENDING: {StageState.RUNNING, StageState.SKIPPED},
        StageState.RUNNING: {StageState.SUCCESS, StageState.FAILED},
        StageState.FAILED:  {StageState.PENDING},
    }

    def __init__(self, step_repo: StepRunRepository):
        self.step_repo = step_repo

    def transition(self, step_run: StepRun, new_state: StageState) -> None:
        """상태 전이. 유효하지 않은 전이 시 InvalidTransitionError 발생.
        전이마다 SQLite에 즉시 저장하여 크래시 복구를 보장한다."""
        current = StageState(step_run.status)
        if new_state not in self.VALID_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(
                f"Invalid transition: {current} -> {new_state}"
            )
        self.step_repo.update_status(step_run.id, status=new_state.value)
        step_run.status = new_state.value
