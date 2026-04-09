from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from airflow_lite.api.analytics_contracts import (
    AnalyticsFilterMetadataResponse,
    ChartQueryRequest,
    ChartQueryResponse,
    DashboardDefinitionResponse,
    DetailQueryRequest,
    DetailQueryResponse,
    ExportCreateRequest,
    ExportCreateResponse,
    ExportJobResponse,
    SummaryQueryRequest,
    SummaryQueryResponse,
)
from airflow_lite.api.dependencies import get_export_service, get_language, get_query_service
from airflow_lite.api.errors import raise_export_http_error, raise_query_http_error
from airflow_lite.export import (
    AnalyticsExportJobNotFoundError,
    AnalyticsExportNotReadyError,
)
from airflow_lite.query import (
    AnalyticsDashboardNotFoundError,
    AnalyticsDatasetNotFoundError,
    AnalyticsQueryError,
)

router = APIRouter(tags=["analytics"])


@router.post("/analytics/summary", response_model=SummaryQueryResponse)
def query_summary(body: SummaryQueryRequest, request: Request, language: str = Depends(get_language)):
    query_service = get_query_service(request)
    try:
        return query_service.query_summary(body, language=language)
    except (AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        raise_query_http_error(exc)


@router.post("/analytics/charts/{chart_id}/query", response_model=ChartQueryResponse)
def query_chart(
    chart_id: str,
    body: ChartQueryRequest,
    request: Request,
    language: str = Depends(get_language),
):
    query_service = get_query_service(request)
    if body.chart_id != chart_id:
        raise HTTPException(status_code=400, detail="chart_id in path and body must match.")

    try:
        return query_service.query_chart(body, language=language)
    except (AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        raise_query_http_error(exc)


@router.post("/analytics/details/{detail_key}/query", response_model=DetailQueryResponse)
def query_detail(
    detail_key: str,
    body: DetailQueryRequest,
    request: Request,
    language: str = Depends(get_language),
):
    query_service = get_query_service(request)
    if body.detail_key != detail_key:
        raise HTTPException(status_code=400, detail="detail_key in path and body must match.")

    try:
        return query_service.query_detail(body, language=language)
    except (AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        raise_query_http_error(exc)


@router.post("/analytics/exports", response_model=ExportCreateResponse)
def create_export(body: ExportCreateRequest, request: Request):
    export_service = get_export_service(request)
    try:
        return export_service.create_export(body)
    except (AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        raise_query_http_error(exc)


@router.get("/analytics/exports/{job_id}", response_model=ExportJobResponse)
def get_export_job(job_id: str, request: Request):
    export_service = get_export_service(request)
    try:
        return export_service.get_job(job_id)
    except AnalyticsExportJobNotFoundError as exc:
        raise_export_http_error(exc)


@router.get("/analytics/exports/{job_id}/download")
def download_export(job_id: str, request: Request):
    export_service = get_export_service(request)
    try:
        artifact_path, file_name = export_service.get_download_path(job_id)
    except (AnalyticsExportJobNotFoundError, AnalyticsExportNotReadyError) as exc:
        raise_export_http_error(exc)

    return FileResponse(path=artifact_path, filename=file_name)


@router.delete("/analytics/exports/{job_id}")
def delete_export_job(job_id: str, request: Request):
    export_service = get_export_service(request)
    try:
        export_service.delete_job(job_id)
    except AnalyticsExportJobNotFoundError as exc:
        raise_export_http_error(exc)
    return {"deleted": job_id}


@router.delete("/analytics/exports")
def delete_all_completed_exports(request: Request):
    export_service = get_export_service(request)
    count = export_service.delete_all_completed()
    return {"deleted_count": count}


@router.get("/analytics/filters", response_model=AnalyticsFilterMetadataResponse)
def get_filters(request: Request, dataset: str = Query(...), language: str = Depends(get_language)):
    query_service = get_query_service(request)
    try:
        return query_service.get_filter_metadata(dataset, language=language)
    except (AnalyticsDatasetNotFoundError, AnalyticsQueryError) as exc:
        raise_query_http_error(exc)


@router.get("/analytics/dashboards/{dashboard_id}", response_model=DashboardDefinitionResponse)
def get_dashboard_definition(
    dashboard_id: str,
    request: Request,
    dataset: str = Query(...),
    language: str = Depends(get_language),
):
    query_service = get_query_service(request)
    try:
        return query_service.get_dashboard_definition(
            dashboard_id=dashboard_id,
            dataset=dataset,
            language=language,
        )
    except (
        AnalyticsDashboardNotFoundError,
        AnalyticsDatasetNotFoundError,
        AnalyticsQueryError,
    ) as exc:
        raise_query_http_error(exc)
