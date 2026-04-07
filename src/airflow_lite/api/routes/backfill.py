from fastapi import APIRouter, HTTPException, Request

from airflow_lite.api.routes.pipelines import _build_run_response_with_steps
from airflow_lite.api.schemas import BackfillRequest, PipelineRunResponse

router = APIRouter(tags=["backfill"])


def _resolve_backfill_manager(entry):
    if hasattr(entry, "run_backfill"):
        return entry
    if callable(entry):
        return entry()
    raise TypeError("backfill_map 항목은 manager 또는 manager factory여야 합니다.")


@router.post("/pipelines/{name}/backfill", response_model=list[PipelineRunResponse])
def request_backfill(name: str, body: BackfillRequest, req: Request):
    """백필 요청. start_date~end_date 범위를 월별 분할하여 실행."""
    backfill_map = req.app.state.backfill_map
    if name not in backfill_map:
        raise HTTPException(status_code=404, detail=f"파이프라인 '{name}'을 찾을 수 없습니다.")

    manager = _resolve_backfill_manager(backfill_map[name])
    runs = manager.run_backfill(
        pipeline_name=name,
        start_date=body.start_date,
        end_date=body.end_date,
        force_rerun=body.force,
    )

    step_repo = req.app.state.step_repo
    return [_build_run_response_with_steps(run, step_repo) for run in runs]
