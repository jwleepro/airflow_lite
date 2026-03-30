from pydantic import BaseModel
from datetime import date, datetime


class TriggerRequest(BaseModel):
    execution_date: date | None = None  # 미지정 시 오늘
    force: bool = False


class BackfillRequest(BaseModel):
    start_date: date
    end_date: date
    force: bool = True


class StepRunResponse(BaseModel):
    step_name: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    records_processed: int
    error_message: str | None
    retry_count: int


class PipelineRunResponse(BaseModel):
    id: str
    pipeline_name: str
    execution_date: date
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    trigger_type: str
    steps: list[StepRunResponse]


class PaginatedResponse(BaseModel):
    items: list[PipelineRunResponse]
    total: int
    page: int
    page_size: int


class PipelineInfo(BaseModel):
    name: str
    table: str
    strategy: str
    schedule: str
