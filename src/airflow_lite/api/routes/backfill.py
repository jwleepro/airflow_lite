from fastapi import APIRouter, HTTPException, Request

from airflow_lite.api.schemas import BackfillRequest, PipelineRunResponse, StepRunResponse

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
    )

    step_repo = req.app.state.step_repo
    result = []
    for run in runs:
        steps = step_repo.find_by_pipeline_run(run.id) if step_repo else []
        result.append(
            PipelineRunResponse(
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
                    for s in steps
                ],
            )
        )
    return result
