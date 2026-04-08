"""서버 사이드 HTML 렌더링 모듈 — Airflow-inspired operations console.

개선 사항 (Airflow 패턴 적용):
- Run Status Grid: 파이프라인별 최근 25건 색상 블록 (Airflow DAG list 스타일)
- Auto-refresh: 페이지별 meta refresh (Monitor 30s / Analytics 60s / Exports 10-30s)
- Duration 컬럼: started_at~finished_at 차이를 "2m 30s" 형식으로 표시
- Next Run: 다음 예정 실행 시각 (web.py에서 APScheduler로 계산)
- Error Summary: 실패 step의 error_message 인라인 표시
- Step Timeline: Gantt 스타일 step 실행 타임라인 상세 페이지
- Running 애니메이션: export/pipeline running 상태 pulse 배지
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from airflow_lite.api.paths import (
    ANALYTICS_EXPORTS_PATH,
    ANALYTICS_FILTERS_PATH,
    MONITOR_ANALYTICS_PATH,
    MONITOR_EXPORTS_PATH,
    MONITOR_EXPORT_DELETE_COMPLETED_PATH,
    MONITOR_EXPORT_DELETE_JOB_PATH,
    MONITOR_PATH,
    PIPELINES_PATH,
    dashboard_definition_path,
    monitor_pipeline_run_detail_path,
    pipeline_run_detail_path,
    pipeline_runs_path,
)
from airflow_lite.i18n import DEFAULT_LANGUAGE, translate


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _fmt(value, fallback: str = "-") -> str:
    if value in (None, ""):
        return fallback
    return escape(str(value))


def _fmt_duration(started_at: str | None, finished_at: str | None) -> str:
    """두 ISO 타임스탬프 차이를 '2m 30s' 형식으로 반환. finished_at이 없으면 현재 시각까지 계산."""
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


def _status_tone(status: str | None) -> str:
    tone_map = {
        "success": "ok",
        "completed": "ok",
        "running": "warn",
        "pending": "warn",
        "queued": "warn",
        "failed": "bad",
    }
    return tone_map.get((status or "").lower(), "neutral")


def _t(language: str, key: str, **kwargs) -> str:
    return translate(key, language, **kwargs)


def _with_language_query(href: str, language: str) -> str:
    split = urlsplit(href)
    query_pairs = [(k, v) for k, v in parse_qsl(split.query, keep_blank_values=True) if k != "lang"]
    if language != DEFAULT_LANGUAGE:
        query_pairs.append(("lang", language))
    query_string = urlencode(query_pairs)
    return urlunsplit((split.scheme, split.netloc, split.path, query_string, split.fragment))


def _nav_link(label: str, href: str, active_path: str, *, language: str) -> str:
    active_class = " active" if urlsplit(href).path == active_path else ""
    return f'<a class="nav-link{active_class}" href="{escape(href)}">{escape(label)}</a>'


def _link_group(links: list[tuple[str, str]] | None, *, language: str) -> str:
    if not links:
        return ""
    return "".join(
        f'<a href="{escape(_with_language_query(href, language))}" target="_blank" rel="noreferrer">{escape(label)}</a>'
        for label, href in links
    )


def _summary_tile(label: str, value: str, detail: str, *, tone: str = "neutral") -> str:
    return f"""
    <article class="summary-tile {escape(tone)}">
      <p class="summary-label">{escape(label)}</p>
      <div class="summary-value">{escape(value)}</div>
      <p class="summary-detail">{escape(detail)}</p>
    </article>
    """


def _run_status_block(status: str | None, *, language: str, title: str = "") -> str:
    """단일 실행 상태 블록 (Airflow DAG list 그리드 셀)."""
    tone = _status_tone(status or "")
    tip = escape(title) if title else escape(status or _t(language, "webui.run.no_run"))
    return f'<span class="run-block {tone}" title="{tip}"></span>'


def _run_status_grid(runs: list[dict], *, language: str) -> str:
    """최근 실행 색상 블록 그리드 (오래된 것 왼쪽, 최신 오른쪽)."""
    if not runs:
        return f'<span class="run-grid-empty">{escape(_t(language, "webui.run.no_run"))}</span>'
    blocks = "".join(
        _run_status_block(
            run.get("status"),
            language=language,
            title=f"{run.get('execution_date', '')} · {run.get('status', '')}",
        )
        for run in reversed(runs)
    )
    return f'<div class="run-grid">{blocks}</div>'


def _cfg(webui_config, key: str, default):
    if webui_config is None:
        return default
    if isinstance(webui_config, dict):
        return webui_config.get(key, default)
    return getattr(webui_config, key, default)


def _first_failed_step_error(run: dict, *, max_length: int = 120) -> str | None:
    """실행 결과에서 첫 번째 실패 step의 error_message 반환."""
    for step in run.get("steps", []):
        if step.get("status") == "failed" and step.get("error_message"):
            name = step.get("step_name", "")
            msg = str(step["error_message"])
            if len(msg) > max_length:
                msg = msg[:max_length] + "…"
            return f"[{name}] {msg}"
    return None


# ---------------------------------------------------------------------------
# 공통 레이아웃
# ---------------------------------------------------------------------------

_CSS = """
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


