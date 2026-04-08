from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from airflow_lite.api.analytics_contracts import (
    ChartQueryRequest,
    DetailQueryRequest,
    ExportCreateRequest,
    ExportFormat,
    SummaryQueryRequest,
)
from airflow_lite.api.dependencies import get_export_service, get_query_service
from airflow_lite.api.routes.pipelines import _build_run_response_with_steps
from airflow_lite.api.webui import (
    render_analytics_dashboard_page,
    render_export_jobs_page,
    render_monitor_page,
    render_run_detail_page,
    render_unavailable_page,
)
from airflow_lite.export import AnalyticsExportJobNotFoundError
from airflow_lite.query import (
    AnalyticsDashboardNotFoundError,
    AnalyticsDatasetNotFoundError,
    AnalyticsQueryError,
)

router = APIRouter(include_in_schema=False)


def _calc_next_run(schedule_cron: str) -> str | None:
    """APScheduler CronTrigger를 사용해 다음 예정 실행 시각을 계산한다."""
    try:
        from datetime import datetime, timezone
        from apscheduler.triggers.cron import CronTrigger

        trigger = CronTrigger.from_crontab(schedule_cron)
        now = datetime.now(timezone.utc)
        next_time = trigger.get_next_fire_time(None, now)
        if next_time:
            local_dt = next_time.astimezone().replace(tzinfo=None)
            return local_dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return None


def _extract_selected_filters(source, filter_definitions: list[dict]) -> dict[str, list[str]]:
    getter = source.getlist if hasattr(source, "getlist") else lambda key: source.get(key, [])
    filters: dict[str, list[str]] = {}
    for filter_definition in filter_definitions:
        key = filter_definition["key"]
        values = [value for value in getter(key) if value]
        if values:
            filters[key] = values
    return filters


def _extract_detail_key(endpoint: str | None) -> str | None:
    if not endpoint:
        return None

    parts = endpoint.strip("/").split("/")
    try:
        detail_index = parts.index("details")
    except ValueError:
        return None
    if detail_index + 1 >= len(parts):
        return None
    return parts[detail_index + 1]


def _redirect_to_exports(job_id: str, dataset: str) -> RedirectResponse:
    query = urlencode({"job_id": job_id, "dataset": dataset})
    return RedirectResponse(url=f"/monitor/exports?{query}", status_code=303)


@router.get("/")
def redirect_root():
    return RedirectResponse(url="/monitor", status_code=303)


@router.get("/monitor", response_class=HTMLResponse)
def get_monitor_page(request: Request):
    settings = request.app.state.settings
    run_repo = request.app.state.run_repo
    step_repo = request.app.state.step_repo

    pipeline_rows = []
    for pipeline in settings.pipelines:
        recent_runs = []
        latest_run = None
        if run_repo is not None:
            # 그리드용 최대 25건, step 포함
            runs = run_repo.find_by_pipeline(pipeline.name, limit=25)
            recent_runs = [
                _build_run_response_with_steps(run, step_repo).model_dump(mode="json")
                for run in runs
            ]
            latest_run = recent_runs[0] if recent_runs else None

        pipeline_rows.append(
            {
                "name": pipeline.name,
                "table": pipeline.table,
                "strategy": pipeline.strategy,
                "schedule": pipeline.schedule,
                "next_run": _calc_next_run(pipeline.schedule),
                "latest_run": latest_run,
                "recent_runs": recent_runs,
            }
        )

    return HTMLResponse(render_monitor_page(pipeline_rows))


@router.get("/monitor/pipelines/{name}/runs/{run_id}", response_class=HTMLResponse)
def get_run_detail_page(name: str, run_id: str, request: Request):
    """특정 실행의 step 타임라인 상세 페이지."""
    run_repo = request.app.state.run_repo
    step_repo = request.app.state.step_repo
    settings = request.app.state.settings

    if run_repo is None:
        return HTMLResponse(
            render_unavailable_page(
                "Run Detail",
                "Repository is not configured for this runtime.",
                active_path="/monitor",
            ),
            status_code=503,
        )

    run_obj = run_repo.find_by_id(run_id)
    if run_obj is None or run_obj.pipeline_name != name:
        return HTMLResponse(
            render_unavailable_page(
                "Run Detail",
                f"Run '{run_id}' not found for pipeline '{name}'.",
                active_path="/monitor",
            ),
            status_code=404,
        )

    run_dict = _build_run_response_with_steps(run_obj, step_repo).model_dump(mode="json")
    pipeline_cfg = next((p for p in settings.pipelines if p.name == name), None)
    schedule = pipeline_cfg.schedule if pipeline_cfg else "-"

    return HTMLResponse(render_run_detail_page(run_dict, pipeline_name=name, schedule=schedule))


