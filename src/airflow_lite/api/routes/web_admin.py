from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from airflow_lite.api.dependencies import get_admin_repo, get_language
from airflow_lite.api.paths import MONITOR_ADMIN_PATH
from airflow_lite.api.presenters import admin_forms, admin_page
from airflow_lite.api.routes._web_common import (
    read_form_data,
    redirect,
)
from airflow_lite.api.webui_admin import render_admin_page

router = APIRouter(include_in_schema=False)


@router.get(MONITOR_ADMIN_PATH, response_class=HTMLResponse)
def get_admin_page(request: Request, language: str = Depends(get_language)):
    admin_repo = get_admin_repo(request)
    view_data = admin_page.build_admin_view_data(admin_repo)
    error = request.query_params.get("error")
    return HTMLResponse(
        render_admin_page(view_data, language=language, error=error)
    )


async def _handle_admin_form(
    request: Request,
    handler,
    language: str,
) -> RedirectResponse:
    admin_repo = get_admin_repo(request)
    form_data = await read_form_data(request)
    try:
        handler(admin_repo, form_data)
    except ValueError as exc:
        return redirect(MONITOR_ADMIN_PATH, language=language, error=str(exc))
    return redirect(MONITOR_ADMIN_PATH, language=language)


@router.post(f"{MONITOR_ADMIN_PATH}/connections")
async def create_connection_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_connection, language)


@router.post(f"{MONITOR_ADMIN_PATH}/connections/delete")
async def delete_connection_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_connection, language)


@router.post(f"{MONITOR_ADMIN_PATH}/variables")
async def create_variable_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_variable, language)


@router.post(f"{MONITOR_ADMIN_PATH}/variables/delete")
async def delete_variable_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_variable, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pools")
async def create_pool_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_pool, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pools/delete")
async def delete_pool_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_pool, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pipelines")
async def create_pipeline_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_pipeline, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pipelines/edit")
async def edit_pipeline_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.update_pipeline, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pipelines/delete")
async def delete_pipeline_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_pipeline, language)
