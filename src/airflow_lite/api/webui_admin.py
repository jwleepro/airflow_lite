"""Admin page renderer.

Delegates HTML production to `templates/admin.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_ADMIN_PATH, MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.viewmodels import AdminPageViewData
from airflow_lite.api.webui_helpers import t


def render_admin_page(
    view_data: AdminPageViewData, *, language: str, error: str | None = None
) -> str:
    chrome = PageChrome(
        title=t(language, "webui.layout.nav.admin"),
        subtitle=t(language, "webui.admin.subtitle"),
        active_path=MONITOR_ADMIN_PATH,
        page_tag=t(language, "webui.layout.page_tag.service_status"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, "webui.layout.nav.admin"), None),
        ],
    )
    return render_page(
        "admin.html",
        chrome=chrome,
        language=language,
        connections=view_data.connections,
        variables=view_data.variables,
        pools=view_data.pools,
        error=error,
    )
