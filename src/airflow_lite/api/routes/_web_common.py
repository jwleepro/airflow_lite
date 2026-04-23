from datetime import date
from urllib.parse import parse_qs, urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from airflow_lite.api.dependencies import get_export_service, get_runner_map, get_backfill_map
from airflow_lite.api.paths import MONITOR_EXPORTS_PATH
from airflow_lite.api.webui_analytics import render_unavailable_page
from airflow_lite.api.webui_helpers import t


def html_unavailable(
    title: str,
    message: str,
    *,
    active_path: str,
    language: str,
    status_code: int = 503,
) -> HTMLResponse:
    return HTMLResponse(
        render_unavailable_page(
            title, message, active_path=active_path, language=language
        ),
        status_code=status_code,
    )


def not_configured(component: str, *, active_path: str, language: str) -> HTMLResponse:
    return html_unavailable(
        component,
        f"{component} is not configured for this runtime.",
        active_path=active_path,
        language=language,
    )


def not_found(resource: str, name: str, *, active_path: str, language: str) -> HTMLResponse:
    return html_unavailable(
        resource,
        f"'{name}' not found for {resource.lower()}.",
        active_path=active_path,
        language=language,
        status_code=404,
    )


async def read_form_data(request: Request) -> dict[str, list[str]]:
    return parse_qs((await request.body()).decode("utf-8"), keep_blank_values=False)


def parse_bool_value(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_iso_date(value: str | None, *, field_name: str) -> date:
    if not value:
        raise ValueError(f"{field_name} is required.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format.") from exc


def pipeline_action_availability(request: Request, pipeline_name: str) -> dict[str, bool]:
    runner_map = get_runner_map(request)
    backfill_map = get_backfill_map(request)
    return {
        "can_trigger": pipeline_name in runner_map,
        "can_backfill": pipeline_name in backfill_map,
    }


def build_pipeline_actions(request: Request, pipeline_rows: list[dict]) -> dict[str, dict]:
    return {
        row["name"]: pipeline_action_availability(request, row["name"])
        for row in pipeline_rows
    }


def operation_notice(
    language: str, *, action: str | None, count: int | None = None
) -> dict | None:
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


def redirect(path: str, *, language: str = "en", **query_params) -> RedirectResponse:
    query_data = {key: value for key, value in query_params.items() if value}
    if language != "en":
        query_data["lang"] = language
    query = urlencode(query_data)
    return RedirectResponse(url=f"{path}{'?' + query if query else ''}", status_code=303)


def redirect_to_exports(job_id: str, dataset: str, language: str) -> RedirectResponse:
    return redirect(MONITOR_EXPORTS_PATH, language=language, job_id=job_id, dataset=dataset)


def try_get_export_service(request: Request, language: str) -> tuple:
    try:
        return get_export_service(request), None
    except Exception:
        return None, not_configured("Export Jobs", active_path=MONITOR_EXPORTS_PATH, language=language)
