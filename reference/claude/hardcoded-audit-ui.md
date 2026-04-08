# Hardcoded Values Audit — UI Layer

감사일: 2026-04-08
대상 파일: webui.py, web.py, dependencies.py, app.py

---

## 1. HARDCODED URL PATHS / API ENDPOINTS

### webui.py

- Line 255: `/docs` — Swagger documentation link
- Line 256: `/api/v1/pipelines` — Pipeline API link
- Line 266: `/monitor` — Pipelines monitor page
- Line 267: `/monitor/analytics` — Analytics page
- Line 268: `/monitor/exports` — Exports page
- Line 424: `/api/v1/pipelines` — Pipelines API link
- Line 425: `/monitor/analytics` — Analytics link
- Line 426: `/monitor/exports` — Exports link
- Line 564: `/api/v1/pipelines/{escape(pipeline_name)}/runs` — All runs API
- Line 565: `/api/v1/pipelines/{escape(pipeline_name)}/runs/{escape(run.get('id', ''))}` — Specific run API
- Line 591: `/monitor` — Pipelines link
- Line 591: `/docs` — Swagger link
- Line 678: `{escape(chart_def["query_endpoint"])}` — Chart query API (dynamic)
- Line 707: `/monitor/analytics/exports` — Export creation endpoint
- Line 747: `/monitor/analytics` — Analytics form action
- Line 753: `/monitor/analytics?dataset={escape(dataset)}&dashboard_id={escape(dashboard_id)}` — Reset filters link
- Line 754: `/api/v1/analytics/dashboards/{escape(dashboard_id)}?dataset={escape(dataset)}` — Dashboard API
- Line 789: `/monitor/exports?dataset={escape(dataset)}` — Full export monitor link
- Line 901: `/monitor/analytics` — Analytics link
- Line 806: `/api/v1/analytics/dashboards/{dashboard_id}?dataset={dataset}` — Dashboard API link
- Line 807: `/api/v1/analytics/filters?dataset={dataset}` — Filters API link
- Line 808: `/monitor/exports?dataset={dataset}` — Export monitor link
- Line 855: `/monitor/exports/delete-job` — Delete job endpoint
- Line 902: `/monitor/exports/delete-completed` — Delete completed endpoint
- Line 933: `/api/v1/analytics/exports/{job_id}` — Export API link

### web.py

- Line 76: `/monitor/exports?{query}` — Export redirect URL
- Line 81: `/monitor` — Root redirect
- Line 156: Default parameter `dataset="mes_ops"` — Default dataset name
- Line 157: Default parameter `dashboard_id="operations_overview"` — Default dashboard ID
- Line 266: Default value `"mes_ops"` — Default dataset in form
- Line 267: Default value `"operations_overview"` — Default dashboard ID in form

---

## 2. HARDCODED TEXT STRINGS (UI LABELS & MESSAGES)

### webui.py — English Labels

