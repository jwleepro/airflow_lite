from fastapi import HTTPException, Query, Request

from airflow_lite.api.language import resolve_request_language


def get_query_service(request: Request):
    query_service = getattr(request.app.state, "analytics_query_service", None)
    if query_service is None:
        raise HTTPException(status_code=503, detail="analytics query service is not configured.")
    return query_service


def get_export_service(request: Request):
    export_service = getattr(request.app.state, "analytics_export_service", None)
    if export_service is None:
        raise HTTPException(status_code=503, detail="analytics export service is not configured.")
    return export_service


def get_language(request: Request, lang: str | None = Query(default=None)) -> str:
    return resolve_request_language(request, lang)
