from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from airflow_lite.api.analytics_contracts import (
    ChartQueryRequest,
    DetailQueryRequest,
    ExportCreateRequest,
    ExportFormat,
    SummaryQueryRequest,
)
from airflow_lite.api.dependencies import get_export_service, get_language, get_query_service
from airflow_lite.api.language import resolve_request_language
from airflow_lite.api.paths import (
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_EXPORT_DELETE_COMPLETED_PATH,
    MONITOR_EXPORT_DELETE_JOB_PATH,
    MONITOR_PATH,
)
from airflow_lite.api.schemas import build_run_response_with_steps
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


def _html_unavailable(
    title: str,
    message: str,
    *,
    active_path: str,
    language: str,
    status_code: int = 503,
) -> HTMLResponse:
    return HTMLResponse(
        render_unavailable_page(title, message, active_path=active_path, language=language),
        status_code=status_code,
    )


def _read_form_values(body: bytes) -> dict[str, list[str]]:
    return parse_qs(body.decode("utf-8"), keep_blank_values=False)


async def _read_form_data(request: Request) -> dict[str, list[str]]:
    return _read_form_values(await request.body())


def _first_value(values: dict[str, list[str]], key: str, default: str | None = None) -> str | None:
    items = values.get(key)
    if not items:
        return default
    return items[0]


def _redirect(path: str, *, language: str = "en", **query_params) -> RedirectResponse:
    query_data = {key: value for key, value in query_params.items() if value}
    if language != "en":
        query_data["lang"] = language
    query = urlencode(query_data)
    return RedirectResponse(url=f"{path}{'?' + query if query else ''}", status_code=303)


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


def _redirect_to_exports(job_id: str, dataset: str, language: str) -> RedirectResponse:
    return _redirect(MONITOR_EXPORTS_PATH, language=language, job_id=job_id, dataset=dataset)


def _try_get_export_service(request: Request, language: str) -> tuple:
    """Export service를 가져오거나, 실패 시 (None, HTMLResponse)를 반환한다."""
    try:
        return get_export_service(request), None
    except Exception:
        return None, _html_unavailable(
            "Export Jobs",
            "Export service is not configured for this runtime.",
            active_path=MONITOR_EXPORTS_PATH,
            language=language,
        )


@router.get("/")
def redirect_root(request: Request):
    requested_lang = request.query_params.get("lang")
    if requested_lang is None:
        return _redirect(MONITOR_PATH)
    language = resolve_request_language(request, requested_lang)
    return _redirect(MONITOR_PATH, language=language)


@router.get(MONITOR_PATH, response_class=HTMLResponse)
def get_monitor_page(request: Request, language: str = Depends(get_language)):
    settings = request.app.state.settings
    run_repo = request.app.state.run_repo
    step_repo = request.app.state.step_repo
    webui = settings.webui

    pipeline_rows = []
    for pipeline in settings.pipelines:
        recent_runs = []
        latest_run = None
        if run_repo is not None:
            runs = run_repo.find_by_pipeline(pipeline.name, limit=webui.recent_runs_limit)
            recent_runs = [
                build_run_response_with_steps(run, step_repo).model_dump(mode="json")
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

    return HTMLResponse(render_monitor_page(pipeline_rows, webui_config=webui, language=language))


@router.get(f"{MONITOR_PATH}/pipelines/{{name}}/runs/{{run_id}}", response_class=HTMLResponse)
def get_run_detail_page(name: str, run_id: str, request: Request, language: str = Depends(get_language)):
    """특정 실행의 step 타임라인 상세 페이지."""
    run_repo = request.app.state.run_repo
    step_repo = request.app.state.step_repo
    settings = request.app.state.settings

    if run_repo is None:
        return _html_unavailable(
            "Run Detail",
            "Repository is not configured for this runtime.",
            active_path=MONITOR_PATH,
            language=language,
        )

    run_obj = run_repo.find_by_id(run_id)
    if run_obj is None or run_obj.pipeline_name != name:
        return _html_unavailable(
            "Run Detail",
            f"Run '{run_id}' not found for pipeline '{name}'.",
            active_path=MONITOR_PATH,
            status_code=404,
            language=language,
        )

    run_dict = build_run_response_with_steps(run_obj, step_repo).model_dump(mode="json")
    pipeline_cfg = next((p for p in settings.pipelines if p.name == name), None)
    schedule = pipeline_cfg.schedule if pipeline_cfg else "-"

    return HTMLResponse(
        render_run_detail_page(run_dict, pipeline_name=name, schedule=schedule, language=language)
    )


def _build_dashboard_data(
    query_service,
    export_service,
    *,
    dataset: str,
    dashboard_id: str,
    selected_filters_source,
    detail_preview_page_size: int,
    export_jobs_limit: int,
    language: str,
) -> dict:
    """대시보드 페이지에 필요한 데이터를 조립한다."""
    dashboard = query_service.get_dashboard_definition(
        dashboard_id=dashboard_id,
        dataset=dataset,
        language=language,
    ).model_dump(mode="json")
    selected_filters = _extract_selected_filters(selected_filters_source, dashboard["filters"])
    summary = query_service.query_summary(
        SummaryQueryRequest(dataset=dataset, filters=selected_filters),
        language=language,
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
            ),
            language=language,
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
                page_size=detail_preview_page_size,
            ),
            language=language,
        ).model_dump(mode="json")
        break

    export_jobs = []
    if export_service is not None:
        export_jobs = [
            job.model_dump(mode="json")
            for job in export_service.list_jobs(dataset=dataset, limit=export_jobs_limit)
        ]

    return {
        "dashboard": dashboard,
        "summary": summary,
        "charts": charts,
        "detail_preview": detail_preview,
        "filters_applied": selected_filters,
        "export_jobs": export_jobs,
    }


