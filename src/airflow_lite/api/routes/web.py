from datetime import date
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from airflow_lite.api._resolver import (
    resolve_backfill_manager,
    resolve_runner,
)
from airflow_lite.api.dependencies import (
    get_backfill_map,
    get_export_service,
    get_language,
    get_query_service,
    get_run_repo,
    get_runner_map,
    get_step_repo,
)
from airflow_lite.api.language import resolve_request_language
from airflow_lite.api.paths import (
    MONITOR_ADMIN_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_EXPORT_DELETE_COMPLETED_PATH,
    MONITOR_EXPORT_DELETE_JOB_PATH,
    MONITOR_PATH,
    MONITOR_PIPELINES_PATH,
    monitor_pipeline_detail_path,
    monitor_pipeline_run_detail_path,
)
from airflow_lite.api.presenters import admin_forms, admin_page
from airflow_lite.api.presenters.admin_forms import _first_value
from airflow_lite.api.presenters.analytics import build_dashboard_data
from airflow_lite.api.presenters.exports import (
    build_export_page_data,
    create_export_from_form,
)
from airflow_lite.api.presenters.monitor import (
    build_pipeline_detail_view_data,
    build_pipeline_rows,
    build_run_detail_data,
)
from airflow_lite.api.webui_admin import render_admin_page
from airflow_lite.api.webui_analytics import (
    render_analytics_dashboard_page,
    render_unavailable_page,
)
from airflow_lite.api.webui_exports import render_export_jobs_page
from airflow_lite.api.webui_helpers import t
from airflow_lite.api.webui_pipeline_detail import render_pipeline_detail_page
from airflow_lite.api.webui_monitor import render_monitor_home_page, render_pipeline_list_page
from airflow_lite.api.webui_run_detail import render_run_detail_page
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


async def _read_form_data(request: Request) -> dict[str, list[str]]:
    from urllib.parse import parse_qs

    return parse_qs((await request.body()).decode("utf-8"), keep_blank_values=False)


def _parse_bool_value(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_iso_date(value: str | None, *, field_name: str) -> date:
    if not value:
        raise ValueError(f"{field_name} is required.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format.") from exc


def _pipeline_action_availability(request: Request, pipeline_name: str) -> dict[str, bool]:
    runner_map = getattr(request.app.state, "runner_map", {}) or {}
    backfill_map = getattr(request.app.state, "backfill_map", {}) or {}
    return {
        "can_trigger": pipeline_name in runner_map,
        "can_backfill": pipeline_name in backfill_map,
    }


def _build_pipeline_actions(request: Request, pipeline_rows: list[dict]) -> dict[str, dict]:
    return {
        row["name"]: _pipeline_action_availability(request, row["name"])
        for row in pipeline_rows
    }


def _operation_notice(language: str, *, action: str | None, count: int | None = None) -> dict | None:
    if action == "triggered":
        return {
            "tone": "ok",
            "title": t(language, "webui.actions.notice.triggered.title"),
            "detail": t(language, "webui.actions.notice.triggered.detail"),
        }
    if action == "force_rerun":
        return {
            "tone": "warn",
            "title": t(language, "webui.actions.notice.force_rerun.title"),
            "detail": t(language, "webui.actions.notice.force_rerun.detail"),
        }
    if action == "backfill":
        return {
            "tone": "ok",
            "title": t(language, "webui.actions.notice.backfill.title"),
            "detail": t(language, "webui.actions.notice.backfill.detail", count=count or 0),
        }
    return None


def _redirect(path: str, *, language: str = "en", **query_params) -> RedirectResponse:
    query_data = {key: value for key, value in query_params.items() if value}
    if language != "en":
        query_data["lang"] = language
    query = urlencode(query_data)
    return RedirectResponse(url=f"{path}{'?' + query if query else ''}", status_code=303)


def _redirect_to_exports(job_id: str, dataset: str, language: str) -> RedirectResponse:
    return _redirect(MONITOR_EXPORTS_PATH, language=language, job_id=job_id, dataset=dataset)


def _try_get_export_service(request: Request, language: str) -> tuple:
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


# --------------------------------------------------------------------------- #
# Admin page
# --------------------------------------------------------------------------- #


@router.get(MONITOR_ADMIN_PATH, response_class=HTMLResponse)
def get_admin_page(request: Request, language: str = Depends(get_language)):
    admin_repo = getattr(request.app.state, "admin_repo", None)
    if not admin_repo:
        return _html_unavailable(
            "Admin UI",
            "AdminRepository is not configured.",
            active_path=MONITOR_ADMIN_PATH,
            language=language,
        )

    view_data = admin_page.build_admin_view_data(admin_repo)
    return HTMLResponse(render_admin_page(view_data, language=language))


async def _handle_admin_form(
    request: Request,
    handler,
    language: str,
) -> RedirectResponse:
    admin_repo = getattr(request.app.state, "admin_repo", None)
    if admin_repo is not None:
        form_data = await _read_form_data(request)
        handler(admin_repo, form_data)
    return _redirect(MONITOR_ADMIN_PATH, language=language)


@router.post(f"{MONITOR_ADMIN_PATH}/connections")
async def create_connection_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_connection, language)


