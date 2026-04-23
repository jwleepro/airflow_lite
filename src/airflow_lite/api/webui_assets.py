"""Assets page renderer."""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_ASSETS_PATH, MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE


def render_assets_page(*, language: str = DEFAULT_LANGUAGE) -> str:
    chrome = PageChrome(
        title=t(language, "webui.assets.title"),
        subtitle=t(language, "webui.assets.hint"),
        active_path=MONITOR_ASSETS_PATH,
        page_tag=t(language, "webui.layout.page_tag.analytics_workspace"),
        breadcrumbs=[
            (t(language, "webui.layout.nav.home"), MONITOR_PATH),
            (t(language, "webui.assets.title"), None),
        ],
    )
    return render_page("assets.html", chrome=chrome, language=language)