- Line 250: `"Airflow Lite"` — Brand name
- Line 251: `"Read-only operations workspace"` — Tagline
- Line 276: `"Ops Console"` — Header tag
- Line 321: `"Configured Pipelines"` — Summary tile label
- Line 321: `"Total pipeline inventory"` — Summary detail
- Line 322: `"Healthy Last Run"` — Summary tile label
- Line 322: `"Most recent run succeeded"` — Summary detail
- Line 324: `"Active Runs"` — Summary tile label
- Line 324: `"Running / queued / pending"` — Summary detail
- Line 328: `"Failed Last Run"` — Summary tile label
- Line 328: `"Requires operator attention"` — Summary detail
- Line 336: `"never-run"` — Default status when no runs exist
- Line 384: `"No pipelines configured."` — Empty state message
- Line 392: `"Pipeline Inventory"` — Section eyebrow
- Line 393: `"All configured pipelines"` — Section title
- Line 403: `"Pipeline / Table"` — Table header
- Line 404: `"Recent Runs (oldest→latest)"` — Table header
- Line 405: `"Status"` — Table header (appears multiple times)
- Line 406: `"Trigger"` — Table header
- Line 407: `"Duration"` — Table header (appears multiple times)
- Line 408: `"Last Run"` — Table header
- Line 409: `"Next Run"` — Table header
- Line 410: `"Schedule"` — Table header
- Line 411: `"Detail"` — Table header
- Line 420: `"Airflow Lite Monitor"` — Page title
- Line 421: `"Pipeline inventory with run-status grid, duration, next scheduled run, and inline error summary."` — Subtitle
- Line 520: `"Run Detail"` — Section eyebrow
- Line 537: `"Step Timeline"` — Section eyebrow
- Line 538: `"Gantt view — {len(steps)} step(s)"` — Section title
- Line 540: `"← Pipelines"` — Back link
- Line 546: `"Step"` — Table header
- Line 548: `"Timeline (relative)"` — Table header
- Line 550: `"Records"` — Table header
- Line 551: `"Retries"` — Table header
- Line 560: `"Run Detail — {pipeline_name}"` — Page title
- Line 561: `"Step-level execution timeline · {run.get('execution_date', '')} · {run_status}"` — Subtitle
- Line 568: `"Run Timeline"` — Page tag
- Line 580: `"Unavailable"` — Section eyebrow
- Line 580: `"Required service is not configured"` — Section title
- Line 581: `"blocked"` — Status badge
- Line 584: `"Enable the analytics mart and export service wiring to use this screen."` — Message
- Line 593: `"Service Status"` — Page tag
- Line 630: `"Dashboard"` — Summary tile label
- Line 630: `"Contract-backed dashboard view"` — Summary detail
- Line 631: `"Charts"` — Summary tile label
- Line 631: `"Rendered from query endpoints"` — Summary detail
- Line 633: `"Active Filters"` — Summary tile label
- Line 635: `"Current filter state in the URL"` — Summary detail
- Line 638: `"Recent Jobs"` — Summary tile label
- Line 638: `"Latest exports for this dataset"` — Summary detail
- Line 622: `"No dashboard filters defined."` — Empty state
- Line 627: `"No filters applied"` — Default chip text
- Line 643: `"Dashboard Metadata"` — Panel eyebrow
- Line 744: `"Filter Bar"` — Panel eyebrow
- Line 744: `"Apply dashboard state"` — Panel title
- Line 745: `"Read-only controls backed by the dashboard contract"` — Muted text
- Line 752: `"Apply Filters"` — Button text
- Line 753: `"Reset"` — Button text
- Line 753: `"Dashboard API"` — Button text
- Line 761: `"Dataset Overview"` — Panel eyebrow
- Line 761: `"Summary cards"` — Panel title
- Line 762: `"Current filter state is reflected across every card and chart"` — Muted text
- Line 767: `"Charts"` — Panel eyebrow
- Line 767: `"Read-only query outputs"` — Panel title
- Line 773: `"Drilldown Preview"` — Panel eyebrow
- Line 773: `"Source Files"` — Panel title
- Line 774: `"Top rows from the current drilldown endpoint"` — Muted text
- Line 781: `"Exports"` — Panel eyebrow
- Line 781: `"Queue Export"` — Panel title
- Line 782: `"Submit via dashboard actions"` — Muted text
- Line 788: `"Recent Jobs"` — Panel eyebrow
- Line 788: `"Latest export activity"` — Panel title
- Line 789: `"Full export monitor →"` — Link text
- Line 802: `"Analytics Dashboard"` — Page title
- Line 803: `"Read-only dashboard workspace — summary metrics, charts, drilldown preview, and export actions."` — Subtitle
- Line 811: `"Analytics Workspace"` — Page tag
- Line 829: `"Queued"` — Summary tile label
- Line 829: `"Waiting for background worker"` — Summary detail
- Line 833: `"Running"` — Summary tile label
- Line 833: `"Artifacts being generated"` — Summary detail
- Line 837: `"Completed"` — Summary tile label
- Line 837: `"Available for download"` — Summary detail
- Line 840: `"Retention"` — Summary tile label
- Line 840: `"Hours before automatic cleanup"` — Summary detail
- Line 848: `"Not ready"` — Cell text when download not available
- Line 858: `"Delete this job?"` — JavaScript confirm dialog
- Line 893: `"Retention Policy"` — Panel eyebrow
- Line 893: `"Export Job Monitor"` — Panel title
- Line 898: `"Artifacts and job records are retained for {retention_hours} hour(s) before automatic cleanup."` — Message
- Line 900: `"All datasets"` — Button text
- Line 901: `"← Analytics"` — Button text
- Line 904: `"Delete all completed export jobs?"` — JavaScript confirm dialog
- Line 904: `"Delete All Completed"` — Button text
- Line 910: `"Job Inventory"` — Panel eyebrow
- Line 910: `"Export job listing"` — Panel title
- Line 911: `"Running jobs highlighted with pulse indicator"` — Muted text
- Line 917: `"Job ID"` — Table header
- Line 917: `"Dataset"` — Table header
- Line 917: `"Action"` — Table header
- Line 918: `"Format"` — Table header
- Line 918: `"Rows"` — Table header
- Line 918: `"Created"` — Table header
- Line 918: `"Updated"` — Table header
- Line 919: `"Expires"` — Table header
- Line 919: `"Download"` — Table header
- Line 919: `"Error"` — Table header
- Line 919: `"Admin"` — Table header
- Line 881: `"No export jobs recorded."` — Empty state
- Line 928: `"Export Jobs"` — Page title
- Line 929: `"Async export job monitor — status, retention, artifact availability, and download links."` — Subtitle
- Line 936: `"Export Workspace"` — Page tag
- Line 93: `"No runs"` — Run grid empty state

