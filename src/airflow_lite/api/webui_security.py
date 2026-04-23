"""Security page renderers.

Each renderer receives a page-specific context and passes it through to the
template so templates can render real data (or an empty state) instead of
relying on static placeholder text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# Context dataclasses — stable presentation contracts for each Security page
# ---------------------------------------------------------------------------


@dataclass
class SecurityUsersContext:
    """Context for the Security > Users page."""

    users: list[Any] = field(default_factory=list)
    total_count: int = 0
    active_count: int = 0
    search_query: str = ""


@dataclass
class SecurityRolesContext:
    """Context for the Security > Roles page."""

    roles: list[Any] = field(default_factory=list)
    total_count: int = 0


@dataclass
class SecurityPermissionsContext:
    """Context for the Security > Permissions page."""

    permissions: list[Any] = field(default_factory=list)
    total_count: int = 0


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def render_security_page(
    template_name: str,
    *,
    title_key: str,
    subtitle_key: str,
    active_path: str,
    language: str = DEFAULT_LANGUAGE,
    **context: Any,
) -> str:
    """Render a Security page with the given page-specific context.

    Extra keyword arguments are forwarded verbatim to the template so each
    Security page can receive its own data (users, roles, permissions, ...).
    """
    chrome = PageChrome(
        title=t(language, title_key),
        subtitle=t(language, subtitle_key),
        active_path=active_path,
        page_tag=t(language, "webui.layout.page_tag.analytics_workspace"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, title_key), None),
        ],
    )
    return render_page(template_name, chrome=chrome, language=language, **context)
