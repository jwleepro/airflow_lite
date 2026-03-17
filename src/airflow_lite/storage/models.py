from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
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
