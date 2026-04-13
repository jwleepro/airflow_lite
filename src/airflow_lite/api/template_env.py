"""Jinja2 template environment for the WebUI.

Renderers in `airflow_lite.api.webui_*` delegate HTML production to
templates under `airflow_lite/api/templates/`. Helper functions are
exposed as Jinja globals so templates can format / translate values
without importing Python helpers directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from airflow_lite.api.paths import (
    MONITOR_ADMIN_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_EXPORT_DELETE_COMPLETED_PATH,
    MONITOR_EXPORT_DELETE_JOB_PATH,
    MONITOR_PATH,
    PIPELINES_PATH,
    monitor_pipeline_run_detail_path,
)
from airflow_lite.api.webui_helpers import (
    ICON_ADMIN,
    ICON_ANALYTICS,
    ICON_DOCS,
    ICON_PIPELINES,
    fmt,
    fmt_duration,
    t,
    with_language_query,
)
from airflow_lite.api.webui_status import tone_of
from airflow_lite.i18n import DEFAULT_LANGUAGE


_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class PageChrome:
    """페이지 공통 "크롬"(레이아웃 바깥 틀) 파라미터.

    모든 WebUI 페이지 렌더러가 base.html로 전달하는 공통 인자 묶음.
    한 곳에 모아 렌더러별 반복을 제거한다.
    """

    title: str
    subtitle: str
    active_path: str
    page_tag: str | None = None
    auto_refresh_seconds: int | None = None
    hero_links: list[tuple[str, str]] = field(default_factory=list)


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html",), default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals.update(
        fmt=fmt,
        fmt_duration=fmt_duration,
        tone_of=tone_of,
        # Raw SVG icons — must be output with |safe
        ICON_PIPELINES=Markup(ICON_PIPELINES),
        ICON_ANALYTICS=Markup(ICON_ANALYTICS),
        ICON_ADMIN=Markup(ICON_ADMIN),
        ICON_DOCS=Markup(ICON_DOCS),
        # Paths
        MONITOR_PATH=MONITOR_PATH,
        MONITOR_ADMIN_PATH=MONITOR_ADMIN_PATH,
        MONITOR_ANALYTICS_PATH=MONITOR_ANALYTICS_PATH,
        MONITOR_EXPORTS_PATH=MONITOR_EXPORTS_PATH,
        MONITOR_EXPORT_DELETE_COMPLETED_PATH=MONITOR_EXPORT_DELETE_COMPLETED_PATH,
        MONITOR_EXPORT_DELETE_JOB_PATH=MONITOR_EXPORT_DELETE_JOB_PATH,
        PIPELINES_PATH=PIPELINES_PATH,
        monitor_pipeline_run_detail_path=monitor_pipeline_run_detail_path,
    )
    return env


_ENV = _make_env()


def render(
    template_name: str,
    *,
    language: str = DEFAULT_LANGUAGE,
    **context,
) -> str:
    """Render a template with language-bound helpers in context."""
    def _t(key: str, **kwargs) -> str:
        return t(language, key, **kwargs)

    def _lang_url(href: str) -> str:
        return with_language_query(href, language)

    context.setdefault("language", language)
    context.setdefault("t", _t)
    context.setdefault("lang_url", _lang_url)
    return _ENV.get_template(template_name).render(**context)


def render_page(
    template_name: str,
    *,
    chrome: PageChrome,
    language: str = DEFAULT_LANGUAGE,
    **context,
) -> str:
    """`PageChrome`을 펼쳐 base.html 공통 컨텍스트와 함께 렌더."""
    return render(
        template_name,
        language=language,
        title=chrome.title,
        subtitle=chrome.subtitle,
        active_path=chrome.active_path,
        page_tag=chrome.page_tag,
        auto_refresh_seconds=chrome.auto_refresh_seconds,
        hero_links=chrome.hero_links,
        **context,
    )
