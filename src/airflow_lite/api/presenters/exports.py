"""Assemble data for the export jobs page."""

from __future__ import annotations

from airflow_lite.api.analytics_contracts import ExportCreateRequest, ExportFormat
from airflow_lite.api.presenters.admin_forms import _first_value
from airflow_lite.api.presenters.analytics import extract_selected_filters
from airflow_lite.export import AnalyticsExportJobNotFoundError


def build_export_page_data(export_service, *, dataset: str | None, job_id: str | None, limit: int) -> dict:
    jobs = [
        job.model_dump(mode="json")
        for job in export_service.list_jobs(dataset=dataset, limit=limit)
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

    return {
        "jobs": jobs,
        "selected_job_id": job_id,
        "counts": counts,
        "dataset": dataset,
        "retention_hours": export_service.retention_hours,
    }


def create_export_from_form(
    query_service,
    export_service,
    form_data: dict[str, list[str]],
    *,
    default_dataset: str,
    default_dashboard_id: str,
    language: str,
):
    """Parse form payload and trigger export creation.

    Returns the export-service create response. Raises the same exceptions
    that the underlying services raise so the route can translate them.
    """
    dataset = _first_value(form_data, "dataset", default_dataset) or default_dataset
    dashboard_id = _first_value(form_data, "dashboard_id", default_dashboard_id) or default_dashboard_id

    dashboard = query_service.get_dashboard_definition(
        dashboard_id=dashboard_id,
        dataset=dataset,
        language=language,
    ).model_dump(mode="json")
    selected_filters = extract_selected_filters(form_data, dashboard["filters"])

    create_response = export_service.create_export(
        ExportCreateRequest(
            dataset=dataset,
            action_key=_first_value(form_data, "action_key", "") or "",
            format=ExportFormat(_first_value(form_data, "format", "") or ""),
            filters=selected_filters,
        )
    )
    return create_response, dataset
