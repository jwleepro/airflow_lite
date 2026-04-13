API_PREFIX = "/api/v1"

MONITOR_PATH = "/monitor"
MONITOR_ANALYTICS_PATH = "/monitor/analytics"
MONITOR_EXPORTS_PATH = "/monitor/exports"
MONITOR_ADMIN_PATH = "/monitor/admin"
MONITOR_EXPORT_DELETE_JOB_PATH = "/monitor/exports/delete-job"
MONITOR_EXPORT_DELETE_COMPLETED_PATH = "/monitor/exports/delete-completed"

PIPELINES_PATH = f"{API_PREFIX}/pipelines"
ANALYTICS_SUMMARY_PATH = f"{API_PREFIX}/analytics/summary"
ANALYTICS_FILTERS_PATH = f"{API_PREFIX}/analytics/filters"
ANALYTICS_EXPORTS_PATH = f"{API_PREFIX}/analytics/exports"


def pipeline_runs_path(pipeline_name: str) -> str:
    return f"{PIPELINES_PATH}/{pipeline_name}/runs"


def pipeline_run_detail_path(pipeline_name: str, run_id: str) -> str:
    return f"{pipeline_runs_path(pipeline_name)}/{run_id}"


def monitor_pipeline_run_detail_path(pipeline_name: str, run_id: str) -> str:
    return f"{MONITOR_PATH}/pipelines/{pipeline_name}/runs/{run_id}"


def dashboard_definition_path(dashboard_id: str) -> str:
    return f"{API_PREFIX}/analytics/dashboards/{dashboard_id}"


def chart_query_path(chart_id: str) -> str:
    return f"{API_PREFIX}/analytics/charts/{chart_id}/query"


def detail_query_path(detail_key: str) -> str:
    return f"{API_PREFIX}/analytics/details/{detail_key}/query"


def export_job_path(job_id: str) -> str:
    return f"{ANALYTICS_EXPORTS_PATH}/{job_id}"


def export_download_path(job_id: str) -> str:
    return f"{export_job_path(job_id)}/download"
