"""WebUI 공통 포맷·URL·아이콘 헬퍼.

HTML/CSS/레이아웃은 `templates/` 아래 Jinja 템플릿과 `static/css/app.css`로
이관됐고, 이 모듈은 Jinja globals로 노출되는 소형 유틸만 남겨 둔다.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from markupsafe import Markup

from airflow_lite.i18n import DEFAULT_LANGUAGE, translate


# ---------------------------------------------------------------------------
# 포맷 / 상태 헬퍼
# ---------------------------------------------------------------------------

def fmt(value, fallback: str = "-"):
    """Format a value for display.

    Returns a ``Markup`` instance so Jinja2 autoescape treats the result
    as already-safe (prevents double-escaping when templates call
    ``{{ fmt(x) }}``). The returned HTML is still escaped via
    :func:`html.escape`, so the contract for Python callers is unchanged.
    """
    if value in (None, ""):
        return Markup(escape(fallback))
    return Markup(escape(str(value)))


def fmt_duration(started_at: str | None, finished_at: str | None) -> str:
    """두 ISO 타임스탬프 차이를 '2m 30s' 형식으로 반환."""
    if not started_at:
        return "-"
    try:
        start = datetime.fromisoformat(str(started_at))
        end = datetime.fromisoformat(str(finished_at)) if finished_at else datetime.now()
        seconds = max(0, int((end - start).total_seconds()))
        if seconds < 60:
            return f"{seconds}s"
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins}m"
    except (ValueError, TypeError):
        return "-"


def t(language: str, key: str, **kwargs) -> str:
    return translate(key, language, **kwargs)


def cfg(webui_config, key: str, default):
    if webui_config is None:
        return default
    if isinstance(webui_config, dict):
        return webui_config.get(key, default)
    return getattr(webui_config, key, default)


# ---------------------------------------------------------------------------
# URL 헬퍼
# ---------------------------------------------------------------------------

def with_language_query(href: str, language: str) -> str:
    split = urlsplit(href)
    query_pairs = [(k, v) for k, v in parse_qsl(split.query, keep_blank_values=True) if k != "lang"]
    if language != DEFAULT_LANGUAGE:
        query_pairs.append(("lang", language))
    query_string = urlencode(query_pairs)
    return urlunsplit((split.scheme, split.netloc, split.path, query_string, split.fragment))


def build_url(path: str, **params) -> str:
    """경로에 쿼리 파라미터를 안전하게 붙인다.

    ``None`` 값은 제거되고 나머지는 ``urlencode``로 이스케이프한다.
    파라미터가 하나도 남지 않으면 ``path``를 그대로 반환한다.
    """
    filtered = [(k, v) for k, v in params.items() if v is not None]
    if not filtered:
        return path
    return f"{path}?{urlencode(filtered)}"


# ---------------------------------------------------------------------------
# 아이콘 SVG 상수 (Jinja globals로 노출)
# ---------------------------------------------------------------------------

ICON_PIPELINES = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
  <path fill="currentColor" d="M4 10.5a2.5 2.5 0 0 1 2.5-2.5h2.2a.9.9 0 0 0 .64-.26l1.6-1.6A3.5 3.5 0 0 1 15.4 5H19.5A2.5 2.5 0 0 1 22 7.5v9A2.5 2.5 0 0 1 19.5 19h-13A2.5 2.5 0 0 1 4 16.5v-6Z"/>
  <path fill="rgba(255,255,255,0.22)" d="M4.6 9.7c.5-.4 1.1-.7 1.9-.7h2.5c.5 0 1 .2 1.4.6l.6.6c.4.4.9.6 1.4.6h8.8c.3 0 .6.3.6.6v5.1A2.5 2.5 0 0 1 19.3 19H6.7A2.5 2.5 0 0 1 4.2 16.5V10.6c0-.4.1-.7.4-.9Z"/>
</svg>
""".strip()

