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

def nav_link(label: str, href: str, active_path: str, *, language: str) -> str:
    active_class = " active" if urlsplit(href).path == active_path else ""
    return f'<a class="nav-link{active_class}" href="{escape(href)}">{escape(label)}</a>'


def link_group(links: list[tuple[str, str]] | None, *, language: str) -> str:
    if not links:
        return ""
    return "".join(
        f'<a href="{escape(with_language_query(href, language))}" target="_blank" rel="noreferrer">{escape(label)}</a>'
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
      :root {
        color-scheme: light; --bg:#f4f7fb; --bg-strong:#e9eef6; --panel:#fff; --panel-soft:#f8fbff;
        --ink:#1f2937; --muted:#667085; --line:#d6deea; --line-strong:#bfcade; --topbar:#12263f;
        --topbar-strong:#0d1c30; --brand:#00a7e1; --accent:#017cee; --accent-soft:rgba(1,124,238,.08);
        --ok:#0f9d58; --warn:#f79009; --bad:#d92d20; --neutral:#7a8699; --shadow:0 12px 34px rgba(15,23,42,.08);
      }
      * { box-sizing:border-box; } body { margin:0; font-family:"Segoe UI","Malgun Gothic",sans-serif; color:var(--ink);
        background:linear-gradient(180deg,var(--bg-strong) 0,var(--bg) 200px,var(--bg) 100%); }
      a { color:var(--accent); }
      .masthead { color:#fff; border-bottom:1px solid rgba(255,255,255,.08);
        background:linear-gradient(135deg,rgba(0,167,225,.16),transparent 28%),linear-gradient(180deg,var(--topbar) 0,var(--topbar-strong) 100%); }
      .masthead-shell,.page-shell { max-width:1400px; margin:0 auto; padding-left:20px; padding-right:20px; }
      .masthead-shell { padding-top:18px; padding-bottom:18px; } .page-shell { padding-top:20px; padding-bottom:40px; }
      .utility-bar,.nav-row,.header-card-row,.panel-head { display:flex; justify-content:space-between; gap:16px; }
      .utility-bar,.header-card-row { align-items:center; } .nav-row,.panel-head { align-items:flex-start; }
      .brand-lockup { display:flex; align-items:center; gap:12px; } .brand-mark { width:12px; height:12px; border-radius:999px;
        background:linear-gradient(135deg,#00a7e1,#5ad8ff); box-shadow:0 0 0 5px rgba(90,216,255,.16); }
      .brand-copy { display:grid; gap:2px; } .brand-copy strong { font-size:.98rem; letter-spacing:.04em; text-transform:uppercase; }
      .brand-copy span,.page-kicker { color:rgba(255,255,255,.68); font-size:.76rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; }
      .utility-links,.header-links,.nav-tabs,.actions,.chip-list { display:flex; flex-wrap:wrap; gap:10px; } .nav-tabs { gap:4px; align-self:stretch; }
      .utility-links a,.header-links a,.button-link,button { text-decoration:none; padding:9px 14px; border-radius:10px; border:1px solid transparent; font-weight:600; cursor:pointer; }
      .utility-links a { color:rgba(255,255,255,.88); background:rgba(255,255,255,.08); border-color:rgba(255,255,255,.12); }
      .page-title { margin:0; font-size:clamp(1.8rem,4vw,2.8rem); line-height:1; } .page-subtitle { margin:10px 0 0; max-width:860px; color:rgba(255,255,255,.72); }
      .nav-link { color:rgba(255,255,255,.68); text-decoration:none; padding:14px 16px 12px; border-bottom:3px solid transparent; font-weight:700; }
      .nav-link.active { color:#fff; border-bottom-color:var(--brand); }
      .header-card,.panel,.subpanel,.summary-tile { background:var(--panel); border:1px solid var(--line); border-radius:16px; box-shadow:var(--shadow); }
      .header-card,.panel { padding:18px 20px; } .subpanel,.summary-tile { padding:16px 18px; }
      .header-tag,.chip { display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px; font-size:.82rem; font-weight:700; }
      .header-tag { background:var(--accent-soft); color:var(--accent); text-transform:uppercase; } .chip { background:var(--accent-soft); color:var(--accent); }
      .header-links a,.button-link,button { color:var(--accent); background:var(--panel-soft); border-color:var(--line); } button.primary { color:#fff; background:var(--accent); border-color:var(--accent); }
      .btn-delete { color:#d32f2f; background:#fff5f5; border:1px solid #d32f2f; padding:4px 10px; border-radius:6px; font-size:.78rem; cursor:pointer; font-weight:600; } .btn-delete:hover { background:#ffebee; }
      .stack,.section-list,.filter-form,.dense-cell,.brand-copy { display:grid; }
      .stack,.section-list,.filter-form,.dense-cell { gap:14px; }
      .filter-field { display:grid; gap:6px; }
      .grid-2 { display:grid; grid-template-columns:minmax(0,1.35fr) minmax(320px,.85fr); gap:16px; }
      .grid-3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
      .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; }
      .summary-tile { border-top:4px solid var(--line-strong); }
      .summary-tile.ok { border-top-color:var(--ok); } .summary-tile.warn { border-top-color:var(--warn); }
      .summary-tile.bad { border-top-color:var(--bad); } .summary-tile.neutral { border-top-color:var(--neutral); }
      .summary-label { color:var(--muted); font-size:.76rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; }
      .summary-value { margin-top:12px; font-size:clamp(1.5rem,3vw,2.25rem); font-weight:800; line-height:1; }
      .summary-detail,.muted { margin:8px 0 0; color:var(--muted); font-size:.92rem; }
      .dense-cell span { color:var(--muted); font-size:.88rem; } h2 { margin:0; font-size:1.2rem; }
      .eyebrow,th,dt { color:var(--muted); font-size:.76rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; }
      .meta-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }
      .meta-grid div { padding:12px 14px; background:var(--panel-soft); border:1px solid var(--line); border-radius:12px; }
      dd { margin:0; font-weight:700; }
      .status { display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px; font-size:.8rem; font-weight:700; text-transform:capitalize; white-space:nowrap; background:rgba(122,134,153,.12); color:var(--neutral); }
      .status::before,.chip::before { content:""; border-radius:999px; background:currentColor; }
      .status::before { width:8px; height:8px; } .chip::before { width:6px; height:6px; }
      .status.ok { background:rgba(15,157,88,.12); color:var(--ok); }
      .status.warn { background:rgba(247,144,9,.16); color:var(--warn); }
      .status.bad { background:rgba(217,45,32,.12); color:var(--bad); }
      .status.warn.pulse::before { animation:pulse 1.2s ease-in-out infinite; }
      @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.3; } }
      .table-wrap { overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:#fff; }
      table { width:100%; border-collapse:collapse; min-width:720px; } th,td { padding:11px 12px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; }
      th { background:#f9fbfd; } tbody tr:hover { background:rgba(1,124,238,.03); } tbody tr:last-child td { border-bottom:none; }
      .dense-cell strong { font-size:.95rem; } .filter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }
      select { width:100%; padding:10px 12px; border-radius:10px; border:1px solid var(--line); background:#fff; color:var(--ink); }
      .chart-list { display:grid; gap:10px; }
      .chart-row { display:grid; grid-template-columns:minmax(120px,200px) minmax(0,1fr) auto; gap:12px; align-items:center; }
      .chart-bar { height:10px; border-radius:999px; background:rgba(1,124,238,.12); overflow:hidden; }
      .chart-bar span { display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,#00a7e1,#017cee); }
      .inline-form { display:inline-flex; } .highlight { box-shadow:inset 3px 0 0 var(--accent); background:rgba(1,124,238,.04); }
      .empty,.empty-page { color:var(--muted); }
      /* Run Status Grid (Airflow 스타일) */
      .run-grid { display:flex; gap:3px; align-items:center; flex-wrap:nowrap; }
      .run-block { width:14px; height:14px; border-radius:3px; flex-shrink:0; background:var(--line-strong); cursor:default; transition:transform .1s; }
      .run-block:hover { transform:scale(1.35); z-index:1; }
      .run-block.ok { background:var(--ok); } .run-block.warn { background:var(--warn); }
      .run-block.bad { background:var(--bad); } .run-block.neutral { background:var(--neutral); }
      .run-grid-empty { color:var(--muted); font-size:.82rem; }
      /* Error inline */
      .error-inline { font-size:.8rem; color:var(--bad); word-break:break-word; max-width:360px; margin-top:4px; }
      /* Auto-refresh 표시 */
      .refresh-notice { font-size:.78rem; color:var(--muted); }
      /* Step Gantt chart */
      .gantt-table { width:100%; border-collapse:collapse; }
      .gantt-table th,.gantt-table td { padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:middle; }
      .gantt-table th { background:#f9fbfd; }
      .gantt-table tbody tr:last-child td { border-bottom:none; }
      .gantt-track { position:relative; height:18px; background:var(--bg-strong); border-radius:4px; min-width:160px; }
      .gantt-bar { position:absolute; top:0; height:100%; border-radius:4px; min-width:3px; }
      .gantt-bar.ok { background:rgba(15,157,88,.6); } .gantt-bar.warn { background:rgba(247,144,9,.6); }
      .gantt-bar.bad { background:rgba(217,45,32,.6); } .gantt-bar.neutral { background:rgba(122,134,153,.4); }
      .step-error { font-size:.78rem; color:var(--bad); margin-top:4px; word-break:break-word; }
      @media (max-width:1080px) { .grid-2,.grid-3 { grid-template-columns:1fr; } }
      @media (max-width:760px) {
        .masthead-shell,.page-shell { padding-left:14px; padding-right:14px; }
        .utility-bar,.nav-row,.header-card-row,.panel-head { flex-direction:column; align-items:flex-start; }
        .chart-row { grid-template-columns:1fr; } .header-card,.panel,.subpanel { padding:16px; }
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
  </head>
  <body>
    <header class="masthead">
      <div class="masthead-shell">
        <div class="utility-bar">
          <div class="brand-lockup">
            <div class="brand-mark"></div>
            <div class="brand-copy">
              <strong>Airflow Lite</strong>
              <span>{escape(t(language, "webui.layout.brand_subtitle"))}</span>
            </div>
          </div>
          <div class="utility-links">
            <a href="{escape(docs_href)}" target="_blank" rel="noreferrer">{escape(t(language, "webui.layout.link.swagger"))}</a>
            <a href="{escape(pipelines_api_href)}" target="_blank" rel="noreferrer">{escape(t(language, "webui.layout.link.pipeline_api"))}</a>
          </div>
        </div>
        <div class="nav-row" style="margin-top:18px;">
          <div>
            <p class="page-kicker">{escape(page_tag_text)}</p>
            <h1 class="page-title">{escape(title)}</h1>
            <p class="page-subtitle">{escape(subtitle)}</p>
          </div>
          <nav class="nav-tabs">
            {nav_link(t(language, "webui.layout.nav.pipelines"), with_language_query(MONITOR_PATH, language), active_path, language=language)}
            {nav_link(t(language, "webui.layout.nav.analytics"), with_language_query(MONITOR_ANALYTICS_PATH, language), active_path, language=language)}
            {nav_link(t(language, "webui.layout.nav.exports"), with_language_query(MONITOR_EXPORTS_PATH, language), active_path, language=language)}
            {nav_link(t(language, "webui.layout.nav.admin"), with_language_query(MONITOR_ADMIN_PATH, language), active_path, language=language)}
          </nav>
        </div>
      </div>
    </header>
    <main class="page-shell">
      <section class="header-card">
        <div class="header-card-row">
          <span class="header-tag">{escape(t(language, "webui.layout.header_tag.ops_console"))}</span>
          <div class="header-links">{hero_links_html}</div>
        </div>
      </section>
      <div class="stack" style="margin-top:16px;">{content_html}</div>
    </main>
  </body>
</html>
"""
