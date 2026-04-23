import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from airflow_lite.api.dependencies import (
    get_dispatch_service,
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
from airflow_lite.logging_config.decorators import log_execution
from airflow_lite.service.dispatch_service import PipelineBusyError

router = APIRouter(tags=["pipelines"])
logger = logging.getLogger("airflow_lite.api.routes.pipelines")


@router.post("/pipelines/{name}/trigger", response_model=PipelineRunResponse)
@log_execution(log_args=True, level=logging.INFO)
def trigger_pipeline(name: str, body: TriggerRequest, req: Request):
    """수동 트리거. queued run 을 즉시 반환(202), 실행은 워커가 소비."""
    runner_map = get_runner_map(req)
    if name not in runner_map:
        raise HTTPException(status_code=404, detail=f"파이프라인 '{name}'을 찾을 수 없습니다.")

    dispatcher = get_dispatch_service(req)
    execution_date = body.execution_date or date.today()
    try:
        run = dispatcher.submit_manual_run(
            pipeline_name=name,
            execution_date=execution_date,
            force_rerun=body.force,
            trigger_type="manual",
        )
    except PipelineBusyError as exc:
        raise HTTPException(status_code=409, detail=exc.to_detail()) from exc
    payload = build_run_response_with_steps(run, get_step_repo(req))
    # 이미 종결된 run(success 재사용)은 200, 새로 큐잉된 건 202 로 접수됨을 명시.
    status_code = 200 if run.status in ("success", "failed") else 202
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


@router.get("/pipelines", response_model=list[PipelineInfo])
@log_execution(level=logging.DEBUG)
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
@log_execution(log_args=True, level=logging.DEBUG)
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
@log_execution(log_args=True, level=logging.DEBUG)
def get_run_detail(name: str, run_id: str, req: Request):
    """실행 상세 조회. 단계별 상태 포함."""
    run_repo = get_run_repo(req)

    run = run_repo.find_by_id(run_id)
    if run is None or run.pipeline_name != name:
        raise HTTPException(status_code=404, detail=f"실행 ID '{run_id}'를 찾을 수 없습니다.")

    return build_run_response_with_steps(run, get_step_repo(req))
