from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from airflow_lite.api.dependencies import (
    get_export_service,
    get_language,
    get_query_service,
)
from airflow_lite.api.language import resolve_request_language
from airflow_lite.api.paths import MONITOR_ANALYTICS_PATH, MONITOR_EXPORTS_PATH
from airflow_lite.api.forms import first_value as _first_value
from airflow_lite.api.presenters.analytics import build_dashboard_data
from airflow_lite.api.presenters.exports import create_export_from_form
from airflow_lite.api.routes._web_common import (
    html_unavailable,
    read_form_data,
    redirect_to_exports,
)
from airflow_lite.api.webui_analytics import render_analytics_dashboard_page
from airflow_lite.query import (
    AnalyticsDashboardNotFoundError,
    AnalyticsDatasetNotFoundError,
    AnalyticsQueryError,
)

router = APIRouter(include_in_schema=False)


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
        return html_unavailable(
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
        return html_unavailable(
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
        return html_unavailable(
            "Export Jobs",
            "Analytics query service or export service is not configured for this runtime.",
            active_path=MONITOR_EXPORTS_PATH,
            language=request_language,
        )

    form_data = await read_form_data(request)
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
        return html_unavailable(
            "Export Jobs",
            str(exc),
            active_path=MONITOR_EXPORTS_PATH,
            status_code=400,
            language=language,
        )

    return redirect_to_exports(create_response.job_id, dataset, language)
