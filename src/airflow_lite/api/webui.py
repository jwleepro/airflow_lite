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

from html import escape
from datetime import datetime


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


def _nav_link(label: str, href: str, active_path: str) -> str:
    active_class = " active" if href == active_path else ""
    return f'<a class="nav-link{active_class}" href="{escape(href)}">{escape(label)}</a>'


def _link_group(links: list[tuple[str, str]] | None) -> str:
    if not links:
        return ""
    return "".join(
        f'<a href="{escape(href)}" target="_blank" rel="noreferrer">{escape(label)}</a>'
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


def _run_status_block(status: str | None, title: str = "") -> str:
    """단일 실행 상태 블록 (Airflow DAG list 그리드 셀)."""
    tone = _status_tone(status or "")
    tip = escape(title) if title else escape(status or "no run")
    return f'<span class="run-block {tone}" title="{tip}"></span>'


def _run_status_grid(runs: list[dict]) -> str:
    """최근 실행 색상 블록 그리드 (오래된 것 왼쪽, 최신 오른쪽)."""
    if not runs:
        return '<span class="run-grid-empty">No runs</span>'
    blocks = "".join(
        _run_status_block(
            run.get("status"),
            f"{run.get('execution_date', '')} · {run.get('status', '')}",
        )
        for run in reversed(runs)
    )
    return f'<div class="run-grid">{blocks}</div>'


def _first_failed_step_error(run: dict) -> str | None:
    """실행 결과에서 첫 번째 실패 step의 error_message 반환 (최대 120자)."""
    for step in run.get("steps", []):
        if step.get("status") == "failed" and step.get("error_message"):
            name = step.get("step_name", "")
            msg = str(step["error_message"])
            if len(msg) > 120:
                msg = msg[:120] + "…"
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
    page_tag: str = "Operations Console",
    auto_refresh_seconds: int | None = None,
) -> str:
    hero_links_html = _link_group(hero_links)
    refresh_meta = (
        f'<meta http-equiv="refresh" content="{auto_refresh_seconds}">'
        if auto_refresh_seconds
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
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
              <span>Read-only operations workspace</span>
            </div>
          </div>
          <div class="utility-links">
            <a href="/docs" target="_blank" rel="noreferrer">Swagger</a>
            <a href="/api/v1/pipelines" target="_blank" rel="noreferrer">Pipeline API</a>
          </div>
        </div>
        <div class="nav-row" style="margin-top:18px;">
          <div>
            <p class="page-kicker">{escape(page_tag)}</p>
            <h1 class="page-title">{escape(title)}</h1>
            <p class="page-subtitle">{escape(subtitle)}</p>
          </div>
          <nav class="nav-tabs">
            {_nav_link("Pipelines", "/monitor", active_path)}
            {_nav_link("Analytics", "/monitor/analytics", active_path)}
            {_nav_link("Exports", "/monitor/exports", active_path)}
          </nav>
        </div>
      </div>
    </header>
    <main class="page-shell">
      <section class="header-card">
        <div class="header-card-row">
          <span class="header-tag">Ops Console</span>
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

def render_monitor_page(pipeline_rows: list[dict]) -> str:
    """파이프라인 목록 + 최근 실행 상태 그리드 (Airflow DAG list 스타일).

    pipeline_rows 각 항목:
      name, table, strategy, schedule, next_run (str|None),
      latest_run (dict|None), recent_runs (list[dict], 최대 25건)
    """
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
        _summary_tile("Configured Pipelines", str(total_pipelines), "Total pipeline inventory"),
        _summary_tile("Healthy Last Run", str(healthy_runs), "Most recent run succeeded", tone="ok"),
        _summary_tile(
            "Active Runs", str(active_runs), "Running / queued / pending",
            tone="warn" if active_runs else "neutral",
        ),
        _summary_tile(
            "Failed Last Run", str(failed_runs), "Requires operator attention",
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
            err = _first_failed_step_error(latest)
            if err:
                error_html = f'<div class="error-inline">{escape(err)}</div>'

        # running/pending → pulse 애니메이션
        pulse_cls = " pulse" if latest_status in {"running", "queued", "pending"} else ""

        # 상세 링크 (run_id가 있을 때만)
        detail_link = (
            f'<a href="/monitor/pipelines/{escape(row["name"])}/runs/{escape(run_id)}">상세</a>'
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
              <td>{_run_status_grid(recent_runs)}</td>
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
        or '<tr><td colspan="9" class="empty">No pipelines configured.</td></tr>'
    )

    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Pipeline Inventory</p>
          <h2>All configured pipelines</h2>
        </div>
        <span class="muted refresh-notice">
          최근 완료: {_fmt(latest_finish, fallback="없음")} &nbsp;·&nbsp; 30초마다 자동 갱신
        </span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pipeline / Table</th>
              <th>Recent Runs (oldest→latest)</th>
              <th>Status</th>
              <th>Trigger</th>
              <th>Duration</th>
              <th>Last Run</th>
              <th>Next Run</th>
              <th>Schedule</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>{inventory_html}</tbody>
        </table>
      </div>
    </section>
    """
    return _render_layout(
        title="Airflow Lite Monitor",
        subtitle="Pipeline inventory with run-status grid, duration, next scheduled run, and inline error summary.",
        active_path="/monitor",
        hero_links=[
            ("Pipelines API", "/api/v1/pipelines"),
            ("Analytics", "/monitor/analytics"),
            ("Exports", "/monitor/exports"),
        ],
        content_html=content_html,
        auto_refresh_seconds=30,
    )


# ---------------------------------------------------------------------------
# /monitor/pipelines/{name}/runs/{run_id} — Run Detail (Step Timeline)
# ---------------------------------------------------------------------------

def render_run_detail_page(run: dict, pipeline_name: str, schedule: str) -> str:
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
        or '<tr><td colspan="6" class="empty">No step records.</td></tr>'
    )

    content_html = f"""
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Run Detail</p>
          <h2>{escape(pipeline_name)} &nbsp;·&nbsp; {_fmt(run.get("execution_date"))}</h2>
        </div>
        <span class="status {run_tone}">{escape(run_status)}</span>
      </div>
      <dl class="meta-grid" style="margin-top:14px;">
        <div><dt>Run ID</dt><dd style="font-family:monospace;font-size:.85rem;">{_fmt(run.get("id"))}</dd></div>
        <div><dt>Trigger</dt><dd>{_fmt(run.get("trigger_type"))}</dd></div>
        <div><dt>Duration</dt><dd>{_fmt(run_duration)}</dd></div>
        <div><dt>Schedule</dt><dd>{_fmt(schedule)}</dd></div>
        <div><dt>Started</dt><dd>{_fmt(run.get("started_at"))}</dd></div>
        <div><dt>Finished</dt><dd>{_fmt(run.get("finished_at"))}</dd></div>
      </dl>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Step Timeline</p>
          <h2>Gantt view — {len(steps)} step(s)</h2>
        </div>
        <a class="button-link" href="/monitor">← Pipelines</a>
      </div>
      <div class="table-wrap">
        <table class="gantt-table">
          <thead>
            <tr>
              <th style="min-width:180px;">Step</th>
              <th>Status</th>
              <th style="min-width:240px;">Timeline (relative)</th>
              <th>Duration</th>
              <th>Records</th>
              <th>Retries</th>
            </tr>
          </thead>
          <tbody>{steps_html}</tbody>
        </table>
      </div>
    </section>
    """
    return _render_layout(
        title=f"Run Detail — {pipeline_name}",
        subtitle=f"Step-level execution timeline · {run.get('execution_date', '')} · {run_status}",
        active_path="/monitor",
        hero_links=[
            ("All Runs API", f"/api/v1/pipelines/{escape(pipeline_name)}/runs"),
            ("This Run API", f"/api/v1/pipelines/{escape(pipeline_name)}/runs/{escape(run.get('id', ''))}"),
        ],
        content_html=content_html,
        page_tag="Run Timeline",
    )


# ---------------------------------------------------------------------------
# /monitor/analytics — Analytics dashboard page
# ---------------------------------------------------------------------------

def render_unavailable_page(title: str, message: str, *, active_path: str) -> str:
    content_html = f"""
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Unavailable</p><h2>Required service is not configured</h2></div>
        <span class="status bad">blocked</span>
      </div>
      <p class="muted">{escape(message)}</p>
      <p class="muted">Enable the analytics mart and export service wiring to use this screen.</p>
    </section>
    """
    return _render_layout(
        title=title,
        subtitle=message,
        active_path=active_path,
        hero_links=[("Pipelines", "/monitor"), ("Swagger", "/docs")],
        content_html=content_html,
        page_tag="Service Status",
    )


def render_analytics_dashboard_page(page: dict) -> str:
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
    filter_controls_html = "".join(filter_controls) or '<p class="empty">No dashboard filters defined.</p>'
    filter_chips_html = "".join(
        f'<span class="chip">{escape(key)}: {escape(value)}</span>'
        for key, values in filters_applied.items()
        for value in values
    ) or '<span class="chip">No filters applied</span>'

    summary_tiles = "".join([
        _summary_tile("Dashboard", dashboard["title"], "Contract-backed dashboard view"),
        _summary_tile("Charts", str(len(dashboard["charts"])), "Rendered from query endpoints"),
        _summary_tile(
            "Active Filters",
            str(sum(len(v) for v in filters_applied.values())),
            "Current filter state in the URL",
        ),
        _summary_tile(
            "Recent Jobs", str(len(export_jobs)), "Latest exports for this dataset",
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
            {_fmt(metric_map.get(card["metric_key"], {}).get("unit"), fallback="No unit")} ·
            {_fmt(card.get("description"), fallback="Dashboard summary metric")}
          </p>
        </article>
        """
        for card in dashboard["cards"]
    ) or '<p class="empty">No summary cards available.</p>'

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
        """ for p in points) or '<p class="empty">No chart data for current filters.</p>'
        chart_sections.append(f"""
            <section class="subpanel">
              <div class="panel-head">
                <div><p class="eyebrow">Chart</p><h2>{escape(chart_def["title"])}</h2></div>
                <a href="{escape(chart_def["query_endpoint"])}" target="_blank" rel="noreferrer">Query API</a>
              </div>
              <div class="chart-list">{point_rows}</div>
            </section>
        """)
    charts_html = "".join(chart_sections) or '<p class="empty">No charts available.</p>'

    detail_table = '<p class="empty">No drilldown preview available.</p>'
    if detail_preview is not None:
        columns = detail_preview["columns"]
        rows = detail_preview["rows"]
        head_html = "".join(f"<th>{escape(col['label'])}</th>" for col in columns)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{_fmt(row.get(col['key']))}</td>" for col in columns) + "</tr>"
            for row in rows
        )
        if not body_html:
            body_html = f'<tr><td colspan="{len(columns)}" class="empty">No rows.</td></tr>'
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
        <form class="inline-form" method="post" action="/monitor/analytics/exports">
          <input type="hidden" name="dataset" value="{escape(dataset)}">
          <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
          <input type="hidden" name="action_key" value="{escape(action["key"])}">
          <input type="hidden" name="format" value="{escape(action["format"] or "")}">
          {hidden_filters_html}
          <button type="submit">{escape(action["label"])}</button>
        </form>
    """ for action in dashboard["export_actions"] if action["status"] == "available"
    ) or '<p class="empty">No export actions available.</p>'

    recent_jobs_rows = "".join(f"""
        <tr>
          <td style="font-family:monospace;font-size:.82rem;">{escape(job["job_id"][:16])}…</td>
          <td><span class="status {_status_tone(job["status"])}">{escape(job["status"])}</span></td>
          <td>{escape(job["format"])}</td>
          <td>{_fmt(job["updated_at"])}</td>
        </tr>
    """ for job in export_jobs
    ) or '<tr><td colspan="4" class="empty">No export jobs yet.</td></tr>'

    content_html = f"""
    <section class="summary-grid">{summary_tiles}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Dashboard Metadata</p><h2>{escape(dashboard["title"])}</h2></div>
        <span class="muted refresh-notice">60초마다 자동 갱신</span>
      </div>
      <dl class="meta-grid">
        <div><dt>Dashboard ID</dt><dd>{escape(dashboard_id)}</dd></div>
        <div><dt>Dataset</dt><dd>{escape(dataset)}</dd></div>
        <div><dt>Last Refreshed</dt><dd>{_fmt(dashboard.get("last_refreshed_at"))}</dd></div>
        <div><dt>Contract</dt><dd>{escape(dashboard["contract_version"])}</dd></div>
      </dl>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Filter Bar</p><h2>Apply dashboard state</h2></div>
        <span class="muted">Read-only controls backed by the dashboard contract</span>
      </div>
      <form class="filter-form" method="get" action="/monitor/analytics">
        <input type="hidden" name="dataset" value="{escape(dataset)}">
        <input type="hidden" name="dashboard_id" value="{escape(dashboard_id)}">
        <div class="filter-grid">{filter_controls_html}</div>
        <div class="actions">
          <button class="primary" type="submit">Apply Filters</button>
          <a class="button-link" href="/monitor/analytics?dataset={escape(dataset)}&dashboard_id={escape(dashboard_id)}">Reset</a>
          <a class="button-link" href="/api/v1/analytics/dashboards/{escape(dashboard_id)}?dataset={escape(dataset)}" target="_blank" rel="noreferrer">Dashboard API</a>
        </div>
      </form>
      <div class="chip-list" style="margin-top:10px;">{filter_chips_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Dataset Overview</p><h2>Summary cards</h2></div>
        <span class="muted">Current filter state is reflected across every card and chart</span>
      </div>
      <div class="summary-grid">{metrics_html}</div>
    </section>
    <section class="panel">
      <div class="panel-head"><div><p class="eyebrow">Charts</p><h2>Read-only query outputs</h2></div></div>
      <div class="grid-2">{charts_html}</div>
    </section>
    <div class="grid-2">
      <section class="panel">
        <div class="panel-head">
          <div><p class="eyebrow">Drilldown Preview</p><h2>Source Files</h2></div>
          <span class="muted">Top rows from the current drilldown endpoint</span>
        </div>
        {detail_table}
      </section>
      <section class="stack">
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">Exports</p><h2>Queue Export</h2></div>
            <span class="muted">Submit via dashboard actions</span>
          </div>
          <div class="actions">{export_forms_html}</div>
        </section>
        <section class="panel">
          <div class="panel-head">
            <div><p class="eyebrow">Recent Jobs</p><h2>Latest export activity</h2></div>
            <a href="/monitor/exports?dataset={escape(dataset)}">Full export monitor →</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Job ID</th><th>Status</th><th>Format</th><th>Updated</th></tr></thead>
              <tbody>{recent_jobs_rows}</tbody>
            </table>
          </div>
        </section>
      </section>
    </div>
    """
    return _render_layout(
        title="Analytics Dashboard",
        subtitle="Read-only dashboard workspace — summary metrics, charts, drilldown preview, and export actions.",
        active_path="/monitor/analytics",
        hero_links=[
            ("Dashboard API", f"/api/v1/analytics/dashboards/{dashboard_id}?dataset={dataset}"),
            ("Filters API", f"/api/v1/analytics/filters?dataset={dataset}"),
            ("Export Monitor", f"/monitor/exports?dataset={dataset}"),
        ],
        content_html=content_html,
        page_tag="Analytics Workspace",
        auto_refresh_seconds=60,
    )


