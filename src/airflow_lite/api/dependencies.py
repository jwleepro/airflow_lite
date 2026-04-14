from fastapi import HTTPException, Query, Request

from airflow_lite.api.language import resolve_request_language


def get_query_service(request: Request):
    query_service = getattr(request.app.state, "analytics_query_service", None)
    if query_service is None:
        raise HTTPException(status_code=503, detail="analytics query service is not configured.")
    return query_service


def get_export_service(request: Request):
    export_service = getattr(request.app.state, "analytics_export_service", None)
    if export_service is None:
        raise HTTPException(status_code=503, detail="analytics export service is not configured.")
    return export_service


def get_language(request: Request, lang: str | None = Query(default=None)) -> str:
    return resolve_request_language(request, lang)


# ---------- app.state 접근 헬퍼 ----------
#
# 라우트가 ``request.app.state.<name>`` 을 직접 집어가는 대신 여기서 꺼낸다.
# 이름/타입 변경 시 수정 지점을 한 곳으로 모으고, 누락된 상태는 503 으로 방어.


def get_run_repo(request: Request):
    run_repo = getattr(request.app.state, "run_repo", None)
    if run_repo is None:
        raise HTTPException(status_code=503, detail="run_repo is not configured.")
    return run_repo


def get_step_repo(request: Request):
    step_repo = getattr(request.app.state, "step_repo", None)
    if step_repo is None:
        raise HTTPException(status_code=503, detail="step_repo is not configured.")
    return step_repo


def get_runner_map(request: Request) -> dict:
    return getattr(request.app.state, "runner_map", {}) or {}


def get_backfill_map(request: Request) -> dict:
    return getattr(request.app.state, "backfill_map", {}) or {}
