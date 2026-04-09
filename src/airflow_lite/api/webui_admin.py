"""Admin page renderer.

Delegates HTML production to `templates/admin.html`.
"""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_ADMIN_PATH
from airflow_lite.api.template_env import render
from airflow_lite.api.viewmodels import AdminPageViewData
from airflow_lite.api.webui_helpers import t


def render_admin_page(view_data: AdminPageViewData, *, language: str) -> str:
    return render(
        "admin.html",
        language=language,
        title=t(language, "webui.layout.nav.admin"),
        subtitle="Manage connections, variables, pools, and pipelines.",
        active_path=MONITOR_ADMIN_PATH,
        connections=view_data.connections,
        variables=view_data.variables,
        pools=view_data.pools,
        pipelines=view_data.pipelines,
        hero_links=[],
        page_tag=None,
        auto_refresh_seconds=None,
    )
