from fastapi import APIRouter, Request

from airflow_lite.api.language import resolve_request_language
from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.routes._web_common import redirect
from airflow_lite.api.routes.web_admin import router as admin_router
from airflow_lite.api.routes.web_analytics import router as analytics_router
from airflow_lite.api.routes.web_browse import router as browse_router
from airflow_lite.api.routes.web_exports import router as exports_router
from airflow_lite.api.routes.web_monitor import router as monitor_router

router = APIRouter(include_in_schema=False)


@router.get("/")
def redirect_root(request: Request):
    requested_lang = request.query_params.get("lang")
    if requested_lang is None:
        return redirect(MONITOR_PATH)
    language = resolve_request_language(request, requested_lang)
    return redirect(MONITOR_PATH, language=language)


router.include_router(admin_router)
router.include_router(monitor_router)
router.include_router(analytics_router)
router.include_router(browse_router)
router.include_router(exports_router)
