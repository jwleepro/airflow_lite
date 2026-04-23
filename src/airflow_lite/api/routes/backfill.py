import logging

from fastapi import APIRouter, HTTPException, Request

from airflow_lite.api.dependencies import get_dispatch_service
from airflow_lite.api.schemas import BackfillRequest
from airflow_lite.logging_config.decorators import log_execution
from airflow_lite.service.dispatch_service import PipelineBusyError

router = APIRouter(tags=["backfill"])
logger = logging.getLogger("airflow_lite.api.routes.backfill")


@router.post("/pipelines/{name}/backfill", status_code=202)
@log_execution(log_args=True, level=logging.INFO)
def request_backfill(name: str, body: BackfillRequest, req: Request):
    """백필 요청. dispatcher 를 통해 비동기 실행. start_date~end_date 범위를 월별 분할하여 워커가 실행."""
    dispatcher = get_dispatch_service(req)
    if not dispatcher.has_backfill(name):
        raise HTTPException(status_code=404, detail=f"파이프라인 '{name}'은 백필이 설정되지 않았습니다.")
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="end_date는 start_date보다 같거나 이후여야 합니다.")

    try:
        dispatcher.submit_backfill(
            pipeline_name=name,
            start_date=body.start_date,
            end_date=body.end_date,
            force_rerun=body.force,
        )
    except PipelineBusyError as exc:
        raise HTTPException(status_code=409, detail=exc.to_detail()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "queued", "message": "백필이 큐에 추가되었습니다"}
