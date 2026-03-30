from datetime import date

from fastapi import APIRouter, HTTPException, Request

from airflow_lite.api.schemas import (
    PaginatedResponse,
    PipelineInfo,
    PipelineRunResponse,
    StepRunResponse,
    TriggerRequest,
)

router = APIRouter(tags=["pipelines"])


def _resolve_runner(entry):
    if hasattr(entry, "run"):
        return entry
    if callable(entry):
        return entry()
    raise TypeError("runner_map 항목은 runner 또는 runner factory여야 합니다.")


def build_run_response(run, step_runs) -> PipelineRunResponse:
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


@router.post("/pipelines/{name}/trigger", response_model=PipelineRunResponse)
def trigger_pipeline(name: str, body: TriggerRequest, req: Request):
    """수동 즉시 실행. execution_date 미지정 시 오늘 날짜 사용."""
    runner_map = req.app.state.runner_map
    if name not in runner_map:
        raise HTTPException(status_code=404, detail=f"파이프라인 '{name}'을 찾을 수 없습니다.")

    execution_date = body.execution_date or date.today()
    runner = _resolve_runner(runner_map[name])
    run = runner.run(
        execution_date=execution_date,
        trigger_type="manual",
        force_rerun=body.force,
    )

    step_repo = req.app.state.step_repo
    steps = step_repo.find_by_pipeline_run(run.id) if step_repo else []
    return build_run_response(run, steps)


@router.get("/pipelines", response_model=list[PipelineInfo])
def list_pipelines(req: Request):
    """설정에 정의된 모든 파이프라인 목록 조회."""
    settings = req.app.state.settings
    return [
        PipelineInfo(
            name=p.name,
            table=p.table,
            strategy=p.strategy,
            schedule=p.schedule,
        )
        for p in settings.pipelines
    ]


@router.get("/pipelines/{name}/runs", response_model=PaginatedResponse)
def list_runs(name: str, req: Request, page: int = 1, page_size: int = 50):
    """파이프라인 실행 이력 조회 (pagination).

    응답 포맷 (AG Grid 호환):
    {
        "items": [...],
        "total": 120,
        "page": 1,
        "page_size": 50
    }
    """
    run_repo = req.app.state.run_repo
    if run_repo is None:
        raise HTTPException(status_code=503, detail="레포지토리가 초기화되지 않았습니다.")

    pipeline_names = [p.name for p in req.app.state.settings.pipelines]
    if name not in pipeline_names:
        raise HTTPException(status_code=404, detail=f"파이프라인 '{name}'을 찾을 수 없습니다.")

    items, total = run_repo.find_by_pipeline_paginated(name, page=page, page_size=page_size)
    step_repo = req.app.state.step_repo

    run_responses = []
    for run in items:
        steps = step_repo.find_by_pipeline_run(run.id) if step_repo else []
        run_responses.append(build_run_response(run, steps))

    return PaginatedResponse(items=run_responses, total=total, page=page, page_size=page_size)


@router.get("/pipelines/{name}/runs/{run_id}", response_model=PipelineRunResponse)
def get_run_detail(name: str, run_id: str, req: Request):
    """실행 상세 조회. 단계별 상태 포함."""
    run_repo = req.app.state.run_repo
    if run_repo is None:
        raise HTTPException(status_code=503, detail="레포지토리가 초기화되지 않았습니다.")

    run = run_repo.find_by_id(run_id)
    if run is None or run.pipeline_name != name:
        raise HTTPException(status_code=404, detail=f"실행 ID '{run_id}'를 찾을 수 없습니다.")

    step_repo = req.app.state.step_repo
    steps = step_repo.find_by_pipeline_run(run.id) if step_repo else []
    return build_run_response(run, steps)
