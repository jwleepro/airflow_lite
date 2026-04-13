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
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4.75 12.25h14.5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
  <path d="M7.5 5.75h8.75" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
  <path d="M7.5 18.75h8.75" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
  <circle cx="6.5" cy="5.75" r="1.25" fill="currentColor"/>
  <circle cx="17.5" cy="12.25" r="1.25" fill="currentColor"/>
  <circle cx="6.5" cy="18.75" r="1.25" fill="currentColor"/>
</svg>
""".strip()

ICON_ANALYTICS = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4.75 8.5c0-1.52 1.23-2.75 2.75-2.75h9a2.75 2.75 0 0 1 2.75 2.75v7a2.75 2.75 0 0 1-2.75 2.75h-9a2.75 2.75 0 0 1-2.75-2.75v-7Z" stroke="currentColor" stroke-width="1.75"/>
  <path d="M8 12h2.5M13.5 12H16" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
  <path d="M9 15.5 12 8.5l3 7" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""".strip()

ICON_ADMIN = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 15.25a3.25 3.25 0 1 0 0-6.5 3.25 3.25 0 0 0 0 6.5Z" stroke="currentColor" stroke-width="1.75"/>
  <path d="M19 12a7 7 0 0 0-.08-1.02l1.52-1.18-1.45-2.51-1.86.6a7.24 7.24 0 0 0-1.77-1.02l-.33-1.95h-2.9l-.33 1.95c-.63.21-1.22.54-1.77 1.02l-1.86-.6L3.56 9.8l1.52 1.18A7 7 0 0 0 5 12c0 .35.03.69.08 1.02L3.56 14.2l1.45 2.51 1.86-.6c.55.48 1.14.81 1.77 1.02l.33 1.95h2.9l.33-1.95c.63-.21 1.22-.54 1.77-1.02l1.86.6 1.45-2.51-1.52-1.18c.05-.33.08-.67.08-1.02Z" stroke="currentColor" stroke-width="1.45" stroke-linejoin="round"/>
</svg>
""".strip()

ICON_DOCS = """
<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M7.25 5.25h7.5a2.5 2.5 0 0 1 2.5 2.5v10.5H8.5a2.25 2.25 0 0 0-2.25 2.25V7.5a2.25 2.25 0 0 1 2.25-2.25Z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
  <path d="M8.75 9h6M8.75 12h6M8.75 15h3.5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
</svg>
""".strip()
