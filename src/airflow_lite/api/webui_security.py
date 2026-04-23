"""Security page renderers with real page context."""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE


def _make_chrome(
    language: str,
    title_key: str,
    subtitle_key: str,
    active_path: str,
) -> PageChrome:
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
    chrome = _make_chrome(
        language,
        "webui.security.users.title",
        "webui.security.users.subtitle",
        active_path,
    )
    return render_page(
        "security/security_users.html",
        chrome=chrome,
        language=language,
        users=users or [],
        total_count=total_count,
        active_count=active_count,
        search_query=search_query,
    )


def render_security_roles_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    roles: list | None = None,
    total_count: int = 0,
) -> str:
    chrome = _make_chrome(
        language,
        "webui.security.roles.title",
        "webui.security.roles.subtitle",
        active_path,
    )
    return render_page(
        "security/security_roles.html",
        chrome=chrome,
        language=language,
        roles=roles or [],
        total_count=total_count,
    )


def render_security_permissions_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    permissions: list | None = None,
    total_count: int = 0,
) -> str:
    chrome = _make_chrome(
        language,
        "webui.security.permissions.title",
        "webui.security.permissions.subtitle",
        active_path,
    )
    return render_page(
        "security/security_permissions.html",
        chrome=chrome,
        language=language,
        permissions=permissions or [],
        total_count=total_count,
    )