ICON_ANALYTICS = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
  <path fill="currentColor" d="M5 19a1 1 0 0 1-1-1V6.5a2.5 2.5 0 0 1 2.5-2.5h11A2.5 2.5 0 0 1 20 6.5V18a1 1 0 0 1-1 1H5Z"/>
  <path fill="rgba(255,255,255,0.22)" d="M7 16.8a.8.8 0 0 1-.8-.8v-6.2a.8.8 0 0 1 1.6 0V16c0 .44-.36.8-.8.8Zm4.2 0a.8.8 0 0 1-.8-.8V8.8a.8.8 0 1 1 1.6 0V16c0 .44-.36.8-.8.8Zm4.2 0a.8.8 0 0 1-.8-.8v-4.1a.8.8 0 1 1 1.6 0V16c0 .44-.36.8-.8.8Z"/>
</svg>
""".strip()

ICON_EXPORTS = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
  <path fill="currentColor" d="M6.5 3h7.2a3 3 0 0 1 2.12.88l3.3 3.3A3 3 0 0 1 20 9.3V18a3 3 0 0 1-3 3h-10a3 3 0 0 1-3-3V6.5a3.5 3.5 0 0 1 3.5-3.5Z"/>
  <path fill="rgba(255,255,255,0.22)" d="M12 18.2a.9.9 0 0 1-.9-.9v-5.1l-1.6 1.6a.9.9 0 1 1-1.27-1.27l3.13-3.13a.9.9 0 0 1 1.27 0l3.13 3.13a.9.9 0 1 1-1.27 1.27l-1.6-1.6v5.1a.9.9 0 0 1-.9.9Z"/>
</svg>
""".strip()

ICON_ADMIN = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
  <path fill="currentColor" d="M12 2a5 5 0 0 1 5 5v1.1a6.5 6.5 0 0 1 3.5 5.7V18a3 3 0 0 1-3 3h-11a3 3 0 0 1-3-3v-4.2A6.5 6.5 0 0 1 7 8.1V7a5 5 0 0 1 5-5Z"/>
  <path fill="rgba(255,255,255,0.22)" d="M12 9.8a2.6 2.6 0 0 1 2.6 2.6 2.6 2.6 0 0 1-1.4 2.3V17a1.2 1.2 0 0 1-2.4 0v-2.3a2.6 2.6 0 0 1-1.4-2.3A2.6 2.6 0 0 1 12 9.8Z"/>
</svg>
""".strip()

ICON_DOCS = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
  <path fill="currentColor" d="M7 3h10a3 3 0 0 1 3 3v12.5a2.5 2.5 0 0 1-2.5 2.5H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z"/>
  <path fill="rgba(255,255,255,0.22)" d="M8 8.2c0-.5.4-.9.9-.9h6.8a.9.9 0 1 1 0 1.8H8.9c-.5 0-.9-.4-.9-.9Zm0 3c0-.5.4-.9.9-.9h6.8a.9.9 0 1 1 0 1.8H8.9c-.5 0-.9-.4-.9-.9Zm0 3c0-.5.4-.9.9-.9h4.6a.9.9 0 1 1 0 1.8H8.9c-.5 0-.9-.4-.9-.9Z"/>
</svg>
""".strip()

ICON_API = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
  <path fill="currentColor" d="M6 6.5A3.5 3.5 0 0 1 9.5 3h5A3.5 3.5 0 0 1 18 6.5v11A3.5 3.5 0 0 1 14.5 21h-5A3.5 3.5 0 0 1 6 17.5v-11Z"/>
  <path fill="rgba(255,255,255,0.22)" d="M9.2 9.3a.9.9 0 0 1 1.27 0l.9.9.9-.9a.9.9 0 0 1 1.27 1.27l-.9.9.9.9a.9.9 0 0 1-1.27 1.27l-.9-.9-.9.9a.9.9 0 0 1-1.27-1.27l.9-.9-.9-.9a.9.9 0 0 1 0-1.27Z"/>
</svg>
""".strip()
