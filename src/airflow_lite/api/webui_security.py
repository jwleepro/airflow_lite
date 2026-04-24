"""Security page renderers with UI-complete placeholder data."""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE

_PLACEHOLDER_USERS = [
    {"username": "admin", "email": "admin@company.com", "role": "Admin", "is_active": True, "last_login": "2 min ago"},
    {"username": "data_team", "email": "data@company.com", "role": "Op", "is_active": True, "last_login": "1h ago"},
    {"username": "ml_team", "email": "ml@company.com", "role": "Op, Viewer", "is_active": True, "last_login": "3h ago"},
    {"username": "readonly_user", "email": "viewer@company.com", "role": "Viewer", "is_active": False, "last_login": "5d ago"},
]

_PLACEHOLDER_ROLES = [
    {"name": "Admin", "description": "Full platform administration", "user_count": 1, "permission_count": 42},
    {"name": "Op", "description": "Trigger, monitor, retry, and inspect DAGs", "user_count": 2, "permission_count": 18},
    {"name": "Viewer", "description": "Read-only access to operational pages", "user_count": 4, "permission_count": 8},
]

_PLACEHOLDER_PERMISSIONS = [
    {"role": "Admin", "resource": "DAGs", "action": "can_edit"},
    {"role": "Admin", "resource": "Connections", "action": "can_delete"},
    {"role": "Op", "resource": "DAG Runs", "action": "can_trigger"},
    {"role": "Viewer", "resource": "Task Logs", "action": "can_read"},
]


def _make_chrome(language: str, title_key: str, subtitle_key: str, active_path: str) -> PageChrome:
    return PageChrome(
        title=t(language, title_key),
        subtitle=t(language, subtitle_key),
        active_path=active_path,
        page_tag=t(language, "webui.layout.page_tag.analytics_workspace"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, title_key), None),
        ],
    )


def render_security_users_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    users: list | None = None,
    total_count: int = 0,
    active_count: int = 0,
    search_query: str = "",
) -> str:
    rows = users if users is not None else _PLACEHOLDER_USERS
    chrome = _make_chrome(language, "webui.security.users.title", "webui.security.users.subtitle", active_path)
    return render_page(
        "security/security_users.html",
        chrome=chrome,
        language=language,
        users=rows,
        total_count=total_count or len(rows),
        active_count=active_count or sum(1 for row in rows if row.get("is_active")),
        search_query=search_query,
    )


def render_security_roles_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    roles: list | None = None,
    total_count: int = 0,
) -> str:
    rows = roles if roles is not None else _PLACEHOLDER_ROLES
    chrome = _make_chrome(language, "webui.security.roles.title", "webui.security.roles.subtitle", active_path)
    return render_page(
        "security/security_roles.html",
        chrome=chrome,
        language=language,
        roles=rows,
        total_count=total_count or len(rows),
    )


def render_security_permissions_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    permissions: list | None = None,
    total_count: int = 0,
) -> str:
    rows = permissions if permissions is not None else _PLACEHOLDER_PERMISSIONS
    chrome = _make_chrome(language, "webui.security.permissions.title", "webui.security.permissions.subtitle", active_path)
    return render_page(
        "security/security_permissions.html",
        chrome=chrome,
        language=language,
        permissions=rows,
        total_count=total_count or len(rows),
    )