@router.get(MONITOR_ANALYTICS_PATH, response_class=HTMLResponse)
def get_analytics_monitor_page(
    request: Request,
    dataset: str | None = Query(default=None),
    dashboard_id: str | None = Query(default=None),
    language: str = Depends(get_language),
):
    settings = request.app.state.settings
    webui = settings.webui
    dataset = dataset or webui.default_dataset
    dashboard_id = dashboard_id or webui.default_dashboard_id

    try:
        query_service = get_query_service(request)
    except Exception:
        return _html_unavailable(
            "Analytics Dashboard",
            "Analytics query service is not configured for this runtime.",
            active_path=MONITOR_ANALYTICS_PATH,
            language=language,
        )
    try:
        export_service = get_export_service(request)
    except Exception:
        export_service = None

    try:
        data = _build_dashboard_data(
            query_service,
            export_service,
            dataset=dataset,
            dashboard_id=dashboard_id,
            selected_filters_source=request.query_params,
            detail_preview_page_size=webui.detail_preview_page_size,
            export_jobs_limit=webui.analytics_export_jobs_limit,
            language=language,
        )
    except (AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        return _html_unavailable(
            "Analytics Dashboard",
            str(exc),
            active_path=MONITOR_ANALYTICS_PATH,
            status_code=404 if isinstance(exc, (AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError)) else 400,
            language=language,
        )

    return HTMLResponse(
        render_analytics_dashboard_page(data, webui_config=webui, language=language)
    )


@router.post(f"{MONITOR_ANALYTICS_PATH}/exports")
async def create_analytics_export_from_monitor(request: Request, request_language: str = Depends(get_language)):
    settings = request.app.state.settings
    webui = settings.webui
    try:
        query_service = get_query_service(request)
        export_service = get_export_service(request)
    except Exception:
        return _html_unavailable(
            "Export Jobs",
            "Analytics query service or export service is not configured for this runtime.",
            active_path=MONITOR_EXPORTS_PATH,
            language=request_language,
        )

    form_data = await _read_form_data(request)
    dataset = _first_value(form_data, "dataset", webui.default_dataset) or webui.default_dataset
    dashboard_id = _first_value(form_data, "dashboard_id", webui.default_dashboard_id) or webui.default_dashboard_id
    language = resolve_request_language(request, _first_value(form_data, "lang"))

    try:
        dashboard = query_service.get_dashboard_definition(
            dashboard_id=dashboard_id,
            dataset=dataset,
            language=language,
        ).model_dump(mode="json")
        selected_filters = _extract_selected_filters(form_data, dashboard["filters"])
        create_response = export_service.create_export(
            ExportCreateRequest(
                dataset=dataset,
                action_key=_first_value(form_data, "action_key", "") or "",
                format=ExportFormat(_first_value(form_data, "format", "") or ""),
                filters=selected_filters,
            )
        )
    except (ValueError, AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        return _html_unavailable(
            "Export Jobs",
            str(exc),
            active_path=MONITOR_EXPORTS_PATH,
            status_code=400,
            language=language,
        )

    return _redirect_to_exports(create_response.job_id, dataset, language)


@router.post(MONITOR_EXPORT_DELETE_JOB_PATH)
async def delete_export_job_from_monitor(request: Request, request_language: str = Depends(get_language)):
    export_service, err = _try_get_export_service(request, request_language)
    if err:
        return err

    form_data = await _read_form_data(request)
    job_id = _first_value(form_data, "job_id")
    dataset = _first_value(form_data, "dataset")
    language = resolve_request_language(request, _first_value(form_data, "lang"))
    if job_id:
        try:
            export_service.delete_job(job_id)
        except AnalyticsExportJobNotFoundError:
            pass

    return _redirect(MONITOR_EXPORTS_PATH, language=language, dataset=dataset)


@router.post(MONITOR_EXPORT_DELETE_COMPLETED_PATH)
async def delete_completed_exports_from_monitor(request: Request, request_language: str = Depends(get_language)):
    export_service, err = _try_get_export_service(request, request_language)
    if err:
        return err

    form_data = await _read_form_data(request)
    dataset = _first_value(form_data, "dataset")
    language = resolve_request_language(request, _first_value(form_data, "lang"))
    export_service.delete_all_completed()

    return _redirect(MONITOR_EXPORTS_PATH, language=language, dataset=dataset)


@router.get(MONITOR_EXPORTS_PATH, response_class=HTMLResponse)
def get_export_monitor_page(
    request: Request,
    dataset: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
    language: str = Depends(get_language),
):
    settings = request.app.state.settings
    webui = settings.webui
    export_service, err = _try_get_export_service(request, language)
    if err:
        return err

    jobs = [
        job.model_dump(mode="json")
        for job in export_service.list_jobs(dataset=dataset, limit=webui.export_jobs_page_limit)
    ]
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
            },
            webui_config=webui,
            language=language,
        )
    )