@router.post(f"{MONITOR_ADMIN_PATH}/connections/delete")
async def delete_connection_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_connection, language)


@router.post(f"{MONITOR_ADMIN_PATH}/variables")
async def create_variable_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_variable, language)


@router.post(f"{MONITOR_ADMIN_PATH}/variables/delete")
async def delete_variable_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_variable, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pools")
async def create_pool_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_pool, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pools/delete")
async def delete_pool_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_pool, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pipelines")
async def create_pipeline_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.create_pipeline, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pipelines/edit")
async def edit_pipeline_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.update_pipeline, language)


@router.post(f"{MONITOR_ADMIN_PATH}/pipelines/delete")
async def delete_pipeline_from_monitor(request: Request, language: str = Depends(get_language)):
    return await _handle_admin_form(request, admin_forms.delete_pipeline, language)


# --------------------------------------------------------------------------- #
# Monitor (runs overview) page
# --------------------------------------------------------------------------- #


@router.get(MONITOR_PATH, response_class=HTMLResponse)
def get_monitor_home_page(request: Request, language: str = Depends(get_language)):
    from airflow_lite.api.routes.health import _check_disk, _check_mart_db, _check_scheduler

    settings = request.app.state.settings
    run_repo = get_run_repo(request)
    step_repo = get_step_repo(request)

    pipeline_rows = build_pipeline_rows(settings, run_repo, step_repo)
    health_checks = [
        _check_scheduler(request),
        _check_mart_db(request),
        _check_disk(request),
    ]
    return HTMLResponse(
        render_monitor_home_page(
            pipeline_rows,
            webui_config=settings.webui,
            language=language,
            health_checks=[
                {"name": c.name, "status": c.status, "detail": c.detail}
                for c in health_checks
            ],
        )
    )


@router.get(MONITOR_PIPELINES_PATH, response_class=HTMLResponse)
def get_monitor_pipeline_list_page(
    request: Request,
    q: str | None = Query(default=None),
    state: str | None = Query(default=None),
    language: str = Depends(get_language),
):
    settings = request.app.state.settings
    run_repo = get_run_repo(request)
    step_repo = get_step_repo(request)
    pipeline_rows = build_pipeline_rows(settings, run_repo, step_repo)

    return HTMLResponse(
        render_pipeline_list_page(
            pipeline_rows,
            webui_config=settings.webui,
            language=language,
            search_query=q or "",
            state=state or "all",
            pipeline_actions=_build_pipeline_actions(request, pipeline_rows),
        )
    )


@router.get(f"{MONITOR_PIPELINES_PATH}/{{name}}", response_class=HTMLResponse)
def get_monitor_pipeline_detail_page(
    name: str,
    request: Request,
    action: str | None = Query(default=None),
    count: int | None = Query(default=None),
    language: str = Depends(get_language),
):
    settings = request.app.state.settings
    run_repo = get_run_repo(request)
    step_repo = get_step_repo(request)
    page = build_pipeline_detail_view_data(settings, run_repo, step_repo, name)
    if page is None:
        return _html_unavailable(
            "DAG Details",
            f"Pipeline '{name}' is not configured.",
            active_path=MONITOR_PIPELINES_PATH,
            status_code=404,
            language=language,
        )

    return HTMLResponse(
        render_pipeline_detail_page(
            page,
            language=language,
            actions=_pipeline_action_availability(request, name),
            operation_notice=_operation_notice(language, action=action, count=count),
        )
    )


@router.post(f"{MONITOR_PIPELINES_PATH}/{{name}}/trigger")
async def trigger_pipeline_from_monitor(
    name: str,
    request: Request,
    request_language: str = Depends(get_language),
):
    form_data = await _read_form_data(request)
    language = resolve_request_language(
        request,
        _first_value(form_data, "lang") or request.query_params.get("lang"),
    )
    runner_map = get_runner_map(request)
    if name not in runner_map:
        return _html_unavailable(
            "Pipeline action",
            f"Pipeline '{name}' is not configured for manual trigger.",
            active_path=MONITOR_PIPELINES_PATH,
            status_code=404,
            language=language or request_language,
        )

    execution_date_raw = _first_value(form_data, "execution_date")
    force = _parse_bool_value(_first_value(form_data, "force"))
    execution_date = (
        _parse_iso_date(execution_date_raw, field_name="execution_date")
        if execution_date_raw
        else date.today()
    )
    runner = resolve_runner(runner_map[name])
    run = runner.run(
        execution_date=execution_date,
        trigger_type="manual",
        force_rerun=force,
    )
    return _redirect(
        monitor_pipeline_run_detail_path(name, run.id),
        language=language or request_language,
        action="force_rerun" if force else "triggered",
    )


