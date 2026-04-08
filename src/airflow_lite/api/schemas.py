from pydantic import BaseModel
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airflow_lite.storage.models import PipelineRun, StepRun
    from airflow_lite.storage.repository import StepRunRepository


class TriggerRequest(BaseModel):
    execution_date: date | None = None  # 미지정 시 오늘
    force: bool = False


class BackfillRequest(BaseModel):
    start_date: date
    end_date: date
    force: bool = False


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


# ---------------------------------------------------------------------------
# Run response builders — 여러 라우트에서 공유하는 유틸
# ---------------------------------------------------------------------------


def build_run_response(run: "PipelineRun", step_runs: "list[StepRun]") -> PipelineRunResponse:
    """PipelineRun + StepRun 목록을 API 응답 모델로 변환."""
    return PipelineRunResponse(
        id=run.id,
        pipeline_name=run.pipeline_name,
        execution_date=run.execution_date,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        trigger_type=run.trigger_type,
        steps=[
            StepRunResponse(
                step_name=s.step_name,
                status=s.status,
                started_at=s.started_at,
                finished_at=s.finished_at,
                records_processed=s.records_processed,
                error_message=s.error_message,
                retry_count=s.retry_count,
            )
            for s in step_runs
        ],
    )


def build_run_response_with_steps(
    run: "PipelineRun", step_repo: "StepRunRepository | None"
) -> PipelineRunResponse:
    """PipelineRun에 대응하는 StepRun을 조회하여 API 응답 모델로 변환."""
    step_runs = step_repo.find_by_pipeline_run(run.id) if step_repo else []
    return build_run_response(run, step_runs)
