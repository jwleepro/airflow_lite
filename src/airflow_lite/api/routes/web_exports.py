from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from airflow_lite.api.dependencies import get_language
from airflow_lite.api.language import resolve_request_language
from airflow_lite.api.paths import (
    MONITOR_EXPORTS_PATH,
    MONITOR_EXPORT_DELETE_COMPLETED_PATH,
    MONITOR_EXPORT_DELETE_JOB_PATH,
)
from airflow_lite.api.forms import first_value as _first_value
from airflow_lite.api.presenters.exports import build_export_page_data
from airflow_lite.api.routes._web_common import (
    not_configured,
    read_form_data,
    redirect,
    try_get_export_service,
)
from airflow_lite.api.webui_exports import render_export_jobs_page
from airflow_lite.export import AnalyticsExportJobNotFoundError

router = APIRouter(include_in_schema=False)


@router.post(MONITOR_EXPORT_DELETE_JOB_PATH)
async def delete_export_job_from_monitor(request: Request, request_language: str = Depends(get_language)):
    export_service, err = try_get_export_service(request, request_language)
    if err:
        return err

    form_data = await read_form_data(request)
    job_id = _first_value(form_data, "job_id")
    dataset = _first_value(form_data, "dataset")
    language = resolve_request_language(request, _first_value(form_data, "lang"))
    if job_id:
        try:
            export_service.delete_job(job_id)
        except AnalyticsExportJobNotFoundError:
            pass

    return redirect(MONITOR_EXPORTS_PATH, language=language, dataset=dataset)


@router.post(MONITOR_EXPORT_DELETE_COMPLETED_PATH)
async def delete_completed_exports_from_monitor(request: Request, request_language: str = Depends(get_language)):
    export_service, err = try_get_export_service(request, request_language)
    if err:
        return err

    form_data = await read_form_data(request)
    dataset = _first_value(form_data, "dataset")
    language = resolve_request_language(request, _first_value(form_data, "lang"))
    export_service.delete_all_completed()

    return redirect(MONITOR_EXPORTS_PATH, language=language, dataset=dataset)


@router.get(MONITOR_EXPORTS_PATH, response_class=HTMLResponse)
def get_export_monitor_page(
    request: Request,
    dataset: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
    language: str = Depends(get_language),
):
    settings = request.app.state.settings
    webui = settings.webui
    export_service, err = try_get_export_service(request, language)
    if err:
        return err

    data = build_export_page_data(
        export_service,
        dataset=dataset,
        job_id=job_id,
        limit=webui.export_jobs_page_limit,
    )

    return HTMLResponse(
        render_export_jobs_page(data, webui_config=webui, language=language)
    )
