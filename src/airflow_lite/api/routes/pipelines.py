from datetime import date

from fastapi import APIRouter, HTTPException, Request

from airflow_lite.api._resolver import resolve_runner
from airflow_lite.api.dependencies import (
    get_run_repo,
    get_runner_map,
    get_step_repo,
)
from airflow_lite.api.schemas import (
    PaginatedResponse,
    PipelineInfo,
    PipelineRunResponse,
    TriggerRequest,
    build_run_response_with_steps,
)

router = APIRouter(tags=["pipelines"])


@router.post("/pipelines/{name}/trigger", response_model=PipelineRunResponse)
def trigger_pipeline(name: str, body: TriggerRequest, req: Request):
    """수동 즉시 실행. execution_date 미지정 시 오늘 날짜 사용."""
    runner_map = get_runner_map(req)
    if name not in runner_map:
        raise HTTPException(status_code=404, detail=f"파이프라인 '{name}'을 찾을 수 없습니다.")

    execution_date = body.execution_date or date.today()
    runner = resolve_runner(runner_map[name])
    run = runner.run(
        execution_date=execution_date,
        trigger_type="manual",
        force_rerun=body.force,
    )

    return build_run_response_with_steps(run, get_step_repo(req))


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
    run_repo = get_run_repo(req)

    pipeline_names = [p.name for p in req.app.state.settings.pipelines]
    if name not in pipeline_names:
        raise HTTPException(status_code=404, detail=f"파이프라인 '{name}'을 찾을 수 없습니다.")

    items, total = run_repo.find_by_pipeline_paginated(name, page=page, page_size=page_size)
    step_repo = get_step_repo(req)

    run_responses = [build_run_response_with_steps(run, step_repo) for run in items]

    return PaginatedResponse(items=run_responses, total=total, page=page, page_size=page_size)


@router.get("/pipelines/{name}/runs/{run_id}", response_model=PipelineRunResponse)
def get_run_detail(name: str, run_id: str, req: Request):
    """실행 상세 조회. 단계별 상태 포함."""
    run_repo = get_run_repo(req)

    run = run_repo.find_by_id(run_id)
    if run is None or run.pipeline_name != name:
        raise HTTPException(status_code=404, detail=f"실행 ID '{run_id}'를 찾을 수 없습니다.")

    return build_run_response_with_steps(run, get_step_repo(req))