### webui.py — Korean (한글) Labels

- Line 355: `"상세"` — Detail link text
- Line 396: `"최근 완료:"` — "Latest completion:"
- Line 396: `"없음"` — "None"
- Line 396: `"30초마다 자동 갱신"` — "Auto-refresh every 30 seconds"
- Line 733: `"60초마다 자동 갱신"` — "Auto-refresh every 60 seconds"
- Line 895: `"{refresh_secs}초마다 자동 갱신"` — "Auto-refresh every X seconds"

### web.py — Text Strings

- Line 128: `"Run Detail"` — Title in error response
- Line 129: `"Repository is not configured for this runtime."` — Error message
- Line 139: `"Run Detail"` — Title in error response
- Line 140: `"Run '{run_id}' not found for pipeline '{name}'."` — Error message
- Line 164: `"Analytics Dashboard"` — Title
- Line 165: `"Analytics query service is not configured for this runtime."` — Error message
- Line 166: `"/monitor/analytics"` — Active path
- Line 253: `"Export Jobs"` — Title
- Line 254: `"Analytics query service or export service is not configured for this runtime."` — Error message
- Line 255: `"/monitor/exports"` — Active path
- Line 303: `"Export Jobs"` — Title
- Line 304: `"Export service is not configured for this runtime."` — Error message
- Line 356: `"Export Jobs"` — Title (multiple locations)

### dependencies.py — Text Strings

- Line 7: `"analytics query service is not configured."` — Error detail
- Line 14: `"analytics export service is not configured."` — Error detail

---

## 3. HARDCODED CSS / STYLING VALUES

### webui.py (Lines 120-215, _CSS 변수)

#### Color Palette (CSS variables)

- Line 122: `--bg:#f4f7fb` — Background color
- Line 122: `--bg-strong:#e9eef6` — Strong background
- Line 122: `--panel:#fff` — Panel background
- Line 122: `--panel-soft:#f8fbff` — Soft panel background
- Line 122: `--ink:#1f2937` — Text color
- Line 122: `--muted:#667085` — Muted text
- Line 122: `--line:#d6deea` — Border color
- Line 122: `--line-strong:#bfcade` — Strong border
- Line 123: `--topbar:#12263f` — Top bar background
- Line 123: `--topbar-strong:#0d1c30` — Strong top bar
- Line 123: `--brand:#00a7e1` — Brand color
- Line 123: `--accent:#017cee` — Accent color
- Line 124: `--accent-soft:rgba(1,124,238,.08)` — Soft accent
- Line 125: `--ok:#0f9d58` — Success color
- Line 125: `--warn:#f79009` — Warning color
- Line 125: `--bad:#d92d20` — Error color
- Line 125: `--neutral:#7a8699` — Neutral color
- Line 125: `--shadow:0 12px 34px rgba(15,23,42,.08)` — Shadow

#### Spacing & Sizing

