"""Jinja2 template environment for the WebUI.

Renderers in `airflow_lite.api.webui_*` delegate HTML production to
templates under `airflow_lite/api/templates/`. Helper functions are
exposed as Jinja globals so templates can format / translate values
without importing Python helpers directly.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from airflow_lite.api.paths import (
    ANALYTICS_EXPORTS_PATH,
    ANALYTICS_FILTERS_PATH,
    MONITOR_ADMIN_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_EXPORT_DELETE_COMPLETED_PATH,
    MONITOR_EXPORT_DELETE_JOB_PATH,
    MONITOR_PATH,
    PIPELINES_PATH,
    dashboard_definition_path,
    monitor_pipeline_run_detail_path,
    pipeline_run_detail_path,
    pipeline_runs_path,
)
from airflow_lite.api.webui_helpers import (
    ICON_ADMIN,
    ICON_ANALYTICS,
    ICON_API,
    ICON_DOCS,
    ICON_EXPORTS,
    ICON_PIPELINES,
    cfg,
    fmt,
    fmt_duration,
    status_tone,
    t,
    with_language_query,
)
from airflow_lite.i18n import DEFAULT_LANGUAGE


_TEMPLATES_DIR = Path(__file__).parent / "templates"


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
        status_tone=status_tone,
        cfg=cfg,
        # Raw SVG icons — must be output with |safe
        ICON_PIPELINES=Markup(ICON_PIPELINES),
        ICON_ANALYTICS=Markup(ICON_ANALYTICS),
        ICON_EXPORTS=Markup(ICON_EXPORTS),
        ICON_ADMIN=Markup(ICON_ADMIN),
        ICON_DOCS=Markup(ICON_DOCS),
        ICON_API=Markup(ICON_API),
        # Paths
        MONITOR_PATH=MONITOR_PATH,
        MONITOR_ADMIN_PATH=MONITOR_ADMIN_PATH,
        MONITOR_ANALYTICS_PATH=MONITOR_ANALYTICS_PATH,
        MONITOR_EXPORTS_PATH=MONITOR_EXPORTS_PATH,
        MONITOR_EXPORT_DELETE_COMPLETED_PATH=MONITOR_EXPORT_DELETE_COMPLETED_PATH,
        MONITOR_EXPORT_DELETE_JOB_PATH=MONITOR_EXPORT_DELETE_JOB_PATH,
        ANALYTICS_EXPORTS_PATH=ANALYTICS_EXPORTS_PATH,
        ANALYTICS_FILTERS_PATH=ANALYTICS_FILTERS_PATH,
        PIPELINES_PATH=PIPELINES_PATH,
        dashboard_definition_path=dashboard_definition_path,
        monitor_pipeline_run_detail_path=monitor_pipeline_run_detail_path,
        pipeline_run_detail_path=pipeline_run_detail_path,
        pipeline_runs_path=pipeline_runs_path,
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