def _render_layout(
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
    hero_links_html = _link_group(hero_links, language=language)
    page_tag_text = page_tag or _t(language, "webui.layout.page_tag.operations_console")
    docs_href = _with_language_query("/docs", language)
    pipelines_api_href = _with_language_query(PIPELINES_PATH, language)
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
    <style>{_CSS}</style>
  </head>
  <body>
    <header class="masthead">
      <div class="masthead-shell">
        <div class="utility-bar">
          <div class="brand-lockup">
            <div class="brand-mark"></div>
            <div class="brand-copy">
              <strong>Airflow Lite</strong>
              <span>{escape(_t(language, "webui.layout.brand_subtitle"))}</span>
            </div>
          </div>
          <div class="utility-links">
            <a href="{escape(docs_href)}" target="_blank" rel="noreferrer">{escape(_t(language, "webui.layout.link.swagger"))}</a>
            <a href="{escape(pipelines_api_href)}" target="_blank" rel="noreferrer">{escape(_t(language, "webui.layout.link.pipeline_api"))}</a>
          </div>
        </div>
        <div class="nav-row" style="margin-top:18px;">
          <div>
            <p class="page-kicker">{escape(page_tag_text)}</p>
            <h1 class="page-title">{escape(title)}</h1>
            <p class="page-subtitle">{escape(subtitle)}</p>
          </div>
          <nav class="nav-tabs">
            {_nav_link(_t(language, "webui.layout.nav.pipelines"), _with_language_query(MONITOR_PATH, language), active_path, language=language)}
            {_nav_link(_t(language, "webui.layout.nav.analytics"), _with_language_query(MONITOR_ANALYTICS_PATH, language), active_path, language=language)}
            {_nav_link(_t(language, "webui.layout.nav.exports"), _with_language_query(MONITOR_EXPORTS_PATH, language), active_path, language=language)}
          </nav>
        </div>
      </div>
    </header>
    <main class="page-shell">
      <section class="header-card">
        <div class="header-card-row">
          <span class="header-tag">{escape(_t(language, "webui.layout.header_tag.ops_console"))}</span>
          <div class="header-links">{hero_links_html}</div>
        </div>
      </section>
      <div class="stack" style="margin-top:16px;">{content_html}</div>
    </main>
  </body>
</html>
"""


# ---------------------------------------------------------------------------
# /monitor — Pipeline monitor page
# ---------------------------------------------------------------------------

def render_monitor_page(
    pipeline_rows: list[dict],
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """파이프라인 목록 + 최근 실행 상태 그리드 (Airflow DAG list 스타일).

    pipeline_rows 각 항목:
      name, table, strategy, schedule, next_run (str|None),
      latest_run (dict|None), recent_runs (list[dict], 최대 25건)
    """
    monitor_refresh_seconds = _cfg(webui_config, "monitor_refresh_seconds", 30)
    error_message_max_length = _cfg(webui_config, "error_message_max_length", 120)
    total_pipelines = len(pipeline_rows)
    active_runs = sum(
        1 for row in pipeline_rows
        if (row.get("latest_run") or {}).get("status", "").lower() in {"running", "queued", "pending"}
    )
    healthy_runs = sum(
        1 for row in pipeline_rows
        if (row.get("latest_run") or {}).get("status", "").lower() in {"success", "completed"}
    )
    failed_runs = sum(
        1 for row in pipeline_rows
        if (row.get("latest_run") or {}).get("status", "").lower() == "failed"
    )
    latest_finish = max(
        (
            row.get("latest_run", {}).get("finished_at")
            for row in pipeline_rows
            if row.get("latest_run", {}).get("finished_at")
        ),
        default=None,
    )

    summary_html = "".join([
        _summary_tile(
            _t(language, "webui.monitor.summary.configured_pipelines.label"),
            str(total_pipelines),
            _t(language, "webui.monitor.summary.configured_pipelines.detail"),
        ),
        _summary_tile(
            _t(language, "webui.monitor.summary.healthy_last_run.label"),
            str(healthy_runs),
            _t(language, "webui.monitor.summary.healthy_last_run.detail"),
            tone="ok",
        ),
        _summary_tile(
            _t(language, "webui.monitor.summary.active_runs.label"),
            str(active_runs),
            _t(language, "webui.monitor.summary.active_runs.detail"),
            tone="warn" if active_runs else "neutral",
        ),
        _summary_tile(
            _t(language, "webui.monitor.summary.failed_last_run.label"),
            str(failed_runs),
            _t(language, "webui.monitor.summary.failed_last_run.detail"),
            tone="bad" if failed_runs else "neutral",
        ),
    ])

    inventory_rows: list[str] = []
    for row in pipeline_rows:
        latest = row.get("latest_run") or {}
        latest_status = latest.get("status", "never-run")
        latest_status_tone = _status_tone(latest_status)
        recent_runs = row.get("recent_runs", [])
        next_run = row.get("next_run")
        duration = _fmt_duration(latest.get("started_at"), latest.get("finished_at"))
        run_id = latest.get("id", "")

        # 실패 시 첫 번째 실패 step error 인라인 표시
        error_html = ""
        if latest_status == "failed":
            err = _first_failed_step_error(latest, max_length=error_message_max_length)
            if err:
                error_html = f'<div class="error-inline">{escape(err)}</div>'

        # running/pending → pulse 애니메이션
        pulse_cls = " pulse" if latest_status in {"running", "queued", "pending"} else ""

        # 상세 링크 (run_id가 있을 때만)
        detail_link = (
            f'<a href="{escape(_with_language_query(monitor_pipeline_run_detail_path(row["name"], run_id), language))}">{escape(_t(language, "webui.monitor.detail_link"))}</a>'
            if run_id
            else "-"
        )

        inventory_rows.append(f"""
            <tr>
              <td>
                <div class="dense-cell">
                  <strong>{_fmt(row["name"])}</strong>
                  <span>{_fmt(row["table"])}</span>
                </div>
              </td>
              <td>{_run_status_grid(recent_runs, language=language)}</td>
              <td>
                <span class="status {latest_status_tone}{pulse_cls}">{_fmt(latest_status)}</span>
                {error_html}
              </td>
              <td>{_fmt(latest.get("trigger_type"))}</td>
              <td>{_fmt(duration)}</td>
              <td>{_fmt(latest.get("finished_at") or latest.get("started_at"))}</td>
              <td>{_fmt(next_run, fallback="—")}</td>
              <td>{_fmt(row["schedule"])}</td>
              <td>{detail_link}</td>
            </tr>
        """)

    inventory_html = (
        "".join(inventory_rows)
        or f'<tr><td colspan="9" class="empty">{escape(_t(language, "webui.monitor.empty.no_pipelines"))}</td></tr>'
    )

    monitor_notice = _t(
        language,
        "webui.monitor.inventory.refresh_notice",
        latest_finish=_fmt(latest_finish, fallback=_t(language, "webui.monitor.inventory.none")),
        seconds=monitor_refresh_seconds,
    )

    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">{escape(_t(language, "webui.monitor.inventory.eyebrow"))}</p>
          <h2>{escape(_t(language, "webui.monitor.inventory.title"))}</h2>
        </div>
        <span class="muted refresh-notice">{escape(monitor_notice)}</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{escape(_t(language, "webui.monitor.table.pipeline_table"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.recent_runs"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.status"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.trigger"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.duration"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.last_run"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.next_run"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.schedule"))}</th>
              <th>{escape(_t(language, "webui.monitor.table.detail"))}</th>
            </tr>
          </thead>
          <tbody>{inventory_html}</tbody>
        </table>
      </div>
    </section>
    """
    return _render_layout(
        title=_t(language, "webui.monitor.title"),
        subtitle=_t(language, "webui.monitor.subtitle"),
        active_path=MONITOR_PATH,
        hero_links=[
            (_t(language, "webui.monitor.hero.pipelines_api"), PIPELINES_PATH),
            (_t(language, "webui.monitor.hero.analytics"), MONITOR_ANALYTICS_PATH),
            (_t(language, "webui.monitor.hero.exports"), MONITOR_EXPORTS_PATH),
        ],
        content_html=content_html,
        auto_refresh_seconds=monitor_refresh_seconds,
        language=language,
    )


# ---------------------------------------------------------------------------
# /monitor/pipelines/{name}/runs/{run_id} — Run Detail (Step Timeline)
# ---------------------------------------------------------------------------

def render_run_detail_page(
    run: dict,
    pipeline_name: str,
    schedule: str,
    *,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Airflow Gantt view 스타일의 step 실행 타임라인 상세 페이지."""
    steps: list[dict] = run.get("steps", [])
    run_status = run.get("status", "unknown")
    run_tone = _status_tone(run_status)
    run_duration = _fmt_duration(run.get("started_at"), run.get("finished_at"))

    # Gantt 전체 시간 범위 계산
    all_starts = [
        datetime.fromisoformat(str(s["started_at"]))
        for s in steps
        if s.get("started_at")
    ]
    all_ends = [
        datetime.fromisoformat(str(s["finished_at"]))
        for s in steps
        if s.get("finished_at")
    ]
    now = datetime.now()
    timeline_start = min(all_starts) if all_starts else now
    timeline_end = max(all_ends) if all_ends else now
    total_secs = max(1.0, (timeline_end - timeline_start).total_seconds())

    step_rows: list[str] = []
    for step in steps:
        step_status = step.get("status", "unknown")
        step_tone = _status_tone(step_status)
        step_duration = _fmt_duration(step.get("started_at"), step.get("finished_at"))
        records = step.get("records_processed", 0)
        retries = step.get("retry_count", 0)

        # Gantt 바 위치/너비 계산
        bar_left_pct = 0.0
        bar_width_pct = 100.0
        if step.get("started_at"):
            try:
                step_start = datetime.fromisoformat(str(step["started_at"]))
                step_end = (
                    datetime.fromisoformat(str(step["finished_at"]))
                    if step.get("finished_at")
                    else now
                )
                offset = (step_start - timeline_start).total_seconds()
                dur_s = max(0.0, (step_end - step_start).total_seconds())
                bar_left_pct = min(98.0, offset / total_secs * 100)
                bar_width_pct = max(1.5, dur_s / total_secs * 100)
                bar_width_pct = min(bar_width_pct, 100.0 - bar_left_pct)
            except (ValueError, TypeError):
                pass

        error_html = ""
        if step.get("error_message"):
            error_html = f'<div class="step-error">{escape(str(step["error_message"]))}</div>'

        step_rows.append(f"""
          <tr>
            <td>
              <strong>{_fmt(step.get("step_name"))}</strong>
              {error_html}
            </td>
            <td><span class="status {step_tone}">{_fmt(step_status)}</span></td>
            <td>
              <div class="gantt-track">
                <div class="gantt-bar {step_tone}"
                     style="left:{bar_left_pct:.1f}%;width:{bar_width_pct:.1f}%"
                     title="{escape(step_duration)}"></div>
              </div>
            </td>
            <td>{_fmt(step_duration)}</td>
            <td>{_fmt(str(records) if records else None)}</td>
            <td>{_fmt(str(retries))}</td>
          </tr>
        """)

    steps_html = (
        "".join(step_rows)
        or f'<tr><td colspan="6" class="empty">{escape(_t(language, "webui.run_detail.empty.no_step_records"))}</td></tr>'
    )

    timeline_title = _t(language, "webui.run_detail.timeline.title", count=len(steps))

    content_html = f"""
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">{escape(_t(language, "webui.run_detail.eyebrow"))}</p>
          <h2>{escape(pipeline_name)} &nbsp;·&nbsp; {_fmt(run.get("execution_date"))}</h2>
        </div>
        <span class="status {run_tone}">{escape(run_status)}</span>
      </div>
      <dl class="meta-grid" style="margin-top:14px;">
        <div><dt>{escape(_t(language, "webui.run_detail.meta.run_id"))}</dt><dd style="font-family:monospace;font-size:.85rem;">{_fmt(run.get("id"))}</dd></div>
        <div><dt>{escape(_t(language, "webui.run_detail.meta.trigger"))}</dt><dd>{_fmt(run.get("trigger_type"))}</dd></div>
        <div><dt>{escape(_t(language, "webui.run_detail.meta.duration"))}</dt><dd>{_fmt(run_duration)}</dd></div>
        <div><dt>{escape(_t(language, "webui.run_detail.meta.schedule"))}</dt><dd>{_fmt(schedule)}</dd></div>
        <div><dt>{escape(_t(language, "webui.run_detail.meta.started"))}</dt><dd>{_fmt(run.get("started_at"))}</dd></div>
        <div><dt>{escape(_t(language, "webui.run_detail.meta.finished"))}</dt><dd>{_fmt(run.get("finished_at"))}</dd></div>
      </dl>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">{escape(_t(language, "webui.run_detail.timeline.eyebrow"))}</p>
          <h2>{escape(timeline_title)}</h2>
        </div>
        <a class="button-link" href="{escape(_with_language_query(MONITOR_PATH, language))}">{escape(_t(language, "webui.run_detail.back_to_pipelines"))}</a>
      </div>
      <div class="table-wrap">
        <table class="gantt-table">
          <thead>
            <tr>
              <th style="min-width:180px;">{escape(_t(language, "webui.run_detail.table.step"))}</th>
              <th>{escape(_t(language, "webui.run_detail.table.status"))}</th>
              <th style="min-width:240px;">{escape(_t(language, "webui.run_detail.table.timeline"))}</th>
              <th>{escape(_t(language, "webui.run_detail.table.duration"))}</th>
              <th>{escape(_t(language, "webui.run_detail.table.records"))}</th>
              <th>{escape(_t(language, "webui.run_detail.table.retries"))}</th>
            </tr>
          </thead>
          <tbody>{steps_html}</tbody>
        </table>
      </div>
    </section>
    """
    return _render_layout(
        title=_t(language, "webui.run_detail.title", pipeline_name=pipeline_name),
        subtitle=_t(
            language,
            "webui.run_detail.subtitle",
            execution_date=run.get("execution_date", ""),
            run_status=run_status,
        ),
        active_path=MONITOR_PATH,
        hero_links=[
            (_t(language, "webui.run_detail.hero.all_runs_api"), pipeline_runs_path(pipeline_name)),
            (_t(language, "webui.run_detail.hero.this_run_api"), pipeline_run_detail_path(pipeline_name, run.get("id", ""))),
        ],
        content_html=content_html,
        page_tag=_t(language, "webui.layout.page_tag.run_timeline"),
        language=language,
    )


# ---------------------------------------------------------------------------
# /monitor/analytics — Analytics dashboard page
# ---------------------------------------------------------------------------

def render_unavailable_page(
    title: str,
    message: str,
    *,
    active_path: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    content_html = f"""
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(_t(language, "webui.unavailable.eyebrow"))}</p><h2>{escape(_t(language, "webui.unavailable.title"))}</h2></div>
        <span class="status bad">{escape(_t(language, "webui.unavailable.status"))}</span>
      </div>
      <p class="muted">{escape(message)}</p>
      <p class="muted">{escape(_t(language, "webui.unavailable.enable_hint"))}</p>
    </section>
    """
    return _render_layout(
        title=title,
        subtitle=message,
        active_path=active_path,
        hero_links=[
            (_t(language, "webui.unavailable.hero.pipelines"), MONITOR_PATH),
            (_t(language, "webui.unavailable.hero.swagger"), "/docs"),
        ],
        content_html=content_html,
        page_tag=_t(language, "webui.layout.page_tag.service_status"),
        language=language,
    )


def render_analytics_dashboard_page(
    page: dict,
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    analytics_refresh_seconds = _cfg(webui_config, "analytics_refresh_seconds", 60)
    dashboard = page["dashboard"]
    summary = page["summary"]
    charts = page["charts"]
    detail_preview = page["detail_preview"]
    filters_applied = page["filters_applied"]
    export_jobs = page["export_jobs"]
    dashboard_id = dashboard["dashboard_id"]
    dataset = dashboard["dataset"]

    filter_controls: list[str] = []
    for filter_def in dashboard["filters"]:
        selected_values = set(filters_applied.get(filter_def["key"], []))
        options_html = "".join(
            f'<option value="{escape(opt["value"])}"{" selected" if opt["value"] in selected_values else ""}>'
            f'{escape(opt["label"])}</option>'
            for opt in filter_def["options"]
        )
        size = max(2, min(6, len(filter_def["options"]) or 2))
        filter_controls.append(f"""
            <label class="filter-field">
              <span>{escape(filter_def["label"])}</span>
              <select name="{escape(filter_def["key"])}" multiple size="{size}">{options_html}</select>
            </label>
        """)
    filter_controls_html = "".join(filter_controls) or (
        f'<p class="empty">{escape(_t(language, "webui.analytics.empty.no_dashboard_filters"))}</p>'
    )
    filter_key_map = {item["key"]: item["label"] for item in dashboard["filters"]}
    filter_chips_html = "".join(
        f'<span class="chip">{escape(filter_key_map.get(key, key))}: {escape(value)}</span>'
        for key, values in filters_applied.items()
        for value in values
    ) or f'<span class="chip">{escape(_t(language, "webui.analytics.filters.none_applied"))}</span>'

    summary_tiles = "".join([
        _summary_tile(
            _t(language, "webui.analytics.summary.dashboard.label"),
            dashboard["title"],
            _t(language, "webui.analytics.summary.dashboard.detail"),
        ),
        _summary_tile(
            _t(language, "webui.analytics.summary.charts.label"),
            str(len(dashboard["charts"])),
            _t(language, "webui.analytics.summary.charts.detail"),
        ),
        _summary_tile(
            _t(language, "webui.analytics.summary.active_filters.label"),
            str(sum(len(v) for v in filters_applied.values())),
            _t(language, "webui.analytics.summary.active_filters.detail"),
        ),
        _summary_tile(
            _t(language, "webui.analytics.summary.recent_jobs.label"),
            str(len(export_jobs)),
            _t(language, "webui.analytics.summary.recent_jobs.detail"),
            tone="warn" if export_jobs else "neutral",
        ),
    ])

    metric_map = {m["key"]: m for m in summary["metrics"]}
    metrics_html = "".join(
        f"""
        <article class="summary-tile neutral">
          <p class="summary-label">{escape(card["label"])}</p>
          <div class="summary-value">{_fmt(metric_map.get(card["metric_key"], {}).get("value"))}</div>
          <p class="summary-detail">
            {_fmt(metric_map.get(card["metric_key"], {}).get("unit"), fallback=_t(language, "webui.analytics.metric.no_unit"))} ·
            {_fmt(card.get("description"), fallback=_t(language, "webui.analytics.metric.default_description"))}
          </p>
        </article>
        """
        for card in dashboard["cards"]
    ) or f'<p class="empty">{escape(_t(language, "webui.analytics.empty.no_summary_cards"))}</p>'

    chart_sections: list[str] = []
    for chart_def in dashboard["charts"]:
        chart_response = charts.get(chart_def["chart_id"])
        points = (
            chart_response["series"][0]["points"]
            if chart_response and chart_response.get("series")
            else []
        )
        max_value = max((p["value"] for p in points), default=1)
        point_rows = "".join(f"""
            <div class="chart-row">
              <strong>{escape(p.get("label") or p["bucket"])}</strong>
              <div class="chart-bar"><span style="width:{max(6, int(p["value"] / max_value * 100)) if max_value else 0}%"></span></div>
              <span>{_fmt(p["value"])}</span>
            </div>
        """ for p in points) or f'<p class="empty">{escape(_t(language, "webui.analytics.empty.no_chart_data"))}</p>'
        chart_sections.append(f"""
            <section class="subpanel">
              <div class="panel-head">
                <div><p class="eyebrow">{escape(_t(language, "webui.analytics.chart.eyebrow"))}</p><h2>{escape(chart_def["title"])}</h2></div>
                <a href="{escape(_with_language_query(chart_def["query_endpoint"], language))}" target="_blank" rel="noreferrer">{escape(_t(language, "webui.analytics.chart.query_api"))}</a>
              </div>
              <div class="chart-list">{point_rows}</div>
            </section>
        """)
    charts_html = "".join(chart_sections) or f'<p class="empty">{escape(_t(language, "webui.analytics.empty.no_charts"))}</p>'

    detail_table = f'<p class="empty">{escape(_t(language, "webui.analytics.empty.no_drilldown_preview"))}</p>'
    if detail_preview is not None:
        columns = detail_preview["columns"]
        rows = detail_preview["rows"]
        head_html = "".join(f"<th>{escape(col['label'])}</th>" for col in columns)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{_fmt(row.get(col['key']))}</td>" for col in columns) + "</tr>"
            for row in rows
        )
        if not body_html:
            body_html = f'<tr><td colspan="{len(columns)}" class="empty">{escape(_t(language, "webui.analytics.empty.no_rows"))}</td></tr>'
        detail_table = (
            f'<div class="table-wrap"><table><thead><tr>{head_html}</tr></thead>'
            f'<tbody>{body_html}</tbody></table></div>'
        )

    hidden_filters_html = "".join(
        f'<input type="hidden" name="{escape(key)}" value="{escape(value)}">'
        for key, values in filters_applied.items()
        for value in values
    )
    export_forms_html = "".join(f"""
        <form class="inline-form" method="post" action="{escape(_with_language_query(f"{MONITOR_ANALYTICS_PATH}/exports", language))}">
          <input type="hidden" name="dataset" value="{escape(dataset)}">
          <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
          <input type="hidden" name="lang" value="{escape(language)}">
          <input type="hidden" name="action_key" value="{escape(action["key"])}">
          <input type="hidden" name="format" value="{escape(action["format"] or "")}">
          {hidden_filters_html}
          <button type="submit">{escape(action["label"])}</button>
        </form>
    """ for action in dashboard["export_actions"] if action["status"] == "available"
    ) or f'<p class="empty">{escape(_t(language, "webui.analytics.empty.no_export_actions"))}</p>'

    recent_jobs_rows = "".join(f"""
        <tr>
          <td style="font-family:monospace;font-size:.82rem;">{escape(job["job_id"][:16])}…</td>
          <td><span class="status {_status_tone(job["status"])}">{escape(job["status"])}</span></td>
          <td>{escape(job["format"])}</td>
          <td>{_fmt(job["updated_at"])}</td>
        </tr>
    """ for job in export_jobs
    ) or f'<tr><td colspan="4" class="empty">{escape(_t(language, "webui.analytics.empty.no_export_jobs"))}</td></tr>'

    analytics_refresh_notice = _t(
        language,
        "webui.analytics.metadata.refresh_notice",
        seconds=analytics_refresh_seconds,
    )
    reset_href = _with_language_query(
        f"{MONITOR_ANALYTICS_PATH}?dataset={dataset}&dashboard_id={dashboard_id}",
        language,
    )
    dashboard_api_href = _with_language_query(
        f"{dashboard_definition_path(dashboard_id)}?dataset={dataset}",
        language,
    )
    full_export_monitor_href = _with_language_query(
        f"{MONITOR_EXPORTS_PATH}?dataset={dataset}",
        language,
    )

    content_html = f"""
    <section class="summary-grid">{summary_tiles}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(_t(language, "webui.analytics.metadata.eyebrow"))}</p><h2>{escape(dashboard["title"])}</h2></div>
        <span class="muted refresh-notice">{escape(analytics_refresh_notice)}</span>
      </div>
      <dl class="meta-grid">
        <div><dt>{escape(_t(language, "webui.analytics.metadata.dashboard_id"))}</dt><dd>{escape(dashboard_id)}</dd></div>
        <div><dt>{escape(_t(language, "webui.analytics.metadata.dataset"))}</dt><dd>{escape(dataset)}</dd></div>
        <div><dt>{escape(_t(language, "webui.analytics.metadata.last_refreshed"))}</dt><dd>{_fmt(dashboard.get("last_refreshed_at"))}</dd></div>
        <div><dt>{escape(_t(language, "webui.analytics.metadata.contract"))}</dt><dd>{escape(dashboard["contract_version"])}</dd></div>
      </dl>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(_t(language, "webui.analytics.filter_bar.eyebrow"))}</p><h2>{escape(_t(language, "webui.analytics.filter_bar.title"))}</h2></div>
        <span class="muted">{escape(_t(language, "webui.analytics.filter_bar.readonly_hint"))}</span>
      </div>
      <form class="filter-form" method="get" action="{escape(_with_language_query(MONITOR_ANALYTICS_PATH, language))}">
        <input type="hidden" name="dataset" value="{escape(dataset)}">
        <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
        <div class="filter-grid">{filter_controls_html}</div>
        <div class="actions">
          <button class="primary" type="submit">{escape(_t(language, "webui.analytics.filter_bar.apply_filters"))}</button>
          <a class="button-link" href="{escape(reset_href)}">{escape(_t(language, "webui.analytics.filter_bar.reset"))}</a>
          <a class="button-link" href="{escape(dashboard_api_href)}" target="_blank" rel="noreferrer">{escape(_t(language, "webui.analytics.filter_bar.dashboard_api"))}</a>
        </div>
      </form>
      <div class="chip-list" style="margin-top:10px;">{filter_chips_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(_t(language, "webui.analytics.dataset_overview.eyebrow"))}</p><h2>{escape(_t(language, "webui.analytics.dataset_overview.title"))}</h2></div>
        <span class="muted">{escape(_t(language, "webui.analytics.dataset_overview.hint"))}</span>
      </div>
      <div class="summary-grid">{metrics_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head"><div><p class="eyebrow">{escape(_t(language, "webui.analytics.charts.eyebrow"))}</p><h2>{escape(_t(language, "webui.analytics.charts.title"))}</h2></div></div>
      <div class="grid-2">{charts_html}</div>
    </section>
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head">
          <div><p class="eyebrow">{escape(_t(language, "webui.analytics.drilldown.eyebrow"))}</p><h2>{escape(_t(language, "webui.analytics.drilldown.title"))}</h2></div>
          <span class="muted">{escape(_t(language, "webui.analytics.drilldown.hint"))}</span>
        </div>
        {detail_table}
      </section>
      <section class="stack">
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">{escape(_t(language, "webui.analytics.exports.eyebrow"))}</p><h2>{escape(_t(language, "webui.analytics.exports.title"))}</h2></div>
            <span class="muted">{escape(_t(language, "webui.analytics.exports.hint"))}</span>
          </div>
          <div class="actions">{export_forms_html}</div>
        </section>
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">{escape(_t(language, "webui.analytics.recent_jobs.eyebrow"))}</p><h2>{escape(_t(language, "webui.analytics.recent_jobs.title"))}</h2></div>
            <a href="{escape(full_export_monitor_href)}">{escape(_t(language, "webui.analytics.recent_jobs.full_monitor"))}</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>{escape(_t(language, "webui.analytics.recent_jobs.table.job_id"))}</th><th>{escape(_t(language, "webui.analytics.recent_jobs.table.status"))}</th><th>{escape(_t(language, "webui.analytics.recent_jobs.table.format"))}</th><th>{escape(_t(language, "webui.analytics.recent_jobs.table.updated"))}</th></tr></thead>
              <tbody>{recent_jobs_rows}</tbody>
            </table>
          </div>
        </section>
      </section>
    </div>
    """
    return _render_layout(
        title=_t(language, "webui.analytics.title"),
        subtitle=_t(language, "webui.analytics.subtitle"),
        active_path=MONITOR_ANALYTICS_PATH,
        hero_links=[
            (_t(language, "webui.analytics.hero.dashboard_api"), f"{dashboard_definition_path(dashboard_id)}?dataset={dataset}"),
            (_t(language, "webui.analytics.hero.filters_api"), f"{ANALYTICS_FILTERS_PATH}?dataset={dataset}"),
            (_t(language, "webui.analytics.hero.export_monitor"), f"{MONITOR_EXPORTS_PATH}?dataset={dataset}"),
        ],
        content_html=content_html,
        page_tag=_t(language, "webui.layout.page_tag.analytics_workspace"),
        auto_refresh_seconds=analytics_refresh_seconds,
        language=language,
    )


# ---------------------------------------------------------------------------
# /monitor/exports — Export jobs page
# ---------------------------------------------------------------------------

def render_export_jobs_page(
    page: dict,
    *,
    webui_config=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    jobs = page["jobs"]
    selected_job_id = page.get("selected_job_id")
    counts = page["counts"]
    dataset = page.get("dataset")
    retention_hours = page["retention_hours"]
    active_refresh_seconds = _cfg(webui_config, "exports_active_refresh_seconds", 10)
    idle_refresh_seconds = _cfg(webui_config, "exports_idle_refresh_seconds", 30)

    summary_html = "".join([
        _summary_tile(
            _t(language, "webui.exports.summary.queued.label"),
            str(counts["queued"]),
            _t(language, "webui.exports.summary.queued.detail"),
            tone="warn" if counts["queued"] else "neutral",
        ),
        _summary_tile(
            _t(language, "webui.exports.summary.running.label"),
            str(counts["running"]),
            _t(language, "webui.exports.summary.running.detail"),
            tone="warn" if counts["running"] else "neutral",
        ),
        _summary_tile(
            _t(language, "webui.exports.summary.completed.label"),
            str(counts["completed"]),
            _t(language, "webui.exports.summary.completed.detail"),
            tone="ok" if counts["completed"] else "neutral",
        ),
        _summary_tile(
            _t(language, "webui.exports.summary.retention.label"),
            f"{retention_hours}h",
            _t(language, "webui.exports.summary.retention.detail"),
        ),
    ])

    rows: list[str] = []
    for job in jobs:
        download_cell = (
            f'<a href="{escape(_with_language_query(job["download_endpoint"], language))}">{escape(_t(language, "webui.exports.download"))}</a>'
            if job.get("download_endpoint")
            else f'<span class="muted">{escape(_t(language, "webui.exports.not_ready"))}</span>'
        )
        highlight = " highlight" if selected_job_id and job["job_id"] == selected_job_id else ""
        is_active = job["status"] in {"running", "queued"}
        pulse_cls = " pulse" if is_active else ""
        dataset_hidden = f'<input type="hidden" name="dataset" value="{escape(dataset)}">' if dataset else ""
        lang_hidden = f'<input type="hidden" name="lang" value="{escape(language)}">'
        delete_cell = (
            f'<form method="post" action="{escape(_with_language_query(MONITOR_EXPORT_DELETE_JOB_PATH, language))}" style="display:inline">'
            f'<input type="hidden" name="job_id" value="{escape(job["job_id"])}">'
            f'{dataset_hidden}'
            f'{lang_hidden}'
            f'<button type="submit" class="btn-delete" onclick="return confirm(\'{escape(_t(language, "webui.exports.confirm.delete_job"))}\')">{escape(_t(language, "webui.exports.delete"))}</button>'
            f'</form>'
        ) if not is_active else '<span class="muted">-</span>'

        rows.append(f"""
            <tr class="{highlight.strip()}">
              <td style="font-family:monospace;font-size:.82rem;">{escape(job["job_id"][:20])}…</td>
              <td>{escape(job["dataset"])}</td>
              <td>{escape(job["action_key"])}</td>
              <td><span class="status {_status_tone(job["status"])}{pulse_cls}">{escape(job["status"])}</span></td>
              <td>{escape(job["format"])}</td>
              <td>{_fmt(job.get("row_count"))}</td>
              <td>{_fmt(job["created_at"])}</td>
              <td>{_fmt(job["updated_at"])}</td>
              <td>{_fmt(job["expires_at"])}</td>
              <td>{download_cell}</td>
              <td>{_fmt(job.get("error_message"), fallback="")}</td>
              <td>{delete_cell}</td>
            </tr>
        """)

    rows_html = (
        "".join(rows)
        or f'<tr><td colspan="12" class="empty">{escape(_t(language, "webui.exports.empty.no_jobs"))}</td></tr>'
    )
    dataset_query = f"?dataset={dataset}" if dataset else ""

    # 진행 중인 job이 있으면 10초, 없으면 30초 갱신
    has_active = counts["queued"] + counts["running"] > 0
    refresh_secs = active_refresh_seconds if has_active else idle_refresh_seconds

    refresh_notice = _t(
        language,
        "webui.exports.retention.refresh_notice",
        dataset=_fmt(dataset, fallback=_t(language, "webui.exports.retention.all_datasets")),
        seconds=refresh_secs,
    )
    retention_description = _t(
        language,
        "webui.exports.retention.description",
        hours=retention_hours,
    )
    all_datasets_href = _with_language_query(MONITOR_EXPORTS_PATH, language)
    analytics_href = _with_language_query(
        f"{MONITOR_ANALYTICS_PATH}{dataset_query if dataset else ''}",
        language,
    )
    delete_completed_action = _with_language_query(MONITOR_EXPORT_DELETE_COMPLETED_PATH, language)

    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(_t(language, "webui.exports.retention.eyebrow"))}</p><h2>{escape(_t(language, "webui.exports.retention.title"))}</h2></div>
        <span class="muted refresh-notice">{escape(refresh_notice)}</span>
      </div>
      <p class="muted">{escape(retention_description)}</p>
      <div class="actions">
        <a class="button-link" href="{escape(all_datasets_href)}">{escape(_t(language, "webui.exports.actions.all_datasets"))}</a>
        <a class="button-link" href="{escape(analytics_href)}">{escape(_t(language, "webui.exports.actions.analytics"))}</a>
        <form method="post" action="{escape(delete_completed_action)}" style="display:inline">
          {'<input type="hidden" name="dataset" value="' + escape(dataset) + '">' if dataset else ''}
          <input type="hidden" name="lang" value="{escape(language)}">
          <button type="submit" class="btn-delete" onclick="return confirm('{escape(_t(language, "webui.exports.confirm.delete_all_completed"))}')">{escape(_t(language, "webui.exports.actions.delete_all_completed"))}</button>
        </form>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">{escape(_t(language, "webui.exports.inventory.eyebrow"))}</p><h2>{escape(_t(language, "webui.exports.inventory.title"))}</h2></div>
        <span class="muted">{escape(_t(language, "webui.exports.inventory.hint"))}</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{escape(_t(language, "webui.exports.table.job_id"))}</th><th>{escape(_t(language, "webui.exports.table.dataset"))}</th><th>{escape(_t(language, "webui.exports.table.action"))}</th><th>{escape(_t(language, "webui.exports.table.status"))}</th>
              <th>{escape(_t(language, "webui.exports.table.format"))}</th><th>{escape(_t(language, "webui.exports.table.rows"))}</th><th>{escape(_t(language, "webui.exports.table.created"))}</th><th>{escape(_t(language, "webui.exports.table.updated"))}</th>
              <th>{escape(_t(language, "webui.exports.table.expires"))}</th><th>{escape(_t(language, "webui.exports.table.download"))}</th><th>{escape(_t(language, "webui.exports.table.error"))}</th><th>{escape(_t(language, "webui.exports.table.admin"))}</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </section>
    """
    return _render_layout(
        title=_t(language, "webui.exports.title"),
        subtitle=_t(language, "webui.exports.subtitle"),
        active_path=MONITOR_EXPORTS_PATH,
        hero_links=[
            (
                _t(language, "webui.exports.hero.analytics"),
                f"{MONITOR_ANALYTICS_PATH}{dataset_query}" if dataset else MONITOR_ANALYTICS_PATH,
            ),
            (_t(language, "webui.exports.hero.export_api"), ANALYTICS_EXPORTS_PATH),
        ],
        content_html=content_html,
        page_tag=_t(language, "webui.layout.page_tag.export_workspace"),
        auto_refresh_seconds=refresh_secs,
        language=language,
    )