- Line 127: `box-sizing:border-box` — CSS box model
- Line 128: `max-width:1400px` — Page max width
- Line 132: `padding-left:20px; padding-right:20px` — Horizontal padding
- Line 133: `padding-top:18px; padding-bottom:18px` — Masthead vertical padding
- Line 133: `padding-top:20px; padding-bottom:40px` — Page vertical padding
- Line 134: `gap:16px` — Default gap
- Line 136: `width:12px; height:12px` — Brand mark size
- Line 137: `box-shadow:0 0 0 5px rgba(90,216,255,.16)` — Brand mark shadow
- Line 138: `gap:2px` — Brand copy gap
- Line 139: `gap:12px` — Utility links gap
- Line 140: `gap:10px` — Chip list gap
- Line 141: `padding:9px 14px` — Button padding
- Line 141: `border-radius:10px` — Button border radius
- Line 142: `padding:9px 14px` — Link padding
- Line 143: `font-size:clamp(1.8rem,4vw,2.8rem)` — Responsive title
- Line 144: `padding:14px 16px 12px` — Nav link padding
- Line 146: `border-radius:16px` — Card border radius
- Line 147: `padding:18px 20px` — Card padding
- Line 147: `padding:16px 18px` — Subpanel padding
- Line 148: `gap:8px` — Tag/chip gap
- Line 148: `padding:6px 10px` — Tag/chip padding
- Line 148: `border-radius:999px` — Pill shape border radius
- Line 148: `font-size:.82rem` — Tag font size
- Line 152: `gap:14px` — Default vertical gap
- Line 154: `gap:6px` — Filter field gap
- Line 155: `grid-template-columns:minmax(0,1.35fr) minmax(320px,.85fr)` — 2-column grid layout
- Line 156: `grid-template-columns:repeat(3,minmax(0,1fr))` — 3-column grid layout
- Line 157: `grid-template-columns:repeat(auto-fit,minmax(200px,1fr))` — Summary grid
- Line 158: `border-top:4px solid` — Top border width
- Line 161: `font-size:.76rem` — Label font size
- Line 162: `font-size:clamp(1.5rem,3vw,2.25rem)` — Summary value size
- Line 163: `font-size:.92rem` — Detail text size
- Line 164: `font-size:.88rem` — Dense cell text size
- Line 165: `font-size:1.2rem` — H2 size
- Line 165: `font-size:.76rem` — Eyebrow font size
- Line 166: `grid-template-columns:repeat(auto-fit,minmax(150px,1fr))` — Meta grid
- Line 167: `padding:12px 14px` — Meta grid cell padding
- Line 169: `padding:6px 10px` — Status badge padding
- Line 169: `font-size:.8rem` — Status font size
- Line 170: `width:8px; height:8px` — Status dot size
- Line 171: `width:6px; height:6px` — Chip dot size
- Line 175: `animation:pulse 1.2s ease-in-out infinite` — Pulse animation
- Line 176: Pulse keyframes with `0%,100%` and `50%` with opacity
- Line 177: `border:1px solid` — Table border
- Line 177: `border-radius:12px` — Table wrapper radius
- Line 178: `padding:11px 12px` — Table cell padding
- Line 178: `min-width:720px` — Minimum table width
- Line 180: `grid-template-columns:repeat(auto-fit,minmax(220px,1fr))` — Filter grid
- Line 181: `padding:10px 12px` — Select padding
- Line 181: `border-radius:10px` — Select border radius
- Line 183: `grid-template-columns:minmax(120px,200px) minmax(0,1fr) auto` — Chart row layout
- Line 184: `height:10px` — Chart bar height
- Line 185: `background:linear-gradient(90deg,#00a7e1,#017cee)` — Chart bar gradient
- Line 186: `box-shadow:inset 3px 0 0` — Highlight shadow
- Line 189: `gap:3px` — Run grid gap
- Line 190: `width:14px; height:14px` — Run block size
- Line 190: `border-radius:3px` — Run block border radius
- Line 191: `transform:scale(1.35)` — Run block hover scale
- Line 196: `font-size:.8rem` — Error inline font size
- Line 196: `max-width:360px` — Error inline max width
- Line 198: `font-size:.78rem` — Refresh notice font size
- Line 201: `padding:9px 10px` — Gantt table cell padding
- Line 204: `height:18px` — Gantt track height
- Line 204: `min-width:160px` — Gantt track min width
- Line 205: `height:100%` — Gantt bar full height
- Line 205: `min-width:3px` — Gantt bar minimum width
- Line 208: `font-size:.78rem` — Step error font size
- Line 210: `max-width:1080px` — Media query breakpoint 1
- Line 211: `max-width:760px` — Media query breakpoint 2

---

