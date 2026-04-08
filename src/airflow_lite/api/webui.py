"""Backward-compatible web UI facade.

페이지별 렌더링 구현은 `webui_*` 모듈로 분리하고,
기존 import 경로(`airflow_lite.api.webui`)는 유지한다.
"""

from airflow_lite.api.webui_analytics import (
    render_analytics_dashboard_page,
    render_unavailable_page,
)
from airflow_lite.api.webui_exports import render_export_jobs_page
from airflow_lite.api.webui_monitor import render_monitor_page
from airflow_lite.api.webui_run_detail import render_run_detail_page

__all__ = [
    "render_analytics_dashboard_page",
    "render_export_jobs_page",
    "render_monitor_page",
    "render_run_detail_page",
    "render_unavailable_page",
]
