"""Browse page renderers with UI-complete placeholder data."""

from __future__ import annotations

from typing import Iterable

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE


def _normalize_status(value: str) -> str:
    lowered = (value or "").strip().lower()
    return "" if lowered in {"", "all"} else lowered


def _matches_search(row: dict, query: str, fields: Iterable[str]) -> bool:
    if not query:
        return True
    needle = query.strip().lower()
    if not needle:
        return True
    for field in fields:
        value = row.get(field)
        if value is None:
            continue
        if needle in str(value).lower():
            return True
    return False


def _filter_rows(
    rows: list,
    *,
    search_query: str = "",
    search_fields: Iterable[str] = (),
    status_value: str = "",
    status_field: str = "status",
    dag_value: str = "",
    dag_field: str = "dag_id",
    user_value: str = "",
    user_field: str = "user",
    type_value: str = "",
    type_field: str = "job_type",
    action_value: str = "",
    action_field: str = "action",
) -> list:
    status_filter = _normalize_status(status_value)
    filtered = []
    for row in rows:
        if not _matches_search(row, search_query, search_fields):
            continue
        if status_filter and (row.get(status_field) or "").lower() != status_filter:
            continue
        if dag_value and row.get(dag_field) != dag_value:
            continue
        if user_value and row.get(user_field) != user_value:
            continue
        if type_value and row.get(type_field) != type_value:
            continue
        if action_value and (row.get(action_field) or "").lower() != action_value.lower():
            continue
        filtered.append(row)
    return filtered


def _resolve_total(total_count: int | None, rows: list) -> int:
    return len(rows) if total_count is None else total_count

_PLACEHOLDER_BACKFILLS = [
    {
        "dag_id": "etl_daily_pipeline",
        "run_id": "backfill__2026-04-22T00:00",
        "status": "success",
        "start_date": "2026-04-20",
        "end_date": "2026-04-22",
        "triggered_at": "2h ago",
    },
    {
        "dag_id": "dbt_transform",
        "run_id": "backfill__2026-04-19T00:00",
        "status": "running",
        "start_date": "2026-04-19",
        "end_date": "2026-04-20",
        "triggered_at": "38m ago",
    },
]

_PLACEHOLDER_JOBS = [
    {"job_type": "SchedulerJob", "hostname": "scheduler-0", "start_date": "Today 05:58", "end_date": "-", "last_heartbeat_date": "2s ago", "duration": "-", "active": True},
    {"job_type": "TriggererJob", "hostname": "triggerer-0", "start_date": "Today 05:58", "end_date": "-", "last_heartbeat_date": "4s ago", "duration": "-", "active": True},
    {"job_type": "DagProcessorJob", "hostname": "processor-0", "start_date": "Today 05:59", "end_date": "-", "last_heartbeat_date": "1s ago", "duration": "-", "active": True},
]

_PLACEHOLDER_AUDIT_LOGS = [
    {"timestamp": "2026-04-24 06:10:12", "user": "admin", "action": "trigger", "resource": "etl_daily_pipeline", "details": "Manual DAG trigger"},
    {"timestamp": "2026-04-24 05:44:09", "user": "data_team", "action": "update", "resource": "variable:max_retries", "details": "Changed value from 2 to 3"},
]

_PLACEHOLDER_TASK_INSTANCES = [
    {
        "dag_id": "etl_daily_pipeline",
        "task_id": "extract_source_a",
        "run_id": "scheduled__2026-04-24T06:00",
        "status": "success",
        "try_number": 1,
        "max_tries": 3,
        "start_date": "Today 06:04",
        "duration": "4s",
    },
    {
        "dag_id": "etl_daily_pipeline",
        "task_id": "data_quality_gate",
        "run_id": "scheduled__2026-04-24T06:00",
        "status": "running",
        "try_number": 1,
        "max_tries": 3,
        "start_date": "Today 06:08",
        "duration": "2m 14s",
    },
]

_PLACEHOLDER_DAG_RUNS = [
    {
        "dag_id": "etl_daily_pipeline",
        "run_id": "scheduled__2026-04-24T06:00",
        "status": "success",
        "start_time": "Today 06:00",
        "duration": "4m 32s",
        "trigger_type": "scheduled",
    },
    {
        "dag_id": "ml_feature_store",
        "run_id": "scheduled__2026-04-24T05:00",
        "status": "running",
        "start_time": "Today 05:00",
        "duration": "1h 12m",
        "trigger_type": "scheduled",
    },
]


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
    total_count: int | None = None,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    source_rows = backfills if backfills is not None else _PLACEHOLDER_BACKFILLS
    dag_options = dag_ids if dag_ids is not None else sorted({row["dag_id"] for row in source_rows})
    filtered_rows = _filter_rows(
        source_rows,
        search_query=search_query,
        search_fields=("dag_id", "run_id", "status"),
        status_value=selected_status,
        dag_value=selected_dag,
    )
    chrome = _make_chrome(language, "webui.browse.backfills.title", "webui.browse.backfills.subtitle", active_path)
    return render_page(
        "browse/browse_backfills.html",
        chrome=chrome,
        language=language,
        backfills=filtered_rows,
        total_count=_resolve_total(total_count, filtered_rows),
        search_query=search_query,
        selected_status=selected_status,
        dag_ids=dag_options,
        selected_dag=selected_dag,
    )


