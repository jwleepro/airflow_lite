from fastapi import APIRouter, HTTPException, Query, Request
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


def _get_query_service(request: Request):
    query_service = getattr(request.app.state, "analytics_query_service", None)
    if query_service is None:
        raise HTTPException(status_code=503, detail="analytics query service is not configured.")
    return query_service


def _get_export_service(request: Request):
    export_service = getattr(request.app.state, "analytics_export_service", None)
    if export_service is None:
        raise HTTPException(status_code=503, detail="analytics export service is not configured.")
    return export_service


@router.post("/analytics/summary", response_model=SummaryQueryResponse)
def query_summary(body: SummaryQueryRequest, request: Request):
    query_service = _get_query_service(request)
    try:
        return query_service.query_summary(body)
    except AnalyticsDatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnalyticsQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analytics/charts/{chart_id}/query", response_model=ChartQueryResponse)
def query_chart(chart_id: str, body: ChartQueryRequest, request: Request):
    query_service = _get_query_service(request)
    if body.chart_id != chart_id:
        raise HTTPException(status_code=400, detail="chart_id in path and body must match.")

    try:
        return query_service.query_chart(body)
    except AnalyticsDatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnalyticsQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analytics/details/{detail_key}/query", response_model=DetailQueryResponse)
def query_detail(detail_key: str, body: DetailQueryRequest, request: Request):
    query_service = _get_query_service(request)
    if body.detail_key != detail_key:
        raise HTTPException(status_code=400, detail="detail_key in path and body must match.")

    try:
        return query_service.query_detail(body)
    except AnalyticsDatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnalyticsQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analytics/exports", response_model=ExportCreateResponse)
def create_export(body: ExportCreateRequest, request: Request):
    export_service = _get_export_service(request)
    try:
        return export_service.create_export(body)
    except AnalyticsDatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnalyticsQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/analytics/exports/{job_id}", response_model=ExportJobResponse)
def get_export_job(job_id: str, request: Request):
    export_service = _get_export_service(request)
    try:
        return export_service.get_job(job_id)
    except AnalyticsExportJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analytics/exports/{job_id}/download")
def download_export(job_id: str, request: Request):
    export_service = _get_export_service(request)
    try:
        artifact_path, file_name = export_service.get_download_path(job_id)
    except AnalyticsExportJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnalyticsExportNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return FileResponse(path=artifact_path, filename=file_name)


@router.get("/analytics/filters", response_model=AnalyticsFilterMetadataResponse)
def get_filters(request: Request, dataset: str = Query(...)):
    query_service = _get_query_service(request)
    try:
        return query_service.get_filter_metadata(dataset)
    except AnalyticsDatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnalyticsQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/analytics/dashboards/{dashboard_id}", response_model=DashboardDefinitionResponse)
def get_dashboard_definition(dashboard_id: str, request: Request, dataset: str = Query(...)):
    query_service = _get_query_service(request)
    try:
        return query_service.get_dashboard_definition(dashboard_id=dashboard_id, dataset=dataset)
    except (AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnalyticsQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