## 4. HARDCODED NUMERIC CONSTANTS (Timeouts, Intervals, Page Sizes, Limits)

### webui.py

- Line 110: `120` — Max error message length (characters)
- Line 396: `30` — Auto-refresh seconds for Monitor page
- Line 429: `30` — Auto-refresh interval (seconds)
- Line 615: `max(2, min(6, len(filter_def["options"]) or 2))` — Filter select size (2-6)
- Line 733: `60` — Auto-refresh seconds for Analytics page
- Line 812: `60` — Auto-refresh interval for analytics (seconds)
- Line 840: `{retention_hours}h` — Retention display from config (variable, not hardcoded)
- Line 887: `10` and `30` — Auto-refresh interval based on active jobs (10 if active, 30 if not)
- Line 937: `refresh_secs` — Variable refresh interval for exports page

### web.py

- Line 96: `limit=25` — Maximum recent runs per grid (25 runs)
- Line 156: `default="mes_ops"` — Default dataset query parameter
- Line 157: `default="operations_overview"` — Default dashboard_id query parameter
- Line 210: `page_size=8` — Detail preview page size (8 rows)
- Line 219: `limit=8` — Recent export jobs limit (8 jobs)
- Line 266: `default="mes_ops"` — Form default dataset
- Line 267: `default="operations_overview"` — Form default dashboard_id
- Line 363: `limit=50` — Export jobs list limit (50 jobs)

### routes/pipelines.py

- Line 88: `page: int = 1` — Default page
- Line 88: `page_size: int = 50` — Default page size (50 items)

### analytics_contracts.py

- Line 132: `default=31, ge=1, le=366` — Chart limit: default 31, max 366
- Line 174: `default=50, ge=1, le=500` — Detail page_size: default 50, max 500
- Line 202: `/api/v1/analytics/summary` — Hardcoded endpoint in card definition
- Line 216: `default=12, ge=1, le=366` — Chart limit: default 12, max 366
- Line 236: `"dashboard.v1"` — Contract version (hardcoded default)

---

## 5. HARDCODED CONFIGURATION VALUES

### app.py

- Line 44-46: FastAPI app metadata (hardcoded):
  - `title="Airflow Lite API"`
  - `version="1.0.0"`

### analytics_contracts.py (Default values)

- Line 202: Default summary endpoint: `"/api/v1/analytics/summary"`
- Line 203: Default request method: `DashboardRequestMethod.POST`
- Line 214: Default request method: `DashboardRequestMethod.POST`
- Line 216: Default chart limit: `12`
- Line 217: Default chart span: `DashboardLayoutSpan.LARGE`
- Line 224: Default action status: `DashboardActionStatus.PLANNED`
- Line 226: Default action scope: `DashboardActionScope.DASHBOARD`
- Line 236: Contract version: `"dashboard.v1"`

---

## 6. HARDCODED JAVASCRIPT IN HTML STRINGS

### webui.py

- Line 858: `onclick="return confirm('Delete this job?')"` — JavaScript confirm dialog
- Line 904: `onclick="return confirm('Delete all completed export jobs?')"` — JavaScript confirm dialog
- Line 751: Button inline style: `style="display:inline"` — CSS inline display in form

---

## SUMMARY TABLE BY FILE

| File | Category | Count | Lines |
|------|----------|-------|-------|
| webui.py | URL Paths | 21 | 255-808 |
| webui.py | Text Labels (EN) | 80+ | 250-936 |
| webui.py | Text Labels (KR) | 5 | 396, 733, 895 |
| webui.py | CSS Colors & Styling | 50+ | 120-215 |
| webui.py | Numeric Constants | 8 | 110, 396, 429, 615, 733, 812, 887, 937 |
| webui.py | JavaScript | 2 | 858, 904 |
| web.py | URL Paths | 10 | 76-320 |
| web.py | Numeric Constants | 8 | 96, 156-157, 210, 219, 266-267, 363 |
| web.py | Text Strings | 20+ | 128-356 |
| routes/pipelines.py | Numeric Constants | 2 | 88 |
| analytics_contracts.py | Numeric Constants | 6 | 132, 174, 216 |
| analytics_contracts.py | Configuration Values | 7 | 202-236 |
| dependencies.py | Text Strings | 2 | 7, 14 |
| app.py | Configuration Values | 2 | 44-46 |
