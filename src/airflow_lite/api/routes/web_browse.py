from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from airflow_lite.api.dependencies import get_language
from airflow_lite.api.paths import (
    MONITOR_BROWSE_AUDIT_LOGS_PATH,
    MONITOR_BROWSE_BACKFILLS_PATH,
    MONITOR_BROWSE_DAG_RUNS_PATH,
    MONITOR_BROWSE_JOBS_PATH,
    MONITOR_BROWSE_TASK_INSTANCES_PATH,
)
from airflow_lite.api.webui_browse import (
    BrowseAuditLogsContext,
    BrowseBackfillsContext,
    BrowseDagRunsContext,
    BrowseJobsContext,
    BrowseTaskInstancesContext,
    render_browse_page,
)

router = APIRouter(include_in_schema=False)


@router.get(MONITOR_BROWSE_BACKFILLS_PATH, response_class=HTMLResponse)
def get_browse_backfills_page(language: str = Depends(get_language)):
    ctx = BrowseBackfillsContext()
    return HTMLResponse(
        render_browse_page(
            "browse/browse_backfills.html",
            title_key="webui.browse.backfills.title",
            subtitle_key="webui.browse.backfills.subtitle",
            active_path=MONITOR_BROWSE_BACKFILLS_PATH,
            language=language,
            **asdict(ctx),
        )
    )


@router.get(MONITOR_BROWSE_JOBS_PATH, response_class=HTMLResponse)
def get_browse_jobs_page(language: str = Depends(get_language)):
    ctx = BrowseJobsContext()
    return HTMLResponse(
        render_browse_page(
            "browse/browse_jobs.html",
            title_key="webui.browse.jobs.title",
            subtitle_key="webui.browse.jobs.subtitle",
            active_path=MONITOR_BROWSE_JOBS_PATH,
            language=language,
            **asdict(ctx),
        )
    )


@router.get(MONITOR_BROWSE_AUDIT_LOGS_PATH, response_class=HTMLResponse)
def get_browse_audit_logs_page(language: str = Depends(get_language)):
    ctx = BrowseAuditLogsContext()
    return HTMLResponse(
        render_browse_page(
            "browse/browse_audit_logs.html",
            title_key="webui.browse.audit_logs.title",
            subtitle_key="webui.browse.audit_logs.subtitle",
            active_path=MONITOR_BROWSE_AUDIT_LOGS_PATH,
            language=language,
            **asdict(ctx),
        )
    )


@router.get(MONITOR_BROWSE_TASK_INSTANCES_PATH, response_class=HTMLResponse)
def get_browse_task_instances_page(language: str = Depends(get_language)):
    ctx = BrowseTaskInstancesContext()
    return HTMLResponse(
        render_browse_page(
            "browse/browse_task_instances.html",
            title_key="webui.browse.task_instances.title",
            subtitle_key="webui.browse.task_instances.subtitle",
            active_path=MONITOR_BROWSE_TASK_INSTANCES_PATH,
            language=language,
            **asdict(ctx),
        )
    )


@router.get(MONITOR_BROWSE_DAG_RUNS_PATH, response_class=HTMLResponse)
def get_browse_dag_runs_page(language: str = Depends(get_language)):
    ctx = BrowseDagRunsContext()
    return HTMLResponse(
        render_browse_page(
            "browse/browse_dag_runs.html",
            title_key="webui.browse.dag_runs.title",
            subtitle_key="webui.browse.dag_runs.subtitle",
            active_path=MONITOR_BROWSE_DAG_RUNS_PATH,
            language=language,
            **asdict(ctx),
        )
    )
