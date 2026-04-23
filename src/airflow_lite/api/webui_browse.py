"""Browse placeholder page renderer."""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE


def render_browse_page(
    template_name: str,
    *,
    title_key: str,
    subtitle_key: str,
    active_path: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
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
    return render_page(template_name, chrome=chrome, language=language)