@router.post(f"{MONITOR_PIPELINES_PATH}/{{name}}/backfill")
async def request_pipeline_backfill_from_monitor(
    name: str,
    request: Request,
    request_language: str = Depends(get_language),
):
    form_data = await _read_form_data(request)
    language = resolve_request_language(
        request,
        _first_value(form_data, "lang") or request.query_params.get("lang"),
    )
    backfill_map = get_backfill_map(request)
    if name not in backfill_map:
        return _html_unavailable(
            "Backfill",
            f"Pipeline '{name}' is not configured for backfill.",
            active_path=MONITOR_PIPELINES_PATH,
            status_code=404,
            language=language or request_language,
        )

    try:
        start_date = _parse_iso_date(_first_value(form_data, "start_date"), field_name="start_date")
        end_date = _parse_iso_date(_first_value(form_data, "end_date"), field_name="end_date")
    except ValueError as exc:
        return _html_unavailable(
            "Backfill",
            str(exc),
            active_path=MONITOR_PIPELINES_PATH,
            status_code=400,
            language=language or request_language,
        )

    manager = resolve_backfill_manager(backfill_map[name])
    runs = manager.run_backfill(
        pipeline_name=name,
        start_date=start_date,
        end_date=end_date,
        force_rerun=_parse_bool_value(_first_value(form_data, "force")),
    )
    return _redirect(
        monitor_pipeline_detail_path(name),
        language=language or request_language,
        action="backfill",
        count=len(runs),
    )


@router.get(f"{MONITOR_PIPELINES_PATH}/{{name}}/runs/{{run_id}}", response_class=HTMLResponse)
def get_run_detail_page(
    name: str,
    run_id: str,
    request: Request,
    action: str | None = Query(default=None),
    language: str = Depends(get_language),
):
    run_repo = getattr(request.app.state, "run_repo", None)
    step_repo = getattr(request.app.state, "step_repo", None)
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

    run_dict, schedule = build_run_detail_data(run_obj, step_repo, settings, name)
    pipeline_cfg = next((p for p in settings.pipelines if p.name == name), None)
    pipeline_meta = {
        "table": getattr(pipeline_cfg, "table", None),
        "partition_column": getattr(pipeline_cfg, "partition_column", None),
        "strategy": getattr(pipeline_cfg, "strategy", None),
        "schedule": getattr(pipeline_cfg, "schedule", schedule),
        "chunk_size": getattr(pipeline_cfg, "chunk_size", None),
        "columns": getattr(pipeline_cfg, "columns", None),
        "incremental_key": getattr(pipeline_cfg, "incremental_key", None),
    }

    # Grid View: collect recent runs with steps for this pipeline
    grid_runs: list[dict] = []
    grid_limit = getattr(settings.webui, "grid_view_run_limit", 10)
    recent_run_objs, _ = run_repo.find_by_pipeline_paginated(name, page=1, page_size=grid_limit)
    for r in recent_run_objs:
        from airflow_lite.api.schemas import build_run_response_with_steps as _build
        grid_runs.append(_build(r, step_repo).model_dump(mode="json"))

    return HTMLResponse(
        render_run_detail_page(
            run_dict, pipeline_name=name, schedule=schedule,
            language=language, grid_runs=grid_runs,
            pipeline_meta=pipeline_meta,
            actions=_pipeline_action_availability(request, name),
            operation_notice=_operation_notice(language, action=action),
        )
    )


# --------------------------------------------------------------------------- #
# Analytics dashboard page
# --------------------------------------------------------------------------- #


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
        data = build_dashboard_data(
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
    language = resolve_request_language(request, _first_value(form_data, "lang"))

    try:
        create_response, dataset = create_export_from_form(
            query_service,
            export_service,
            form_data,
            default_dataset=webui.default_dataset,
            default_dashboard_id=webui.default_dashboard_id,
            language=language,
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

    data = build_export_page_data(
        export_service,
        dataset=dataset,
        job_id=job_id,
        limit=webui.export_jobs_page_limit,
    )

    return HTMLResponse(
        render_export_jobs_page(data, webui_config=webui, language=language)
    )
