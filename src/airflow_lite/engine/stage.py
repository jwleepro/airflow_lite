from enum import Enum
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING
from datetime import date

if TYPE_CHECKING:
    from airflow_lite.config.settings import PipelineConfig


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
    table_config: "PipelineConfig | None"
    run_id: str
    chunk_size: int
    trigger_type: str = "scheduled"


@dataclass
class StageResult:
    records_processed: int = 0
    error_message: str | None = None


@dataclass
class RetryConfig:
    max_attempts: int = 3
    min_wait_seconds: int = 4
    max_wait_seconds: int = 60
    on_failure_callback: Callable[["StageContext", Exception], None] | None = None


@dataclass
class StageDefinition:
    name: str
    callable: Callable[["StageContext"], StageResult]
    retry_config: RetryConfig


# Oracle 환경 특화 재시도 대상 에러 코드
# ORA-03113: end-of-file on communication channel
# ORA-03114: not connected to ORACLE
# ORA-12541: TNS: no listener
# ORA-12170: TNS: connect timeout
# ORA-12571: TNS: packet writer failure
RETRYABLE_ORACLE_ERRORS = {3113, 3114, 12541, 12170, 12571}


class RetryableOracleError(Exception):
    """재시도 가능한 Oracle 에러를 래핑 (네트워크/연결 장애)."""


class NonRetryableOracleError(Exception):
    """재시도 불가 에러 (데이터/로직 오류: ORA-00001, ORA-01400 등)."""


RETRYABLE_EXCEPTIONS = (RetryableOracleError, ConnectionError, TimeoutError)
