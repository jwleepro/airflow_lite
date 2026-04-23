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
    render_browse_audit_logs_page,
    render_browse_backfills_page,
    render_browse_dag_runs_page,
    render_browse_jobs_page,
    render_browse_task_instances_page,
)

router = APIRouter(include_in_schema=False)


@router.get(MONITOR_BROWSE_BACKFILLS_PATH, response_class=HTMLResponse)
def get_browse_backfills_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_browse_backfills_page(
            active_path=MONITOR_BROWSE_BACKFILLS_PATH,
            language=language,
        )
    )


@router.get(MONITOR_BROWSE_JOBS_PATH, response_class=HTMLResponse)
def get_browse_jobs_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_browse_jobs_page(
            active_path=MONITOR_BROWSE_JOBS_PATH,
            language=language,
        )
    )


@router.get(MONITOR_BROWSE_AUDIT_LOGS_PATH, response_class=HTMLResponse)
def get_browse_audit_logs_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_browse_audit_logs_page(
            active_path=MONITOR_BROWSE_AUDIT_LOGS_PATH,
            language=language,
        )
    )


@router.get(MONITOR_BROWSE_TASK_INSTANCES_PATH, response_class=HTMLResponse)
def get_browse_task_instances_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_browse_task_instances_page(
            active_path=MONITOR_BROWSE_TASK_INSTANCES_PATH,
            language=language,
        )
    )


@router.get(MONITOR_BROWSE_DAG_RUNS_PATH, response_class=HTMLResponse)
def get_browse_dag_runs_page(language: str = Depends(get_language)):
    return HTMLResponse(
        render_browse_dag_runs_page(
            active_path=MONITOR_BROWSE_DAG_RUNS_PATH,
            language=language,
        )
    )