@router.get("/monitor/analytics", response_class=HTMLResponse)
def get_analytics_monitor_page(
    request: Request,
    dataset: str = Query(default="mes_ops"),
    dashboard_id: str = Query(default="operations_overview"),
):
    try:
        query_service = get_query_service(request)
    except Exception:
        return HTMLResponse(
            render_unavailable_page(
                "Analytics Dashboard",
                "Analytics query service is not configured for this runtime.",
                active_path="/monitor/analytics",
            ),
            status_code=503,
        )
    try:
        export_service = get_export_service(request)
    except Exception:
        export_service = None

    try:
        dashboard = query_service.get_dashboard_definition(
            dashboard_id=dashboard_id,
            dataset=dataset,
        ).model_dump(mode="json")
        selected_filters = _extract_selected_filters(request.query_params, dashboard["filters"])
        summary = query_service.query_summary(
            SummaryQueryRequest(dataset=dataset, filters=selected_filters)
        ).model_dump(mode="json")

        charts: dict[str, dict] = {}
        for chart_definition in dashboard["charts"]:
            charts[chart_definition["chart_id"]] = query_service.query_chart(
                ChartQueryRequest(
                    dataset=dataset,
                    chart_id=chart_definition["chart_id"],
                    granularity=chart_definition["default_granularity"],
                    limit=chart_definition["limit"],
                    filters=selected_filters,
                )
            ).model_dump(mode="json")

        detail_preview = None
        for drilldown_action in dashboard["drilldown_actions"]:
            if drilldown_action["status"] != "available":
                continue
            detail_key = _extract_detail_key(drilldown_action.get("endpoint"))
            if not detail_key:
                continue
            detail_preview = query_service.query_detail(
                DetailQueryRequest(
                    dataset=dataset,
                    detail_key=detail_key,
                    filters=selected_filters,
                    page=1,
                    page_size=8,
                )
            ).model_dump(mode="json")
            break

        export_jobs = []
        if export_service is not None:
            export_jobs = [
                job.model_dump(mode="json")
                for job in export_service.list_jobs(dataset=dataset, limit=8)
            ]
    except (AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        return HTMLResponse(
            render_unavailable_page(
                "Analytics Dashboard",
                str(exc),
                active_path="/monitor/analytics",
            ),
            status_code=404 if isinstance(exc, (AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError)) else 400,
        )

    return HTMLResponse(
        render_analytics_dashboard_page(
            {
                "dashboard": dashboard,
                "summary": summary,
                "charts": charts,
                "detail_preview": detail_preview,
                "filters_applied": selected_filters,
                "export_jobs": export_jobs,
            }
        )
    )


@router.post("/monitor/analytics/exports")
async def create_analytics_export_from_monitor(request: Request):
    try:
        query_service = get_query_service(request)
        export_service = get_export_service(request)
    except Exception:
        return HTMLResponse(
            render_unavailable_page(
                "Export Jobs",
                "Analytics query service or export service is not configured for this runtime.",
                active_path="/monitor/exports",
            ),
            status_code=503,
        )

    form_data = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=False)

    def _first(name: str, default: str = "") -> str:
        values = form_data.get(name)
        return values[0] if values else default

    dataset = _first("dataset", "mes_ops")
    dashboard_id = _first("dashboard_id", "operations_overview")

    try:
        dashboard = query_service.get_dashboard_definition(
            dashboard_id=dashboard_id,
            dataset=dataset,
        ).model_dump(mode="json")
        selected_filters = _extract_selected_filters(form_data, dashboard["filters"])
        create_response = export_service.create_export(
            ExportCreateRequest(
                dataset=dataset,
                action_key=_first("action_key"),
                format=ExportFormat(_first("format")),
                filters=selected_filters,
            )
        )
    except (ValueError, AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        return HTMLResponse(
            render_unavailable_page(
                "Export Jobs",
                str(exc),
                active_path="/monitor/exports",
            ),
            status_code=400,
        )

    return _redirect_to_exports(create_response.job_id, dataset)


@router.get("/monitor/exports", response_class=HTMLResponse)
def get_export_monitor_page(
    request: Request,
    dataset: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
):
    try:
        export_service = get_export_service(request)
    except Exception:
        return HTMLResponse(
            render_unavailable_page(
                "Export Jobs",
                "Export service is not configured for this runtime.",
                active_path="/monitor/exports",
            ),
            status_code=503,
        )

    jobs = [job.model_dump(mode="json") for job in export_service.list_jobs(dataset=dataset, limit=50)]
    counts = {
        "queued": sum(1 for job in jobs if job["status"] == "queued"),
        "running": sum(1 for job in jobs if job["status"] == "running"),
        "completed": sum(1 for job in jobs if job["status"] == "completed"),
    }
    if job_id:
        try:
            selected_job = export_service.get_job(job_id).model_dump(mode="json")
            if not any(job["job_id"] == job_id for job in jobs):
                jobs.insert(0, selected_job)
        except AnalyticsExportJobNotFoundError:
            pass

    return HTMLResponse(
        render_export_jobs_page(
            {
                "jobs": jobs,
                "selected_job_id": job_id,
                "counts": counts,
                "dataset": dataset,
                "retention_hours": export_service.retention_hours,
            }
        )
    )
