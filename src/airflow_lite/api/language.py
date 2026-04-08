from __future__ import annotations

from fastapi import Request

from airflow_lite.i18n import resolve_language


def resolve_request_language(request: Request, query_language: str | None = None) -> str:
    settings = request.app.state.settings
    webui = getattr(settings, "webui", None)
    default_language = getattr(webui, "default_language", None)
    accept_language = request.headers.get("accept-language")
    return resolve_language(
        query_language=query_language,
        default_language=default_language,
        accept_language=accept_language,
    )
