# Task-003: 파이프라인 엔진 코어

## 목적

파이프라인의 단계별 실행, 상태 관리, 재시도를 담당하는 엔진 코어를 구현한다. StageState enum 기반 유한 상태 머신으로 단계 상태를 관리하고, Tenacity로 재시도를 처리한다.

## 입력

- Task-002의 storage 모듈 (PipelineRunRepository, StepRunRepository, StageStateMachine 상태 영속화용)
- `RetryConfig` dataclass (architecture.md에 정의)

## 출력

- `src/airflow_lite/engine/stage.py` — StageDefinition, StageState enum
- `src/airflow_lite/engine/state_machine.py` — StageStateMachine
- `src/airflow_lite/engine/pipeline.py` — PipelineDefinition, PipelineRunner

## 구현 제약

- 모든 상태 전이는 `StageStateMachine.transition()`을 통해서만 수행
- 전이 즉시 SQLite에 영속화 (크래시 복구 보장, NFR-04)
- 특정 단계 실패 시 후속 단계를 SKIPPED 처리 (실패 격리, P3)
- 동일 execution_date 재실행 시 결과 동일 (멱등성, P2)

## 구현 상세

### stage.py — StageState enum + StageDefinition

```python
from enum import Enum
from dataclasses import dataclass
from typing import Callable
from datetime import date

class StageState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class StageContext:
    pipeline_name: str
    execution_date: date
    table_config: "PipelineConfig"  # config/settings.py의 PipelineConfig
    run_id: str
    chunk_size: int

@dataclass
class StageResult:
    records_processed: int = 0
    error_message: str | None = None

@dataclass
class RetryConfig:
    max_attempts: int = 3
    min_wait_seconds: int = 4
    max_wait_seconds: int = 60
    on_failure_callback: Callable[[StageContext, Exception], None] | None = None

@dataclass
class StageDefinition:
    name: str
    callable: Callable[[StageContext], StageResult]
    retry_config: RetryConfig
```

### state_machine.py — 상태 전이 관리

```python
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
        전이마다 SQLite에 즉시 저장."""
        current = StageState(step_run.status)
        if new_state not in self.VALID_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(
                f"Invalid transition: {current} -> {new_state}"
            )
        self.step_repo.update_status(step_run.id, status=new_state.value)
        step_run.status = new_state.value

class InvalidTransitionError(Exception):
    pass
```

**상태 전이 다이어그램:**

```
[*] --> PENDING
PENDING --> RUNNING : 실행 시작
RUNNING --> SUCCESS : 정상 완료
RUNNING --> FAILED : 에러 발생 (재시도 소진)
FAILED --> PENDING : 재시도 요청
PENDING --> SKIPPED : 선행 단계 실패
```

### pipeline.py — PipelineRunner (재시도 포함)

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger("airflow_lite.engine.pipeline")

@dataclass
class PipelineDefinition:
    name: str
    stages: list[StageDefinition]    # 순서대로 실행
    strategy: "MigrationStrategy"

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

        1. PipelineRun 레코드 생성
        2. 각 StageDefinition을 순차 실행
        3. 단계 실패 시 후속 단계를 SKIPPED 처리
        4. 모든 단계 완료 후 PipelineRun 상태 갱신
        """

    def _execute_stage_with_retry(
        self, stage: StageDefinition, context: StageContext, step_run: StepRun
    ) -> StageResult:
        """Tenacity 재시도 데코레이터를 동적으로 적용하여 단계 실행.

        RetryConfig 기반으로 재시도 파라미터를 설정한다.
        """
        # Tenacity retry 데코레이터를 RetryConfig에서 동적으로 구성
        retrying = retry(
            stop=stop_after_attempt(stage.retry_config.max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=stage.retry_config.min_wait_seconds,
                max=stage.retry_config.max_wait_seconds,
            ),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        retryable_fn = retrying(stage.callable)
        return retryable_fn(context)
```

### 재시도 대상 에러 정의

```python
# ORACLE 환경 특화 재시도 대상 Oracle 에러
RETRYABLE_ORACLE_ERRORS = {3113, 3114, 12541, 12170, 12571}

# 에러 코드별 설명:
# ORA-03113: end-of-file on communication channel → 재시도 O
# ORA-03114: not connected to ORACLE             → 재시도 O
# ORA-12541: TNS: no listener                    → 재시도 O
# ORA-12170: TNS: connect timeout                → 재시도 O
# ORA-12571: TNS: packet writer failure           → 재시도 O
# ORA-00001: unique constraint violation          → 재시도 X (데이터 오류)
# ORA-01400: cannot insert NULL                   → 재시도 X (데이터 오류)

class RetryableOracleError(Exception):
    """재시도 가능한 Oracle 에러를 래핑"""

class NonRetryableOracleError(Exception):
    """재시도 불가 에러 (데이터/로직 오류)"""

RETRYABLE_EXCEPTIONS = (RetryableOracleError, ConnectionError, TimeoutError)
```

### 단계 실패 처리 흐름

1. `_execute_stage_with_retry()`에서 재시도 소진 시 예외 전파
2. `run()`에서 예외 캐치 → 해당 단계를 `FAILED`로 전이
3. `on_failure_callback` 호출 (설정된 경우)
4. 후속 모든 단계를 `SKIPPED`로 전이
5. PipelineRun 상태를 `failed`로 갱신

## 완료 조건

- [ ] `StageState` enum 5개 상태 정의
- [ ] `StageStateMachine` 유효 전이 테스트 (모든 허용/금지 조합)
- [ ] `InvalidTransitionError` 발생 테스트
- [ ] `PipelineRunner.run()` 순차 실행 테스트 (모든 단계 성공)
- [ ] 단계 실패 시 후속 단계 SKIPPED 처리 테스트
- [ ] Tenacity 재시도 동작 테스트 (재시도 후 성공 / 재시도 소진 후 실패)
- [ ] `on_failure_callback` 호출 테스트
- [ ] 상태 전이마다 SQLite 영속화 확인

## 참고 (선택)

- 상태 전이 다이어그램: `docs/system_design/architecture.md` 섹션 3.2
- PipelineRunner 인터페이스: `docs/system_design/architecture.md` 섹션 3.3
- 재시도 에러 목록: `docs/system_design/architecture.md` 섹션 3.6