# ---------------------------------------------------------------------------
# /monitor/exports — Export jobs page
# ---------------------------------------------------------------------------

def render_export_jobs_page(page: dict) -> str:
    jobs = page["jobs"]
    selected_job_id = page.get("selected_job_id")
    counts = page["counts"]
    dataset = page.get("dataset")
    retention_hours = page["retention_hours"]

    summary_html = "".join([
        _summary_tile(
            "Queued", str(counts["queued"]), "Waiting for background worker",
            tone="warn" if counts["queued"] else "neutral",
        ),
        _summary_tile(
            "Running", str(counts["running"]), "Artifacts being generated",
            tone="warn" if counts["running"] else "neutral",
        ),
        _summary_tile(
            "Completed", str(counts["completed"]), "Available for download",
            tone="ok" if counts["completed"] else "neutral",
        ),
        _summary_tile("Retention", f"{retention_hours}h", "Hours before automatic cleanup"),
    ])

    rows: list[str] = []
    for job in jobs:
        download_cell = (
            f'<a href="{escape(job["download_endpoint"])}">Download</a>'
            if job.get("download_endpoint")
            else '<span class="muted">Not ready</span>'
        )
        highlight = " highlight" if selected_job_id and job["job_id"] == selected_job_id else ""
        is_active = job["status"] in {"running", "queued"}
        pulse_cls = " pulse" if is_active else ""

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
            </tr>
        """)

    rows_html = (
        "".join(rows)
        or '<tr><td colspan="11" class="empty">No export jobs recorded.</td></tr>'
    )
    dataset_query = f"?dataset={escape(dataset)}" if dataset else ""

    # 진행 중인 job이 있으면 10초, 없으면 30초 갱신
    has_active = counts["queued"] + counts["running"] > 0
    refresh_secs = 10 if has_active else 30

    content_html = f"""
    <section class="summary-grid">{summary_html}</section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Retention Policy</p><h2>Export Job Monitor</h2></div>
        <span class="muted refresh-notice">
          Filtered: {_fmt(dataset, fallback="all datasets")} &nbsp;·&nbsp; {refresh_secs}초마다 자동 갱신
        </span>
      </div>
      <p class="muted">Artifacts and job records are retained for {retention_hours} hour(s) before automatic cleanup.</p>
      <div class="actions">
        <a class="button-link" href="/monitor/exports">All datasets</a>
        <a class="button-link" href="/monitor/analytics{dataset_query if dataset else ''}">← Analytics</a>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><p class="eyebrow">Job Inventory</p><h2>Export job listing</h2></div>
        <span class="muted">Running jobs highlighted with pulse indicator</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Job ID</th><th>Dataset</th><th>Action</th><th>Status</th>
              <th>Format</th><th>Rows</th><th>Created</th><th>Updated</th>
              <th>Expires</th><th>Download</th><th>Error</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </section>
    """
    return _render_layout(
        title="Export Jobs",
        subtitle="Async export job monitor — status, retention, artifact availability, and download links.",
        active_path="/monitor/exports",
        hero_links=[
            ("Analytics", f"/monitor/analytics{dataset_query}" if dataset else "/monitor/analytics"),
            ("Export API", "/api/v1/analytics/exports/{job_id}"),
        ],
        content_html=content_html,
        page_tag="Export Workspace",
        auto_refresh_seconds=refresh_secs,
    )
