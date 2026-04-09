"""Admin page renderer.

Delegates HTML production to `templates/admin.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_ADMIN_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.viewmodels import AdminPageViewData
from airflow_lite.api.webui_helpers import t


def render_admin_page(view_data: AdminPageViewData, *, language: str) -> str:
    chrome = PageChrome(
        title=t(language, "webui.layout.nav.admin"),
        subtitle="Manage connections, variables, pools, and pipelines.",
        active_path=MONITOR_ADMIN_PATH,
    )
    return render_page(
        "admin.html",
        chrome=chrome,
        language=language,
        connections=view_data.connections,
        variables=view_data.variables,
        pools=view_data.pools,
        pipelines=view_data.pipelines,
    )
