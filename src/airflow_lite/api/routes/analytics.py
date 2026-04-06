from fastapi import APIRouter, HTTPException, Query, Request

from airflow_lite.api.analytics_contracts import (
    AnalyticsFilterMetadataResponse,
    ChartQueryRequest,
    ChartQueryResponse,
    DashboardDefinitionResponse,
    SummaryQueryRequest,
    SummaryQueryResponse,
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
