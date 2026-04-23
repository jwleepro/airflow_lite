from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from airflow_lite.api.dependencies import get_language
from airflow_lite.api.paths import (
    MONITOR_SECURITY_PERMISSIONS_PATH,
    MONITOR_SECURITY_ROLES_PATH,
    MONITOR_SECURITY_USERS_PATH,
)
from airflow_lite.api.webui_security import (
    SecurityPermissionsContext,
    SecurityRolesContext,
    SecurityUsersContext,
    render_security_page,
)

router = APIRouter(include_in_schema=False)


@router.get(MONITOR_SECURITY_USERS_PATH, response_class=HTMLResponse)
def get_security_users_page(language: str = Depends(get_language)):
    ctx = SecurityUsersContext()
    return HTMLResponse(
        render_security_page(
            "security/security_users.html",
            title_key="webui.security.users.title",
            subtitle_key="webui.security.users.subtitle",
            active_path=MONITOR_SECURITY_USERS_PATH,
            language=language,
            **asdict(ctx),
        )
    )


@router.get(MONITOR_SECURITY_ROLES_PATH, response_class=HTMLResponse)
def get_security_roles_page(language: str = Depends(get_language)):
    ctx = SecurityRolesContext()
    return HTMLResponse(
        render_security_page(
            "security/security_roles.html",
            title_key="webui.security.roles.title",
            subtitle_key="webui.security.roles.subtitle",
            active_path=MONITOR_SECURITY_ROLES_PATH,
            language=language,
            **asdict(ctx),
        )
    )


@router.get(MONITOR_SECURITY_PERMISSIONS_PATH, response_class=HTMLResponse)
def get_security_permissions_page(language: str = Depends(get_language)):
    ctx = SecurityPermissionsContext()
    return HTMLResponse(
        render_security_page(
            "security/security_permissions.html",
            title_key="webui.security.permissions.title",
            subtitle_key="webui.security.permissions.subtitle",
            active_path=MONITOR_SECURITY_PERMISSIONS_PATH,
            language=language,
            **asdict(ctx),
        )
    )
