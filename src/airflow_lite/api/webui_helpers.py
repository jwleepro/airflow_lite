"""공통 HTML 헬퍼, CSS, 레이아웃 셸.

webui_*.py 페이지 모듈들이 공유하는 유틸리티를 모아 놓은 모듈이다.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from airflow_lite.api.paths import (
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_PATH,
    MONITOR_ADMIN_PATH,
    PIPELINES_PATH,
)
from airflow_lite.i18n import DEFAULT_LANGUAGE, translate


# ---------------------------------------------------------------------------
# 포맷 / 상태 헬퍼
# ---------------------------------------------------------------------------

def fmt(value, fallback: str = "-") -> str:
    if value in (None, ""):
        return fallback
    return escape(str(value))


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


def status_tone(status: str | None) -> str:
    tone_map = {
        "success": "ok",
        "completed": "ok",
        "running": "warn",
        "pending": "warn",
        "queued": "warn",
        "failed": "bad",
    }
    return tone_map.get((status or "").lower(), "neutral")


def t(language: str, key: str, **kwargs) -> str:
    return translate(key, language, **kwargs)


def with_language_query(href: str, language: str) -> str:
    split = urlsplit(href)
    query_pairs = [(k, v) for k, v in parse_qsl(split.query, keep_blank_values=True) if k != "lang"]
    if language != DEFAULT_LANGUAGE:
        query_pairs.append(("lang", language))
    query_string = urlencode(query_pairs)
    return urlunsplit((split.scheme, split.netloc, split.path, query_string, split.fragment))


# ---------------------------------------------------------------------------
# 공통 위젯
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


def nav_link(label: str, href: str, active_path: str, *, language: str, icon_svg: str) -> str:
    active_class = " is-active" if urlsplit(href).path == active_path else ""
    aria_current = ' aria-current="page"' if active_class else ""
    return (
        f'<a class="side-link{active_class}" href="{escape(href)}"{aria_current}>'
        f'<span class="side-icon" aria-hidden="true">{icon_svg}</span>'
        f'<span class="side-label">{escape(label)}</span>'
        f"</a>"
    )


def link_group(links: list[tuple[str, str]] | None, *, language: str) -> str:
    if not links:
        return ""
    return "".join(
        f'<a class="utility-link" href="{escape(with_language_query(href, language))}" target="_blank" rel="noreferrer">{escape(label)}</a>'
        for label, href in links
    )


def summary_tile(label: str, value: str, detail: str, *, tone: str = "neutral") -> str:
    return f"""
    <article class="summary-tile {escape(tone)}">
      <p class="summary-label">{escape(label)}</p>
      <div class="summary-value">{escape(value)}</div>
      <p class="summary-detail">{escape(detail)}</p>
    </article>
    """


def cfg(webui_config, key: str, default):
    if webui_config is None:
        return default
    if isinstance(webui_config, dict):
        return webui_config.get(key, default)
    return getattr(webui_config, key, default)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
      /* Airflow-ish theme for the lightweight FastAPI Web UI.
         Goal: familiar IA (sidebar + topbar), strong status colors, and theme toggle (light/dark).
      */
      :root {
        color-scheme: light;
        --bg: #f5f7fb;
        --bg-2: #edf2f7;
        --surface: #ffffff;
        --surface-2: #f7fafc;
        --ink: #101828;
        --muted: #667085;
        --line: rgba(16, 24, 40, 0.12);
        --line-strong: rgba(16, 24, 40, 0.18);
        --shadow: 0 18px 55px rgba(16, 24, 40, 0.10);

        --primary: #017cee;
        --primary-2: #00a7e1;
        --primary-soft: rgba(1, 124, 238, 0.10);

        --ok: #12b76a;
        --warn: #f79009;
        --bad: #f04438;
        --neutral: #98a2b3;

        --sidebar: #0b1220;
        --sidebar-2: #0f1a2d;
        --sidebar-ink: rgba(255,255,255,0.92);
        --sidebar-muted: rgba(255,255,255,0.62);
        --sidebar-line: rgba(255,255,255,0.12);
        --focus: 0 0 0 3px rgba(1, 124, 238, 0.28);
      }
      :root[data-theme="dark"] {
        color-scheme: dark;
        --bg: #0b1220;
        --bg-2: #0f1a2d;
        --surface: #111c2f;
        --surface-2: #0f192b;
        --ink: rgba(255,255,255,0.92);
        --muted: rgba(255,255,255,0.62);
        --line: rgba(255,255,255,0.12);
        --line-strong: rgba(255,255,255,0.18);
        --shadow: 0 18px 70px rgba(0,0,0,0.55);
        --primary-soft: rgba(1, 124, 238, 0.22);
        --sidebar: #070c16;
        --sidebar-2: #0b1220;
        --sidebar-line: rgba(255,255,255,0.10);
        --focus: 0 0 0 3px rgba(90, 216, 255, 0.30);
      }

      * { box-sizing: border-box; }
      html, body { height: 100%; }
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", "Malgun Gothic", system-ui, sans-serif;
        color: var(--ink);
        background: radial-gradient(1200px 700px at 18% -10%, rgba(1,124,238,0.12), transparent 55%),
                    radial-gradient(900px 600px at 85% 0%, rgba(0,167,225,0.10), transparent 50%),
                    linear-gradient(180deg, var(--bg-2) 0%, var(--bg) 42%, var(--bg) 100%);
      }
      a { color: var(--primary); }
      a:hover { text-decoration: none; }
      code, pre { font-family: ui-monospace, "Cascadia Mono", "Consolas", monospace; }

      /* Shell */
      .app-shell { min-height: 100%; display: grid; grid-template-columns: 84px minmax(0, 1fr); }
      .sidebar {
        background: linear-gradient(180deg, var(--sidebar) 0%, var(--sidebar-2) 100%);
        border-right: 1px solid var(--sidebar-line);
        position: sticky;
        top: 0;
        height: 100vh;
        padding: 12px 10px 12px;
        display: grid;
        grid-template-rows: auto 1fr auto;
        gap: 10px;
      }
      .brand {
        display: grid;
        justify-items: center;
        gap: 8px;
        padding: 10px 6px;
        border-radius: 16px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.10);
      }
      .brand-mark {
        width: 18px;
        height: 18px;
        border-radius: 999px;
        background: conic-gradient(from 210deg, var(--primary), var(--primary-2), #5ad8ff, var(--primary));
        box-shadow: 0 0 0 6px rgba(90,216,255,0.14);
        flex: none;
      }
      .brand-copy { display: grid; gap: 2px; min-width: 0; text-align: center; }
      .brand-copy strong {
        color: var(--sidebar-ink);
        font-size: 0.70rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        line-height: 1.1;
      }
      .brand-copy span {
        color: rgba(255,255,255,0.44);
        font-size: 0.62rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        line-height: 1.1;
      }

      .side-section { display: grid; gap: 10px; }
      .side-nav { display: grid; gap: 6px; justify-items: stretch; }
      .side-link {
        display: grid;
        justify-items: center;
        gap: 6px;
        padding: 10px 8px;
        border-radius: 16px;
        color: var(--sidebar-muted);
        text-decoration: none;
        border: 1px solid transparent;
      }
      .side-link:hover {
        color: var(--sidebar-ink);
        background: rgba(255,255,255,0.06);
        border-color: rgba(255,255,255,0.10);
      }
      .side-link:focus { outline: none; box-shadow: var(--focus); }
      .side-link.is-active {
        color: var(--sidebar-ink);
        background: linear-gradient(135deg, rgba(1,124,238,0.24), rgba(0,167,225,0.10));
        border-color: rgba(90,216,255,0.20);
      }
      .side-icon { color: rgba(255,255,255,0.78); }
      .side-link.is-active .side-icon { color: rgba(255,255,255,0.95); }
      .side-icon svg { display: block; }
      .side-label {
        font-weight: 800;
        font-size: 0.70rem;
        line-height: 1.05;
        text-align: center;
      }

      .sidebar-footer { display: grid; gap: 6px; padding: 0 2px; }
      .side-util {
        display: grid;
        justify-items: center;
        gap: 6px;
        padding: 10px 8px;
        border-radius: 16px;
        color: rgba(255,255,255,0.70);
        text-decoration: none;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.05);
      }
      .side-util:hover { color: rgba(255,255,255,0.92); border-color: rgba(255,255,255,0.18); }
      .side-util:focus { outline: none; box-shadow: var(--focus); }
      .side-util span { font-size: 0.70rem; font-weight: 800; text-align: center; line-height: 1.05; }

      .main { padding: 18px 20px 44px; }
      .main-inner { max-width: 1400px; margin: 0 auto; }

      /* Topbar */
      .topbar {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: start;
        gap: 16px;
        padding: 18px 18px;
        border-radius: 18px;
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--line);
        box-shadow: var(--shadow);
        backdrop-filter: blur(10px);
      }
      :root[data-theme="dark"] .topbar { background: rgba(17, 28, 47, 0.72); }

      .page-kicker {
        margin: 0;
        color: var(--muted);
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
      .page-title {
        margin: 10px 0 0;
        font-size: clamp(1.6rem, 3.2vw, 2.6rem);
        line-height: 1.05;
        letter-spacing: -0.02em;
      }
      .page-subtitle { margin: 10px 0 0; color: var(--muted); max-width: 980px; }
      .top-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }

      /* Buttons / Inputs */
      button, .button-link, .utility-link {
        appearance: none;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--surface);
        color: var(--ink);
        padding: 9px 12px;
        font-weight: 700;
        cursor: pointer;
        text-decoration: none;
      }
      button:hover, .button-link:hover, .utility-link:hover { border-color: var(--line-strong); }
      button:focus, .button-link:focus, .utility-link:focus { outline: none; box-shadow: var(--focus); }
      button.primary {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-2) 100%);
        color: #fff;
        border-color: rgba(255,255,255,0.0);
      }
      .icon-button { padding: 9px 10px; min-width: 44px; display: inline-flex; justify-content: center; align-items: center; }
      .btn-delete { border-color: rgba(240, 68, 56, 0.35); color: var(--bad); background: rgba(240, 68, 56, 0.06); }
      .btn-delete:hover { border-color: rgba(240, 68, 56, 0.55); background: rgba(240, 68, 56, 0.10); }

      input, textarea, select {
        width: 100%;
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: var(--surface);
        color: var(--ink);
      }
      input:focus, textarea:focus, select:focus { outline: none; box-shadow: var(--focus); }
      textarea { resize: vertical; }

      /* Cards / Panels */
      .panel, .subpanel, .summary-tile {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 16px;
        box-shadow: var(--shadow);
      }
      .panel { padding: 18px 20px; }
      .subpanel, .summary-tile { padding: 16px 18px; }
      .stack, .section-list, .filter-form, .dense-cell, .brand-copy { display: grid; }
      .stack, .section-list, .filter-form, .dense-cell { gap: 14px; }
      .filter-field { display: grid; gap: 6px; }
      .grid-2 { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.85fr); gap: 16px; }
      .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }

      .panel-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 14px; }
      h2 { margin: 0; font-size: 1.15rem; letter-spacing: -0.01em; }
      .muted { color: var(--muted); }
      .eyebrow, th, dt {
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.10em;
        text-transform: uppercase;
      }
      .refresh-notice { font-size: 0.78rem; color: var(--muted); }

      /* Summary tiles */
      .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
      .summary-label { margin: 0; }
      .summary-value { font-size: 1.7rem; font-weight: 900; letter-spacing: -0.02em; margin-top: 10px; }
      .summary-detail { margin: 10px 0 0; color: var(--muted); font-size: 0.92rem; }
      .summary-tile.ok { border-color: rgba(18, 183, 106, 0.26); box-shadow: 0 18px 55px rgba(18, 183, 106, 0.08); }
      .summary-tile.warn { border-color: rgba(247, 144, 9, 0.28); box-shadow: 0 18px 55px rgba(247, 144, 9, 0.08); }
      .summary-tile.bad { border-color: rgba(240, 68, 56, 0.26); box-shadow: 0 18px 55px rgba(240, 68, 56, 0.08); }

      /* Chips / Status */
      .chip-list { display: flex; flex-wrap: wrap; gap: 10px; }
      .chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        border: 1px solid var(--line);
        background: var(--surface-2);
        font-size: 0.82rem;
        font-weight: 800;
      }
      .chip::before { content: ""; width: 6px; height: 6px; border-radius: 999px; background: var(--primary); }
      .status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.80rem;
        font-weight: 900;
        text-transform: capitalize;
        white-space: nowrap;
        background: rgba(152, 162, 179, 0.14);
        color: var(--neutral);
        border: 1px solid var(--line);
      }
      .status::before { content: ""; width: 8px; height: 8px; border-radius: 999px; background: currentColor; }
      .status.ok { background: rgba(18, 183, 106, 0.14); color: var(--ok); border-color: rgba(18, 183, 106, 0.20); }
      .status.warn { background: rgba(247, 144, 9, 0.18); color: var(--warn); border-color: rgba(247, 144, 9, 0.22); }
      .status.bad { background: rgba(240, 68, 56, 0.14); color: var(--bad); border-color: rgba(240, 68, 56, 0.22); }
      .status.warn.pulse::before { animation: pulse 1.2s ease-in-out infinite; }
      @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

      /* Tables */
      .table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 14px; background: var(--surface); }
      table { width: 100%; border-collapse: collapse; min-width: 720px; }
      th, td { padding: 11px 12px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
      th { background: var(--surface-2); }
      tbody tr:hover { background: rgba(1, 124, 238, 0.05); }
      tbody tr:last-child td { border-bottom: none; }
      .dense-cell span { color: var(--muted); font-size: 0.88rem; }
      .error-inline { font-size: 0.80rem; color: var(--bad); word-break: break-word; max-width: 420px; margin-top: 6px; }

      /* Meta grid */
      .meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
      .meta-grid div { padding: 12px 14px; background: var(--surface-2); border: 1px solid var(--line); border-radius: 14px; }
      dd { margin: 0; font-weight: 900; }

      /* Filters / Actions */
      .filter-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
      .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
      .inline-form { display: inline-flex; }

      /* Chart */
      .chart-list { display: grid; gap: 10px; }
      .chart-row { display: grid; grid-template-columns: minmax(120px, 200px) minmax(0, 1fr) auto; gap: 12px; align-items: center; }
      .chart-bar { height: 10px; border-radius: 999px; background: var(--primary-soft); overflow: hidden; border: 1px solid var(--line); }
      .chart-bar span { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--primary-2), var(--primary)); }

      /* Run Status Grid (Airflow-style signal) */
      .run-grid { display: flex; gap: 3px; align-items: center; flex-wrap: nowrap; }
      .run-block { width: 14px; height: 14px; border-radius: 4px; flex-shrink: 0; background: var(--line-strong); cursor: default; transition: transform 0.10s ease; }
      .run-block:hover { transform: scale(1.35); z-index: 1; }
      .run-block.ok { background: var(--ok); }
      .run-block.warn { background: var(--warn); }
      .run-block.bad { background: var(--bad); }
      .run-block.neutral { background: var(--neutral); }
      .run-grid-empty { color: var(--muted); font-size: 0.82rem; }

      /* Step Gantt chart */
      .gantt-table { width: 100%; border-collapse: collapse; }
      .gantt-table th, .gantt-table td { padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: middle; }
      .gantt-track { position: relative; height: 18px; background: var(--bg-2); border-radius: 6px; min-width: 160px; border: 1px solid var(--line); }
      .gantt-bar { position: absolute; top: 0; height: 100%; border-radius: 6px; min-width: 3px; }
      .gantt-bar.ok { background: rgba(18, 183, 106, 0.60); }
      .gantt-bar.warn { background: rgba(247, 144, 9, 0.60); }
      .gantt-bar.bad { background: rgba(240, 68, 56, 0.60); }
      .gantt-bar.neutral { background: rgba(152, 162, 179, 0.50); }
      .step-error { font-size: 0.78rem; color: var(--bad); margin-top: 4px; word-break: break-word; }

      .empty, .empty-page { color: var(--muted); }
      .highlight { box-shadow: inset 3px 0 0 var(--primary); background: rgba(1,124,238,0.06); }

      @media (max-width: 1080px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
      @media (max-width: 980px) {
        .app-shell { grid-template-columns: 1fr; }
        .sidebar { position: relative; height: auto; }
        .main { padding: 14px 14px 34px; }
        .topbar { grid-template-columns: 1fr; }
        .top-actions { justify-content: flex-start; }
      }
"""


