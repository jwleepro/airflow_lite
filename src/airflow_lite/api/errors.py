from fastapi import HTTPException

from airflow_lite.export import (
    AnalyticsExportJobNotFoundError,
    AnalyticsExportNotReadyError,
)
from airflow_lite.query import (
    AnalyticsDashboardNotFoundError,
    AnalyticsDatasetNotFoundError,
    AnalyticsQueryError,
)


def raise_query_http_error(exc: Exception) -> None:
    if isinstance(exc, (AnalyticsDashboardNotFoundError, AnalyticsDatasetNotFoundError)):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, AnalyticsQueryError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


def raise_export_http_error(exc: Exception) -> None:
    if isinstance(exc, AnalyticsExportJobNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, AnalyticsExportNotReadyError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise exc