def render_browse_jobs_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    jobs: list | None = None,
    total_count: int | None = None,
    active_count: int | None = None,
    search_query: str = "",
    selected_type: str = "",
) -> str:
    source_rows = jobs if jobs is not None else _PLACEHOLDER_JOBS
    filtered_rows = _filter_rows(
        source_rows,
        search_query=search_query,
        search_fields=("job_type", "hostname"),
        type_value=selected_type,
    )
    chrome = _make_chrome(language, "webui.browse.jobs.title", "webui.browse.jobs.subtitle", active_path)
    resolved_active = (
        active_count
        if active_count is not None
        else sum(1 for row in filtered_rows if row.get("active"))
    )
    return render_page(
        "browse/browse_jobs.html",
        chrome=chrome,
        language=language,
        jobs=filtered_rows,
        total_count=_resolve_total(total_count, filtered_rows),
        active_count=resolved_active,
        search_query=search_query,
        selected_type=selected_type,
    )


def render_browse_audit_logs_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    audit_logs: list | None = None,
    total_count: int | None = None,
    search_query: str = "",
    selected_action: str = "",
    selected_user: str = "",
    users: list[str] | None = None,
) -> str:
    source_rows = audit_logs if audit_logs is not None else _PLACEHOLDER_AUDIT_LOGS
    user_options = users if users is not None else sorted({row["user"] for row in source_rows})
    filtered_rows = _filter_rows(
        source_rows,
        search_query=search_query,
        search_fields=("user", "action", "resource", "details"),
        action_value=selected_action,
        user_value=selected_user,
    )
    chrome = _make_chrome(language, "webui.browse.audit_logs.title", "webui.browse.audit_logs.subtitle", active_path)
    return render_page(
        "browse/browse_audit_logs.html",
        chrome=chrome,
        language=language,
        audit_logs=filtered_rows,
        total_count=_resolve_total(total_count, filtered_rows),
        search_query=search_query,
        selected_action=selected_action,
        selected_user=selected_user,
        users=user_options,
    )


def render_browse_task_instances_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    task_instances: list | None = None,
    total_count: int | None = None,
    running_count: int | None = None,
    failed_count: int | None = None,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    source_rows = task_instances if task_instances is not None else _PLACEHOLDER_TASK_INSTANCES
    dag_options = dag_ids if dag_ids is not None else sorted({row["dag_id"] for row in source_rows})
    filtered_rows = _filter_rows(
        source_rows,
        search_query=search_query,
        search_fields=("dag_id", "task_id", "run_id", "status"),
        status_value=selected_status,
        dag_value=selected_dag,
    )
    chrome = _make_chrome(language, "webui.browse.task_instances.title", "webui.browse.task_instances.subtitle", active_path)
    resolved_running = (
        running_count
        if running_count is not None
        else sum(1 for row in filtered_rows if row.get("status") == "running")
    )
    resolved_failed = (
        failed_count
        if failed_count is not None
        else sum(1 for row in filtered_rows if row.get("status") == "failed")
    )
    return render_page(
        "browse/browse_task_instances.html",
        chrome=chrome,
        language=language,
        task_instances=filtered_rows,
        total_count=_resolve_total(total_count, filtered_rows),
        running_count=resolved_running,
        failed_count=resolved_failed,
        search_query=search_query,
        selected_status=selected_status,
        dag_ids=dag_options,
        selected_dag=selected_dag,
    )


def render_browse_dag_runs_page(
    *,
    language: str = DEFAULT_LANGUAGE,
    active_path: str,
    dag_runs: list | None = None,
    total_count: int | None = None,
    running_count: int | None = None,
    failed_count: int | None = None,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    source_rows = dag_runs if dag_runs is not None else _PLACEHOLDER_DAG_RUNS
    dag_options = dag_ids if dag_ids is not None else sorted({row["dag_id"] for row in source_rows})
    filtered_rows = _filter_rows(
        source_rows,
        search_query=search_query,
        search_fields=("dag_id", "run_id", "status", "trigger_type"),
        status_value=selected_status,
        dag_value=selected_dag,
    )
    chrome = _make_chrome(language, "webui.browse.dag_runs.title", "webui.browse.dag_runs.subtitle", active_path)
    resolved_running = (
        running_count
        if running_count is not None
        else sum(1 for row in filtered_rows if row.get("status") == "running")
    )
    resolved_failed = (
        failed_count
        if failed_count is not None
        else sum(1 for row in filtered_rows if row.get("status") == "failed")
    )
    return render_page(
        "browse/browse_dag_runs.html",
        chrome=chrome,
        language=language,
        dag_runs=filtered_rows,
        total_count=_resolve_total(total_count, filtered_rows),
        running_count=resolved_running,
        failed_count=resolved_failed,
        search_query=search_query,
        selected_status=selected_status,
        dag_ids=dag_options,
        selected_dag=selected_dag,
    )
