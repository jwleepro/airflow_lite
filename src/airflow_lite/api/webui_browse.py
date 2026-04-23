"""Browse page renderers with real page context."""

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


def render_browse_backfills_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    backfills: list | None = None,
    total_count: int = 0,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    chrome = _make_chrome(
        language,
        "webui.browse.backfills.title",
        "webui.browse.backfills.subtitle",
        active_path,
    )
    return render_page(
        "browse/browse_backfills.html",
        chrome=chrome,
        language=language,
        backfills=backfills or [],
        total_count=total_count,
        search_query=search_query,
        selected_status=selected_status,
        dag_ids=dag_ids or [],
        selected_dag=selected_dag,
    )


def render_browse_jobs_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    jobs: list | None = None,
    total_count: int = 0,
    active_count: int = 0,
    search_query: str = "",
    selected_type: str = "",
) -> str:
    chrome = _make_chrome(
        language,
        "webui.browse.jobs.title",
        "webui.browse.jobs.subtitle",
        active_path,
    )
    return render_page(
        "browse/browse_jobs.html",
        chrome=chrome,
        language=language,
        jobs=jobs or [],
        total_count=total_count,
        active_count=active_count,
        search_query=search_query,
        selected_type=selected_type,
    )


def render_browse_audit_logs_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    audit_logs: list | None = None,
    total_count: int = 0,
    search_query: str = "",
    selected_action: str = "",
    selected_user: str = "",
    users: list[str] | None = None,
) -> str:
    chrome = _make_chrome(
        language,
        "webui.browse.audit_logs.title",
        "webui.browse.audit_logs.subtitle",
        active_path,
    )
    return render_page(
        "browse/browse_audit_logs.html",
        chrome=chrome,
        language=language,
        audit_logs=audit_logs or [],
        total_count=total_count,
        search_query=search_query,
        selected_action=selected_action,
        selected_user=selected_user,
        users=users or [],
    )


def render_browse_task_instances_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    task_instances: list | None = None,
    total_count: int = 0,
    running_count: int = 0,
    failed_count: int = 0,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    chrome = _make_chrome(
        language,
        "webui.browse.task_instances.title",
        "webui.browse.task_instances.subtitle",
        active_path,
    )
    return render_page(
        "browse/browse_task_instances.html",
        chrome=chrome,
        language=language,
        task_instances=task_instances or [],
        total_count=total_count,
        running_count=running_count,
        failed_count=failed_count,
        search_query=search_query,
        selected_status=selected_status,
        dag_ids=dag_ids or [],
        selected_dag=selected_dag,
    )


def render_browse_dag_runs_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    dag_runs: list | None = None,
    total_count: int = 0,
    running_count: int = 0,
    failed_count: int = 0,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    chrome = _make_chrome(
        language,
        "webui.browse.dag_runs.title",
        "webui.browse.dag_runs.subtitle",
        active_path,
    )
    return render_page(
        "browse/browse_dag_runs.html",
        chrome=chrome,
        language=language,
        dag_runs=dag_runs or [],
        total_count=total_count,
        running_count=running_count,
        failed_count=failed_count,
        search_query=search_query,
        selected_status=selected_status,
        dag_ids=dag_ids or [],
        selected_dag=selected_dag,
    )
