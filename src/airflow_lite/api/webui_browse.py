"""Browse page renderers with UI-complete placeholder data."""

from __future__ import annotations

from airflow_lite.api.paths import MONITOR_PATH
from airflow_lite.api.template_env import PageChrome, render_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.i18n import DEFAULT_LANGUAGE

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
    total_count: int = 0,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    rows = backfills if backfills is not None else _PLACEHOLDER_BACKFILLS
    chrome = _make_chrome(language, "webui.browse.backfills.title", "webui.browse.backfills.subtitle", active_path)
    dag_options = dag_ids if dag_ids is not None else sorted({row["dag_id"] for row in rows})
    return render_page(
        "browse/browse_backfills.html",
        chrome=chrome,
        language=language,
        backfills=rows,
        total_count=total_count or len(rows),
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
    total_count: int = 0,
    active_count: int = 0,
    search_query: str = "",
    selected_type: str = "",
) -> str:
    rows = jobs if jobs is not None else _PLACEHOLDER_JOBS
    chrome = _make_chrome(language, "webui.browse.jobs.title", "webui.browse.jobs.subtitle", active_path)
    return render_page(
        "browse/browse_jobs.html",
        chrome=chrome,
        language=language,
        jobs=rows,
        total_count=total_count or len(rows),
        active_count=active_count or sum(1 for row in rows if row.get("active")),
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
    rows = audit_logs if audit_logs is not None else _PLACEHOLDER_AUDIT_LOGS
    chrome = _make_chrome(language, "webui.browse.audit_logs.title", "webui.browse.audit_logs.subtitle", active_path)
    user_options = users if users is not None else sorted({row["user"] for row in rows})
    return render_page(
        "browse/browse_audit_logs.html",
        chrome=chrome,
        language=language,
        audit_logs=rows,
        total_count=total_count or len(rows),
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
    total_count: int = 0,
    running_count: int = 0,
    failed_count: int = 0,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    rows = task_instances if task_instances is not None else _PLACEHOLDER_TASK_INSTANCES
    chrome = _make_chrome(language, "webui.browse.task_instances.title", "webui.browse.task_instances.subtitle", active_path)
    dag_options = dag_ids if dag_ids is not None else sorted({row["dag_id"] for row in rows})
    return render_page(
        "browse/browse_task_instances.html",
        chrome=chrome,
        language=language,
        task_instances=rows,
        total_count=total_count or len(rows),
        running_count=running_count or sum(1 for row in rows if row.get("status") == "running"),
        failed_count=failed_count or sum(1 for row in rows if row.get("status") == "failed"),
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
    total_count: int = 0,
    running_count: int = 0,
    failed_count: int = 0,
    search_query: str = "",
    selected_status: str = "",
    dag_ids: list[str] | None = None,
    selected_dag: str = "",
) -> str:
    rows = dag_runs if dag_runs is not None else _PLACEHOLDER_DAG_RUNS
    chrome = _make_chrome(language, "webui.browse.dag_runs.title", "webui.browse.dag_runs.subtitle", active_path)
    dag_options = dag_ids if dag_ids is not None else sorted({row["dag_id"] for row in rows})
    return render_page(
        "browse/browse_dag_runs.html",
        chrome=chrome,
        language=language,
        dag_runs=rows,
        total_count=total_count or len(rows),
        running_count=running_count or sum(1 for row in rows if row.get("status") == "running"),
        failed_count=failed_count or sum(1 for row in rows if row.get("status") == "failed"),
        search_query=search_query,
        selected_status=selected_status,
        dag_ids=dag_options,
        selected_dag=selected_dag,
    )
