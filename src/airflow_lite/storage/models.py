from dataclasses import dataclass, field
from datetime import date, datetime
import uuid


@dataclass
class PipelineRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_name: str = ""
    execution_date: date = None
    status: str = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trigger_type: str = "scheduled"
    created_at: datetime | None = None


@dataclass
class StepRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_run_id: str = ""
    step_name: str = ""
    status: str = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    records_processed: int = 0
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime | None = None


@dataclass
class ConnectionModel:
    conn_id: str
    conn_type: str = "oracle"
    host: str | None = None
    port: int | None = None
    schema: str | None = None
    login: str | None = None
    password: str | None = None
    extra: str | None = None
    description: str | None = None


@dataclass
class VariableModel:
    key: str
    val: str | None = None
    description: str | None = None


@dataclass
class PoolModel:
    pool_name: str
    slots: int = 1
    description: str | None = None


@dataclass
class PipelineModel:
    name: str
    table: str
    source_where_template: str | None = None
    source_bind_params: str | dict | None = None
    strategy: str = "full"
    schedule: str = "0 2 * * *"
    chunk_size: int | None = None
    columns: str | None = None
    incremental_key: str | None = None
