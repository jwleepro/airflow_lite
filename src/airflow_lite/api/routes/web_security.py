from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from airflow_lite.api.dependencies import get_language
from airflow_lite.api.paths import (
    MONITOR_SECURITY_PERMISSIONS_PATH,
    MONITOR_SECURITY_ROLES_PATH,
    MONITOR_SECURITY_USERS_PATH,
)
from airflow_lite.api.webui_security import (
    render_security_permissions_page,
    render_security_roles_page,
    render_security_users_page,
)

router = APIRouter(include_in_schema=False)


@router.get(MONITOR_SECURITY_USERS_PATH, response_class=HTMLResponse)
def get_security_users_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_security_users_page(
            active_path=MONITOR_SECURITY_USERS_PATH,
            language=language,
        )
    )


@router.get(MONITOR_SECURITY_ROLES_PATH, response_class=HTMLResponse)
def get_security_roles_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_security_roles_page(
            active_path=MONITOR_SECURITY_ROLES_PATH,
            language=language,
        )
    )


@router.get(MONITOR_SECURITY_PERMISSIONS_PATH, response_class=HTMLResponse)
def get_security_permissions_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_security_permissions_page(
            active_path=MONITOR_SECURITY_PERMISSIONS_PATH,
            language=language,
        )
    )