# ---------------------------------------------------------------------------
# 레이아웃 셸
# ---------------------------------------------------------------------------

def render_layout(
    *,
    title: str,
    subtitle: str,
    active_path: str,
    content_html: str,
    hero_links: list[tuple[str, str]] | None = None,
    page_tag: str | None = None,
    auto_refresh_seconds: int | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    hero_links_html = link_group(hero_links, language=language)
    page_tag_text = page_tag or t(language, "webui.layout.page_tag.operations_console")
    docs_href = with_language_query("/docs", language)
    pipelines_api_href = with_language_query(PIPELINES_PATH, language)
    refresh_meta = (
        f'<meta http-equiv="refresh" content="{auto_refresh_seconds}">'
        if auto_refresh_seconds
        else ""
    )
    return f"""<!doctype html>
<html lang="{escape(language)}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {refresh_meta}
    <title>{escape(title)}</title>
    <style>{CSS}</style>
    <script>
      (function() {{
        try {{
          var saved = localStorage.getItem("airflow_lite_theme");
          if (saved === "dark" || saved === "light") {{
            document.documentElement.setAttribute("data-theme", saved);
            return;
          }}
          var prefersDark = false;
          try {{
            prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
          }} catch (e) {{}}
          document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
        }} catch (e) {{}}
      }})();
    </script>
  </head>
  <body>
    <div class="app-shell">
      <aside class="sidebar" aria-label="{escape(t(language, "webui.layout.header_tag.ops_console"))}">
        <div class="brand" role="banner">
          <div class="brand-mark" aria-hidden="true"></div>
          <div class="brand-copy">
            <strong>Airflow Lite</strong>
            <span>{escape(t(language, "webui.layout.brand_subtitle"))}</span>
          </div>
        </div>

        <div class="side-section">
          <nav class="side-nav" aria-label="Primary">
            {nav_link(t(language, "webui.layout.nav.pipelines"), with_language_query(MONITOR_PATH, language), active_path, language=language, icon_svg=ICON_PIPELINES)}
            {nav_link(t(language, "webui.layout.nav.analytics"), with_language_query(MONITOR_ANALYTICS_PATH, language), active_path, language=language, icon_svg=ICON_ANALYTICS)}
            {nav_link(t(language, "webui.layout.nav.exports"), with_language_query(MONITOR_EXPORTS_PATH, language), active_path, language=language, icon_svg=ICON_EXPORTS)}
            {nav_link(t(language, "webui.layout.nav.admin"), with_language_query(MONITOR_ADMIN_PATH, language), active_path, language=language, icon_svg=ICON_ADMIN)}
          </nav>
        </div>

        <div></div>

        <div class="sidebar-footer" aria-label="Utilities">
          <a class="side-util" href="{escape(docs_href)}" target="_blank" rel="noreferrer">
            <span aria-hidden="true">{ICON_DOCS}</span><span>{escape(t(language, "webui.layout.link.swagger"))}</span>
          </a>
          <a class="side-util" href="{escape(pipelines_api_href)}" target="_blank" rel="noreferrer">
            <span aria-hidden="true">{ICON_API}</span><span>{escape(t(language, "webui.layout.link.pipeline_api"))}</span>
          </a>
        </div>
      </aside>

      <main class="main">
        <div class="main-inner">
          <section class="topbar">
            <div>
              <p class="page-kicker">{escape(page_tag_text)}</p>
              <h1 class="page-title">{escape(title)}</h1>
              <p class="page-subtitle">{escape(subtitle)}</p>
            </div>
            <div class="top-actions">
              {hero_links_html}
              <button id="theme-toggle" class="icon-button" type="button" title="Toggle theme" aria-label="Toggle theme"></button>
            </div>
          </section>

          <div class="stack">{content_html}</div>
        </div>
      </main>
    </div>

    <script>
      (function() {{
        var SUN = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12 17.3a5.3 5.3 0 1 1 0-10.6 5.3 5.3 0 0 1 0 10.6Zm0-14.3a.9.9 0 0 1 .9.9v1.1a.9.9 0 0 1-1.8 0V3.9c0-.5.4-.9.9-.9Zm0 18a.9.9 0 0 1 .9.9v1.1a.9.9 0 0 1-1.8 0v-1.1c0-.5.4-.9.9-.9ZM3.9 11.1H5a.9.9 0 0 1 0 1.8H3.9a.9.9 0 0 1 0-1.8Zm15.1 0h1.1a.9.9 0 0 1 0 1.8H19a.9.9 0 0 1 0-1.8ZM6.2 5.0a.9.9 0 0 1 1.3 0l.8.8A.9.9 0 1 1 7 7.1l-.8-.8a.9.9 0 0 1 0-1.3Zm10.5 10.5a.9.9 0 0 1 1.3 0l.8.8a.9.9 0 0 1-1.3 1.3l-.8-.8a.9.9 0 0 1 0-1.3ZM18.0 5.0a.9.9 0 0 1 0 1.3l-.8.8a.9.9 0 0 1-1.3-1.3l.8-.8a.9.9 0 0 1 1.3 0ZM7.1 15.9a.9.9 0 0 1 0 1.3l-.8.8A.9.9 0 1 1 5 16.7l.8-.8a.9.9 0 0 1 1.3 0Z"/></svg>';
        var MOON = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path fill="currentColor" d="M21 14.3a8.2 8.2 0 0 1-11.3 5.9A8.3 8.3 0 0 1 4 12.2 8.2 8.2 0 0 1 12.4 3c.5 0 .8.5.6 1A6.7 6.7 0 0 0 20 12.9c.5-.2 1 .2 1 .7Z"/></svg>';
        function currentTheme() {{
          return document.documentElement.getAttribute("data-theme") || "light";
        }}
        function setTheme(theme) {{
          document.documentElement.setAttribute("data-theme", theme);
          try {{ localStorage.setItem("airflow_lite_theme", theme); }} catch (e) {{}}
        }}
        function renderButton(btn) {{
          var theme = currentTheme();
          btn.innerHTML = theme === "dark" ? SUN : MOON;
          btn.title = theme === "dark" ? "Switch to light" : "Switch to dark";
        }}
        var btn = document.getElementById("theme-toggle");
        if (btn) {{
          renderButton(btn);
          btn.addEventListener("click", function() {{
            setTheme(currentTheme() === "dark" ? "light" : "dark");
            renderButton(btn);
          }});
        }}
      }})();
    </script>
  </body>
</html>
"""
