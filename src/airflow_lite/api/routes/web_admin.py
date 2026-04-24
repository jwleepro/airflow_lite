from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from airflow_lite.api.dependencies import get_language
from airflow_lite.api.paths import (
    MONITOR_ADMIN_CONNECTIONS_PATH,
    MONITOR_ADMIN_CONFIG_PATH,
    MONITOR_ADMIN_PATH,
    MONITOR_ADMIN_PLUGINS_PATH,
    MONITOR_ADMIN_POOLS_PATH,
    MONITOR_ADMIN_PROVIDERS_PATH,
    MONITOR_ADMIN_VARIABLES_PATH,
    MONITOR_ADMIN_XCOMS_PATH,
)
from airflow_lite.api.presenters import admin_forms, admin_page
from airflow_lite.api.routes._web_common import read_form_data, redirect
from airflow_lite.api.viewmodels import AdminPageViewData
from airflow_lite.api.webui_admin import (
    render_admin_config_page,
    render_admin_connections_page,
    render_admin_page,
    render_admin_plugins_page,
    render_admin_pools_page,
    render_admin_providers_page,
    render_admin_variables_page,
    render_admin_xcoms_page,
)

router = APIRouter(include_in_schema=False)


def _view_data(request: Request):
    admin_repo = request.app.state.admin_repo
    if admin_repo is None:
        return AdminPageViewData()
    return admin_page.build_admin_view_data(admin_repo)


@router.get(MONITOR_ADMIN_PATH, response_class=HTMLResponse)
def get_admin_page(request: Request, language: str = Depends(get_language)):
    return HTMLResponse(render_admin_page(_view_data(request), language=language, error=request.query_params.get("error")))


@router.get(MONITOR_ADMIN_CONNECTIONS_PATH, response_class=HTMLResponse)
def get_admin_connections_page(request: Request, language: str = Depends(get_language)):
    return HTMLResponse(render_admin_connections_page(_view_data(request), language=language, error=request.query_params.get("error")))


@router.get(MONITOR_ADMIN_VARIABLES_PATH, response_class=HTMLResponse)
def get_admin_variables_page(request: Request, language: str = Depends(get_language)):
    return HTMLResponse(render_admin_variables_page(_view_data(request), language=language, error=request.query_params.get("error")))


@router.get(MONITOR_ADMIN_POOLS_PATH, response_class=HTMLResponse)
def get_admin_pools_page(request: Request, language: str = Depends(get_language)):
    return HTMLResponse(render_admin_pools_page(_view_data(request), language=language, error=request.query_params.get("error")))


@router.get(MONITOR_ADMIN_PROVIDERS_PATH, response_class=HTMLResponse)
def get_admin_providers_page(language: str = Depends(get_language)):
    return HTMLResponse(render_admin_providers_page(language=language))


@router.get(MONITOR_ADMIN_PLUGINS_PATH, response_class=HTMLResponse)
def get_admin_plugins_page(language: str = Depends(get_language)):
    return HTMLResponse(render_admin_plugins_page(language=language))


@router.get(MONITOR_ADMIN_CONFIG_PATH, response_class=HTMLResponse)
def get_admin_config_page(language: str = Depends(get_language)):
    return HTMLResponse(render_admin_config_page(language=language))


@router.get(MONITOR_ADMIN_XCOMS_PATH, response_class=HTMLResponse)
def get_admin_xcoms_page(language: str = Depends(get_language)):
    return HTMLResponse(render_admin_xcoms_page(language=language))


async def _handle_admin_form(request: Request, handler, language: str, redirect_path: str) -> RedirectResponse:
    admin_repo = request.app.state.admin_repo
    form_data = await read_form_data(request)
    try:
        handler(admin_repo, form_data)
    except ValueError as exc:
        return redirect(redirect_path, language=language, error=str(exc))
    return redirect(redirect_path, language=language)


@router.post(f"{MONITOR_ADMIN_PATH}/connections")
async def create_connection_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_connection, language, MONITOR_ADMIN_CONNECTIONS_PATH)


@router.post(f"{MONITOR_ADMIN_PATH}/connections/delete")
async def delete_connection_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_connection, language, MONITOR_ADMIN_CONNECTIONS_PATH)


@router.post(f"{MONITOR_ADMIN_PATH}/variables")
async def create_variable_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_variable, language, MONITOR_ADMIN_VARIABLES_PATH)


@router.post(f"{MONITOR_ADMIN_PATH}/variables/delete")
async def delete_variable_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_variable, language, MONITOR_ADMIN_VARIABLES_PATH)


@router.post(f"{MONITOR_ADMIN_PATH}/pools")
async def create_pool_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_pool, language, MONITOR_ADMIN_POOLS_PATH)


@router.post(f"{MONITOR_ADMIN_PATH}/pools/delete")
async def delete_pool_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_pool, language, MONITOR_ADMIN_POOLS_PATH)
