from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from airflow_lite.api._resolver import resolve_backfill_manager
from airflow_lite.api.dependencies import (
    get_backfill_map,
    get_dispatch_service,
    get_language,
    get_run_repo,
    get_runner_map,
    get_step_repo,
)
from airflow_lite.api.language import resolve_request_language
from airflow_lite.api.paths import (
    MONITOR_PATH,
    MONITOR_PIPELINES_PATH,
    monitor_pipeline_detail_path,
    monitor_pipeline_run_detail_path,
)
from airflow_lite.api.forms import first_value as _first_value
from airflow_lite.api.presenters.monitor import (
    build_pipeline_detail_view_data,
    build_pipeline_rows,
    build_run_detail_data,
)
from airflow_lite.api.routes._web_common import (
    build_pipeline_actions,
    html_unavailable,
    operation_notice,
    parse_bool_value,
    parse_iso_date,
    pipeline_action_availability,
    read_form_data,
    redirect,
)
from airflow_lite.api.webui_monitor import (
    render_monitor_home_page,
    render_pipeline_list_page,
)
from airflow_lite.api.webui_helpers import t
from airflow_lite.api.webui_pipeline_detail import render_pipeline_detail_page
from airflow_lite.api.webui_run_detail import render_run_detail_page
from airflow_lite.service.dispatch_service import PipelineBusyError

router = APIRouter(include_in_schema=False)


def _pipeline_busy_message(language: str, name: str, exc: PipelineBusyError) -> str:
    if exc.run_id:
        if language == "ko":
            run_hint = (
                f"활성 실행: {exc.run_id}"
                f" ({exc.status or 'unknown'}, {exc.execution_date.isoformat() if exc.execution_date else 'unknown'})"
            )
        else:
            run_hint = (
                f"Active run: {exc.run_id}"
                f" ({exc.status or 'unknown'}, {exc.execution_date.isoformat() if exc.execution_date else 'unknown'})"
            )
    else:
        run_hint = ""
    return t(
        language,
        "webui.errors.pipeline_busy",
        pipeline_name=name,
        active_run_hint=run_hint,
    ).strip()


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
            pipeline_actions=build_pipeline_actions(request, pipeline_rows),
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
        return html_unavailable(
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
            actions=pipeline_action_availability(request, name),
            operation_notice=operation_notice(language, action=action, count=count),
        )
    )


@router.post(f"{MONITOR_PIPELINES_PATH}/{{name}}/trigger")
async def trigger_pipeline_from_monitor(
    name: str,
    request: Request,
    request_language: str = Depends(get_language),
):
    form_data = await read_form_data(request)
    language = resolve_request_language(
        request,
        _first_value(form_data, "lang") or request.query_params.get("lang"),
    )
    runner_map = get_runner_map(request)
    if name not in runner_map:
        return html_unavailable(
            "Pipeline action",
            f"Pipeline '{name}' is not configured for manual trigger.",
            active_path=MONITOR_PIPELINES_PATH,
            status_code=404,
            language=language or request_language,
        )

    execution_date_raw = _first_value(form_data, "execution_date")
    force = parse_bool_value(_first_value(form_data, "force"))
    execution_date = (
        parse_iso_date(execution_date_raw, field_name="execution_date")
        if execution_date_raw
        else date.today()
    )
    dispatcher = get_dispatch_service(request)
    try:
        run = dispatcher.submit_manual_run(
            pipeline_name=name,
            execution_date=execution_date,
            force_rerun=force,
            trigger_type="manual",
        )
    except PipelineBusyError as exc:
        return html_unavailable(
            "Pipeline busy",
            _pipeline_busy_message(language or request_language, name, exc),
            active_path=MONITOR_PIPELINES_PATH,
            status_code=409,
            language=language or request_language,
        )
    return redirect(
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
    form_data = await read_form_data(request)
    language = resolve_request_language(
        request,
        _first_value(form_data, "lang") or request.query_params.get("lang"),
    )
    backfill_map = get_backfill_map(request)
    if name not in backfill_map:
        return html_unavailable(
            "Backfill",
            f"Pipeline '{name}' is not configured for backfill.",
            active_path=MONITOR_PIPELINES_PATH,
            status_code=404,
            language=language or request_language,
        )

    try:
        start_date = parse_iso_date(_first_value(form_data, "start_date"), field_name="start_date")
        end_date = parse_iso_date(_first_value(form_data, "end_date"), field_name="end_date")
    except ValueError as exc:
        return html_unavailable(
            "Backfill",
            str(exc),
            active_path=MONITOR_PIPELINES_PATH,
            status_code=400,
            language=language or request_language,
        )
    if end_date < start_date:
        return html_unavailable(
            "Backfill",
            "end_date는 start_date보다 같거나 이후여야 합니다.",
            active_path=MONITOR_PIPELINES_PATH,
            status_code=400,
            language=language or request_language,
        )

    dispatcher = get_dispatch_service(request)
    try:
        dispatcher.submit_backfill(
            pipeline_name=name,
            start_date=start_date,
            end_date=end_date,
            force_rerun=parse_bool_value(_first_value(form_data, "force")),
        )
    except PipelineBusyError as exc:
        return html_unavailable(
            "Pipeline busy",
            _pipeline_busy_message(language or request_language, name, exc),
            active_path=MONITOR_PIPELINES_PATH,
            status_code=409,
            language=language or request_language,
        )
    return redirect(
        monitor_pipeline_detail_path(name),
        language=language or request_language,
        action="backfill",
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
        return html_unavailable(
            "Run Detail",
            "Repository is not configured for this runtime.",
            active_path=MONITOR_PATH,
            language=language,
        )

    run_obj = run_repo.find_by_id(run_id)
    if run_obj is None or run_obj.pipeline_name != name:
        return html_unavailable(
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
            actions=pipeline_action_availability(request, name),
            operation_notice=operation_notice(language, action=action),
        )
    )
