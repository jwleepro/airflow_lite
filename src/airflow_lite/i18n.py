from __future__ import annotations

from typing import Final

DEFAULT_LANGUAGE: Final[str] = "en"
SUPPORTED_LANGUAGES: Final[frozenset[str]] = frozenset({"en", "ko"})

_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "en": {
        # analytics labels
        "analytics.filter.source.label": "Source Table",
        "analytics.filter.partition_month.label": "Partition Month",
        "analytics.dashboard.operations_overview.title": "MES Operations Overview",
        "analytics.dashboard.operations_overview.description": (
            "Promoted mart coverage and refresh health view for MES datasets."
        ),
        "analytics.dashboard.card.rows_loaded.label": "Rows Loaded",
        "analytics.dashboard.card.rows_loaded.description": "Total rows covered by the current mart selection.",
        "analytics.dashboard.card.source_files.label": "Source Files",
        "analytics.dashboard.card.source_files.description": "Parquet file count backing the selected view.",
        "analytics.dashboard.card.source_tables.label": "Source Tables",
        "analytics.dashboard.card.source_tables.description": (
            "Distinct raw sources currently represented in the mart."
        ),
        "analytics.dashboard.card.covered_months.label": "Covered Months",
        "analytics.dashboard.card.covered_months.description": (
            "Number of month partitions included in the response window."
        ),
        "analytics.dashboard.card.avg_rows_per_file.label": "Avg Rows per File",
        "analytics.dashboard.card.avg_rows_per_file.description": (
            "Average row density across the selected parquet files."
        ),
        "analytics.chart.rows_by_month.title": "Rows by Month",
        "analytics.chart.files_by_source.title": "Files by Source",
        "analytics.chart.series.rows": "Rows Loaded",
        "analytics.chart.series.files": "Files",
        "analytics.chart.rows_by_month.granularity_normalized": (
            "rows_by_month uses month buckets; granularity was normalized to month."
        ),
        "analytics.action.source_file_detail.label": "Source File Detail",
        "analytics.action.source_file_detail.description": (
            "Detail grid for source-level file records and partition slices."
        ),
        "analytics.action.csv_zip_export.label": "CSV Zip Export",
        "analytics.action.csv_zip_export.description": "Large-result export workflow for downstream analysis.",
        "analytics.action.parquet_export.label": "Parquet Export",
        "analytics.action.parquet_export.description": "Raw-compatible export for bulk data reuse.",
        "analytics.metric.rows_loaded.label": "Rows Loaded",
        "analytics.metric.rows_loaded.unit": "rows",
        "analytics.metric.source_files.label": "Source Files",
        "analytics.metric.source_files.unit": "files",
        "analytics.metric.source_tables.label": "Source Tables",
        "analytics.metric.source_tables.unit": "tables",
        "analytics.metric.avg_rows_per_file.label": "Avg Rows per File",
        "analytics.metric.avg_rows_per_file.unit": "rows",
        "analytics.metric.covered_months.label": "Covered Months",
        "analytics.metric.covered_months.unit": "months",
        "analytics.detail.column.source_name": "Source Table",
        "analytics.detail.column.partition_month": "Partition Month",
        "analytics.detail.column.file_path": "File Path",
        "analytics.detail.column.row_count": "Rows",
        "analytics.detail.column.last_build_id": "Build ID",
        # web ui labels
        "webui.layout.brand_subtitle": "Read-only operations workspace",
        "webui.layout.link.swagger": "Swagger",
        "webui.layout.link.pipeline_api": "Pipeline API",
        "webui.layout.nav.pipelines": "Pipelines",
        "webui.layout.nav.analytics": "Analytics",
        "webui.layout.nav.exports": "Exports",
        "webui.layout.header_tag.ops_console": "Ops Console",
        "webui.layout.page_tag.operations_console": "Operations Console",
        "webui.layout.page_tag.run_timeline": "Run Timeline",
        "webui.layout.page_tag.analytics_workspace": "Analytics Workspace",
        "webui.layout.page_tag.export_workspace": "Export Workspace",
        "webui.layout.page_tag.service_status": "Service Status",
        "webui.run.no_run": "no run",
        "webui.monitor.summary.configured_pipelines.label": "Configured Pipelines",
        "webui.monitor.summary.configured_pipelines.detail": "Total pipeline inventory",
        "webui.monitor.summary.healthy_last_run.label": "Healthy Last Run",
        "webui.monitor.summary.healthy_last_run.detail": "Most recent run succeeded",
        "webui.monitor.summary.active_runs.label": "Active Runs",
        "webui.monitor.summary.active_runs.detail": "Running / queued / pending",
        "webui.monitor.summary.failed_last_run.label": "Failed Last Run",
        "webui.monitor.summary.failed_last_run.detail": "Requires operator attention",
        "webui.monitor.inventory.eyebrow": "Pipeline Inventory",
        "webui.monitor.inventory.title": "All configured pipelines",
        "webui.monitor.inventory.refresh_notice": "Last finished: {latest_finish} · Auto-refresh every {seconds}s",
        "webui.monitor.inventory.none": "none",
        "webui.monitor.detail_link": "Detail",
        "webui.monitor.empty.no_pipelines": "No pipelines configured.",
        "webui.monitor.table.pipeline_table": "Pipeline / Table",
        "webui.monitor.table.recent_runs": "Recent Runs (oldest→latest)",
        "webui.monitor.table.status": "Status",
        "webui.monitor.table.trigger": "Trigger",
        "webui.monitor.table.duration": "Duration",
        "webui.monitor.table.last_run": "Last Run",
        "webui.monitor.table.next_run": "Next Run",
        "webui.monitor.table.schedule": "Schedule",
        "webui.monitor.table.detail": "Detail",
        "webui.monitor.title": "Airflow Lite Monitor",
        "webui.monitor.subtitle": (
            "Pipeline inventory with run-status grid, duration, next scheduled run, and inline error summary."
        ),
        "webui.monitor.hero.pipelines_api": "Pipelines API",
        "webui.monitor.hero.analytics": "Analytics",
        "webui.monitor.hero.exports": "Exports",
        "webui.run_detail.eyebrow": "Run Detail",
        "webui.run_detail.meta.run_id": "Run ID",
        "webui.run_detail.meta.trigger": "Trigger",
        "webui.run_detail.meta.duration": "Duration",
        "webui.run_detail.meta.schedule": "Schedule",
        "webui.run_detail.meta.started": "Started",
        "webui.run_detail.meta.finished": "Finished",
        "webui.run_detail.timeline.eyebrow": "Step Timeline",
        "webui.run_detail.timeline.title": "Gantt view — {count} step(s)",
        "webui.run_detail.back_to_pipelines": "← Pipelines",
        "webui.run_detail.table.step": "Step",
        "webui.run_detail.table.status": "Status",
        "webui.run_detail.table.timeline": "Timeline (relative)",
        "webui.run_detail.table.duration": "Duration",
        "webui.run_detail.table.records": "Records",
        "webui.run_detail.table.retries": "Retries",
        "webui.run_detail.empty.no_step_records": "No step records.",
        "webui.run_detail.title": "Run Detail — {pipeline_name}",
        "webui.run_detail.subtitle": "Step-level execution timeline · {execution_date} · {run_status}",
        "webui.run_detail.hero.all_runs_api": "All Runs API",
        "webui.run_detail.hero.this_run_api": "This Run API",
        "webui.unavailable.eyebrow": "Unavailable",
        "webui.unavailable.title": "Required service is not configured",
        "webui.unavailable.status": "blocked",
        "webui.unavailable.enable_hint": "Enable the analytics mart and export service wiring to use this screen.",
        "webui.unavailable.hero.pipelines": "Pipelines",
        "webui.unavailable.hero.swagger": "Swagger",
        "webui.analytics.empty.no_dashboard_filters": "No dashboard filters defined.",
        "webui.analytics.filters.none_applied": "No filters applied",
        "webui.analytics.summary.dashboard.label": "Dashboard",
        "webui.analytics.summary.dashboard.detail": "Contract-backed dashboard view",
        "webui.analytics.summary.charts.label": "Charts",
        "webui.analytics.summary.charts.detail": "Rendered from query endpoints",
        "webui.analytics.summary.active_filters.label": "Active Filters",
        "webui.analytics.summary.active_filters.detail": "Current filter state in the URL",
        "webui.analytics.summary.recent_jobs.label": "Recent Jobs",
        "webui.analytics.summary.recent_jobs.detail": "Latest exports for this dataset",
        "webui.analytics.metric.no_unit": "No unit",
        "webui.analytics.metric.default_description": "Dashboard summary metric",
        "webui.analytics.empty.no_summary_cards": "No summary cards available.",
        "webui.analytics.empty.no_chart_data": "No chart data for current filters.",
        "webui.analytics.chart.eyebrow": "Chart",
        "webui.analytics.chart.query_api": "Query API",
        "webui.analytics.empty.no_charts": "No charts available.",
        "webui.analytics.empty.no_drilldown_preview": "No drilldown preview available.",
        "webui.analytics.empty.no_rows": "No rows.",
        "webui.analytics.empty.no_export_actions": "No export actions available.",
        "webui.analytics.empty.no_export_jobs": "No export jobs yet.",
        "webui.analytics.metadata.eyebrow": "Dashboard Metadata",
        "webui.analytics.metadata.refresh_notice": "Auto-refresh every {seconds}s",
        "webui.analytics.metadata.dashboard_id": "Dashboard ID",
        "webui.analytics.metadata.dataset": "Dataset",
        "webui.analytics.metadata.last_refreshed": "Last Refreshed",
        "webui.analytics.metadata.contract": "Contract",
        "webui.analytics.filter_bar.eyebrow": "Filter Bar",
        "webui.analytics.filter_bar.title": "Apply dashboard state",
        "webui.analytics.filter_bar.readonly_hint": "Read-only controls backed by the dashboard contract",
        "webui.analytics.filter_bar.apply_filters": "Apply Filters",
        "webui.analytics.filter_bar.reset": "Reset",
        "webui.analytics.filter_bar.dashboard_api": "Dashboard API",
        "webui.analytics.dataset_overview.eyebrow": "Dataset Overview",
        "webui.analytics.dataset_overview.title": "Summary cards",
        "webui.analytics.dataset_overview.hint": "Current filter state is reflected across every card and chart",
        "webui.analytics.charts.eyebrow": "Charts",
        "webui.analytics.charts.title": "Read-only query outputs",
        "webui.analytics.drilldown.eyebrow": "Drilldown Preview",
        "webui.analytics.drilldown.title": "Source Files",
        "webui.analytics.drilldown.hint": "Top rows from the current drilldown endpoint",
        "webui.analytics.exports.eyebrow": "Exports",
        "webui.analytics.exports.title": "Queue Export",
        "webui.analytics.exports.hint": "Submit via dashboard actions",
        "webui.analytics.recent_jobs.eyebrow": "Recent Jobs",
        "webui.analytics.recent_jobs.title": "Latest export activity",
        "webui.analytics.recent_jobs.full_monitor": "Full export monitor →",
        "webui.analytics.recent_jobs.table.job_id": "Job ID",
        "webui.analytics.recent_jobs.table.status": "Status",
        "webui.analytics.recent_jobs.table.format": "Format",
        "webui.analytics.recent_jobs.table.updated": "Updated",
        "webui.analytics.title": "Analytics Dashboard",
        "webui.analytics.subtitle": (
            "Read-only dashboard workspace — summary metrics, charts, drilldown preview, and export actions."
        ),
        "webui.analytics.hero.dashboard_api": "Dashboard API",
        "webui.analytics.hero.filters_api": "Filters API",
        "webui.analytics.hero.export_monitor": "Export Monitor",
        "webui.exports.summary.queued.label": "Queued",
        "webui.exports.summary.queued.detail": "Waiting for background worker",
        "webui.exports.summary.running.label": "Running",
        "webui.exports.summary.running.detail": "Artifacts being generated",
        "webui.exports.summary.completed.label": "Completed",
        "webui.exports.summary.completed.detail": "Available for download",
        "webui.exports.summary.retention.label": "Retention",
        "webui.exports.summary.retention.detail": "Hours before automatic cleanup",
        "webui.exports.download": "Download",
        "webui.exports.not_ready": "Not ready",
        "webui.exports.delete": "Delete",
        "webui.exports.confirm.delete_job": "Delete this job?",
        "webui.exports.empty.no_jobs": "No export jobs recorded.",
        "webui.exports.retention.eyebrow": "Retention Policy",
        "webui.exports.retention.title": "Export Job Monitor",
        "webui.exports.retention.refresh_notice": "Filtered: {dataset} · Auto-refresh every {seconds}s",
        "webui.exports.retention.all_datasets": "all datasets",
        "webui.exports.retention.description": (
            "Artifacts and job records are retained for {hours} hour(s) before automatic cleanup."
        ),
        "webui.exports.actions.all_datasets": "All datasets",
        "webui.exports.actions.analytics": "← Analytics",
        "webui.exports.actions.delete_all_completed": "Delete All Completed",
        "webui.exports.confirm.delete_all_completed": "Delete all completed export jobs?",
        "webui.exports.inventory.eyebrow": "Job Inventory",
        "webui.exports.inventory.title": "Export job listing",
        "webui.exports.inventory.hint": "Running jobs highlighted with pulse indicator",
        "webui.exports.table.job_id": "Job ID",
        "webui.exports.table.dataset": "Dataset",
        "webui.exports.table.action": "Action",
        "webui.exports.table.status": "Status",
        "webui.exports.table.format": "Format",
        "webui.exports.table.rows": "Rows",
        "webui.exports.table.created": "Created",
        "webui.exports.table.updated": "Updated",
        "webui.exports.table.expires": "Expires",
        "webui.exports.table.download": "Download",
        "webui.exports.table.error": "Error",
        "webui.exports.table.admin": "Admin",
        "webui.exports.title": "Export Jobs",
        "webui.exports.subtitle": (
            "Async export job monitor — status, retention, artifact availability, and download links."
        ),
        "webui.exports.hero.analytics": "Analytics",
        "webui.exports.hero.export_api": "Export API",
    },
    "ko": {
        # analytics labels
        "analytics.filter.source.label": "원본 테이블",
        "analytics.filter.partition_month.label": "파티션 월",
        "analytics.dashboard.operations_overview.title": "MES 운영 개요",
        "analytics.dashboard.operations_overview.description": "MES 데이터셋의 mart 반영 범위와 갱신 상태를 보여줍니다.",
        "analytics.dashboard.card.rows_loaded.label": "적재 행 수",
        "analytics.dashboard.card.rows_loaded.description": "현재 mart 선택 기준에 포함된 전체 행 수입니다.",
        "analytics.dashboard.card.source_files.label": "원본 파일 수",
        "analytics.dashboard.card.source_files.description": "현재 조회 기준을 구성하는 Parquet 파일 수입니다.",
        "analytics.dashboard.card.source_tables.label": "원본 테이블 수",
        "analytics.dashboard.card.source_tables.description": "mart에 반영된 원본 소스 테이블의 개수입니다.",
        "analytics.dashboard.card.covered_months.label": "커버 월 수",
        "analytics.dashboard.card.covered_months.description": "현재 응답 구간에 포함된 월 파티션 개수입니다.",
        "analytics.dashboard.card.avg_rows_per_file.label": "파일당 평균 행 수",
        "analytics.dashboard.card.avg_rows_per_file.description": "선택된 Parquet 파일의 평균 행 밀도입니다.",
        "analytics.chart.rows_by_month.title": "월별 적재 행 수",
        "analytics.chart.files_by_source.title": "소스별 파일 수",
        "analytics.chart.series.rows": "적재 행 수",
        "analytics.chart.series.files": "파일 수",
        "analytics.chart.rows_by_month.granularity_normalized": "rows_by_month는 월 단위 버킷만 지원하여 granularity를 month로 보정했습니다.",
        "analytics.action.source_file_detail.label": "소스 파일 상세",
        "analytics.action.source_file_detail.description": "소스별 파일 레코드와 파티션 구간 상세를 조회합니다.",
        "analytics.action.csv_zip_export.label": "CSV ZIP 내보내기",
        "analytics.action.csv_zip_export.description": "후속 분석을 위한 대용량 결과 내보내기 워크플로입니다.",
        "analytics.action.parquet_export.label": "Parquet 내보내기",
        "analytics.action.parquet_export.description": "대용량 재사용을 위한 원본 호환 내보내기입니다.",
        "analytics.metric.rows_loaded.label": "적재 행 수",
        "analytics.metric.rows_loaded.unit": "행",
        "analytics.metric.source_files.label": "원본 파일 수",
        "analytics.metric.source_files.unit": "파일",
        "analytics.metric.source_tables.label": "원본 테이블 수",
        "analytics.metric.source_tables.unit": "테이블",
        "analytics.metric.avg_rows_per_file.label": "파일당 평균 행 수",
        "analytics.metric.avg_rows_per_file.unit": "행",
        "analytics.metric.covered_months.label": "커버 월 수",
        "analytics.metric.covered_months.unit": "개월",
        "analytics.detail.column.source_name": "원본 테이블",
        "analytics.detail.column.partition_month": "파티션 월",
        "analytics.detail.column.file_path": "파일 경로",
        "analytics.detail.column.row_count": "행 수",
        "analytics.detail.column.last_build_id": "빌드 ID",
        # web ui labels
        "webui.layout.brand_subtitle": "읽기 전용 운영 워크스페이스",
        "webui.layout.link.swagger": "Swagger",
        "webui.layout.link.pipeline_api": "파이프라인 API",
        "webui.layout.nav.pipelines": "파이프라인",
        "webui.layout.nav.analytics": "분석",
        "webui.layout.nav.exports": "내보내기",
        "webui.layout.header_tag.ops_console": "운영 콘솔",
        "webui.layout.page_tag.operations_console": "운영 콘솔",
        "webui.layout.page_tag.run_timeline": "실행 타임라인",
        "webui.layout.page_tag.analytics_workspace": "분석 워크스페이스",
        "webui.layout.page_tag.export_workspace": "내보내기 워크스페이스",
        "webui.layout.page_tag.service_status": "서비스 상태",
        "webui.run.no_run": "실행 없음",
        "webui.monitor.summary.configured_pipelines.label": "설정된 파이프라인",
        "webui.monitor.summary.configured_pipelines.detail": "전체 파이프라인 목록",
        "webui.monitor.summary.healthy_last_run.label": "최근 성공",
        "webui.monitor.summary.healthy_last_run.detail": "최근 실행이 성공한 파이프라인",
        "webui.monitor.summary.active_runs.label": "활성 실행",
        "webui.monitor.summary.active_runs.detail": "실행중 / 대기 / 예약",
        "webui.monitor.summary.failed_last_run.label": "최근 실패",
        "webui.monitor.summary.failed_last_run.detail": "운영자 확인이 필요한 실패",
        "webui.monitor.inventory.eyebrow": "파이프라인 인벤토리",
        "webui.monitor.inventory.title": "전체 설정 파이프라인",
        "webui.monitor.inventory.refresh_notice": "최근 완료: {latest_finish} · {seconds}초마다 자동 갱신",
        "webui.monitor.inventory.none": "없음",
        "webui.monitor.detail_link": "상세",
        "webui.monitor.empty.no_pipelines": "설정된 파이프라인이 없습니다.",
        "webui.monitor.table.pipeline_table": "파이프라인 / 테이블",
        "webui.monitor.table.recent_runs": "최근 실행 (오래된 순→최신)",
        "webui.monitor.table.status": "상태",
        "webui.monitor.table.trigger": "트리거",
        "webui.monitor.table.duration": "소요 시간",
        "webui.monitor.table.last_run": "최근 실행",
        "webui.monitor.table.next_run": "다음 실행",
        "webui.monitor.table.schedule": "스케줄",
        "webui.monitor.table.detail": "상세",
        "webui.monitor.title": "Airflow Lite 모니터",
        "webui.monitor.subtitle": "실행 상태 그리드, 소요 시간, 다음 실행 시각, 실패 요약을 한 화면에서 확인합니다.",
        "webui.monitor.hero.pipelines_api": "파이프라인 API",
        "webui.monitor.hero.analytics": "분석",
        "webui.monitor.hero.exports": "내보내기",
        "webui.run_detail.eyebrow": "실행 상세",
        "webui.run_detail.meta.run_id": "실행 ID",
        "webui.run_detail.meta.trigger": "트리거",
        "webui.run_detail.meta.duration": "소요 시간",
        "webui.run_detail.meta.schedule": "스케줄",
        "webui.run_detail.meta.started": "시작 시각",
        "webui.run_detail.meta.finished": "종료 시각",
        "webui.run_detail.timeline.eyebrow": "스텝 타임라인",
        "webui.run_detail.timeline.title": "간트 뷰 — {count}개 스텝",
        "webui.run_detail.back_to_pipelines": "← 파이프라인",
        "webui.run_detail.table.step": "스텝",
        "webui.run_detail.table.status": "상태",
        "webui.run_detail.table.timeline": "타임라인 (상대)",
        "webui.run_detail.table.duration": "소요 시간",
        "webui.run_detail.table.records": "처리 건수",
        "webui.run_detail.table.retries": "재시도",
        "webui.run_detail.empty.no_step_records": "스텝 실행 기록이 없습니다.",
        "webui.run_detail.title": "실행 상세 — {pipeline_name}",
        "webui.run_detail.subtitle": "스텝 단위 실행 타임라인 · {execution_date} · {run_status}",
        "webui.run_detail.hero.all_runs_api": "전체 실행 API",
        "webui.run_detail.hero.this_run_api": "현재 실행 API",
        "webui.unavailable.eyebrow": "사용 불가",
        "webui.unavailable.title": "필수 서비스가 구성되지 않았습니다",
        "webui.unavailable.status": "차단됨",
        "webui.unavailable.enable_hint": "이 화면을 사용하려면 analytics mart와 export 서비스 연결을 활성화하세요.",
        "webui.unavailable.hero.pipelines": "파이프라인",
        "webui.unavailable.hero.swagger": "Swagger",
        "webui.analytics.empty.no_dashboard_filters": "정의된 대시보드 필터가 없습니다.",
        "webui.analytics.filters.none_applied": "적용된 필터 없음",
        "webui.analytics.summary.dashboard.label": "대시보드",
        "webui.analytics.summary.dashboard.detail": "계약 기반 대시보드 뷰",
        "webui.analytics.summary.charts.label": "차트",
        "webui.analytics.summary.charts.detail": "조회 API 결과로 렌더링",
        "webui.analytics.summary.active_filters.label": "활성 필터",
        "webui.analytics.summary.active_filters.detail": "URL에 반영된 현재 필터 상태",
        "webui.analytics.summary.recent_jobs.label": "최근 작업",
        "webui.analytics.summary.recent_jobs.detail": "현재 데이터셋의 최신 export 작업",
        "webui.analytics.metric.no_unit": "단위 없음",
        "webui.analytics.metric.default_description": "대시보드 요약 지표",
        "webui.analytics.empty.no_summary_cards": "요약 카드가 없습니다.",
        "webui.analytics.empty.no_chart_data": "현재 필터에 해당하는 차트 데이터가 없습니다.",
        "webui.analytics.chart.eyebrow": "차트",
        "webui.analytics.chart.query_api": "조회 API",
        "webui.analytics.empty.no_charts": "표시할 차트가 없습니다.",
        "webui.analytics.empty.no_drilldown_preview": "드릴다운 미리보기 데이터가 없습니다.",
        "webui.analytics.empty.no_rows": "행이 없습니다.",
        "webui.analytics.empty.no_export_actions": "사용 가능한 export 액션이 없습니다.",
        "webui.analytics.empty.no_export_jobs": "아직 export 작업이 없습니다.",
        "webui.analytics.metadata.eyebrow": "대시보드 메타데이터",
        "webui.analytics.metadata.refresh_notice": "{seconds}초마다 자동 갱신",
        "webui.analytics.metadata.dashboard_id": "대시보드 ID",
        "webui.analytics.metadata.dataset": "데이터셋",
        "webui.analytics.metadata.last_refreshed": "마지막 갱신",
        "webui.analytics.metadata.contract": "계약 버전",
        "webui.analytics.filter_bar.eyebrow": "필터 바",
        "webui.analytics.filter_bar.title": "대시보드 상태 적용",
        "webui.analytics.filter_bar.readonly_hint": "대시보드 계약을 기반으로 한 읽기 전용 컨트롤",
        "webui.analytics.filter_bar.apply_filters": "필터 적용",
        "webui.analytics.filter_bar.reset": "초기화",
        "webui.analytics.filter_bar.dashboard_api": "대시보드 API",
        "webui.analytics.dataset_overview.eyebrow": "데이터셋 개요",
        "webui.analytics.dataset_overview.title": "요약 카드",
        "webui.analytics.dataset_overview.hint": "현재 필터 상태가 모든 카드와 차트에 반영됩니다.",
        "webui.analytics.charts.eyebrow": "차트",
        "webui.analytics.charts.title": "읽기 전용 조회 결과",
        "webui.analytics.drilldown.eyebrow": "드릴다운 미리보기",
        "webui.analytics.drilldown.title": "소스 파일",
        "webui.analytics.drilldown.hint": "현재 드릴다운 endpoint의 상위 행",
        "webui.analytics.exports.eyebrow": "내보내기",
        "webui.analytics.exports.title": "내보내기 요청",
        "webui.analytics.exports.hint": "대시보드 액션으로 제출",
        "webui.analytics.recent_jobs.eyebrow": "최근 작업",
        "webui.analytics.recent_jobs.title": "최신 내보내기 활동",
        "webui.analytics.recent_jobs.full_monitor": "전체 export 모니터 →",
        "webui.analytics.recent_jobs.table.job_id": "작업 ID",
        "webui.analytics.recent_jobs.table.status": "상태",
        "webui.analytics.recent_jobs.table.format": "포맷",
        "webui.analytics.recent_jobs.table.updated": "갱신 시각",
        "webui.analytics.title": "분석 대시보드",
        "webui.analytics.subtitle": "요약 지표, 차트, 드릴다운 미리보기, export 액션을 제공하는 읽기 전용 워크스페이스",
        "webui.analytics.hero.dashboard_api": "대시보드 API",
        "webui.analytics.hero.filters_api": "필터 API",
        "webui.analytics.hero.export_monitor": "내보내기 모니터",
        "webui.exports.summary.queued.label": "대기",
        "webui.exports.summary.queued.detail": "백그라운드 워커 대기 중",
        "webui.exports.summary.running.label": "실행중",
        "webui.exports.summary.running.detail": "아티팩트 생성 중",
        "webui.exports.summary.completed.label": "완료",
        "webui.exports.summary.completed.detail": "다운로드 가능",
        "webui.exports.summary.retention.label": "보관 기간",
        "webui.exports.summary.retention.detail": "자동 정리 전 보관 시간",
        "webui.exports.download": "다운로드",
        "webui.exports.not_ready": "준비되지 않음",
        "webui.exports.delete": "삭제",
        "webui.exports.confirm.delete_job": "이 작업을 삭제할까요?",
        "webui.exports.empty.no_jobs": "기록된 export 작업이 없습니다.",
        "webui.exports.retention.eyebrow": "보관 정책",
        "webui.exports.retention.title": "Export 작업 모니터",
        "webui.exports.retention.refresh_notice": "필터: {dataset} · {seconds}초마다 자동 갱신",
        "webui.exports.retention.all_datasets": "전체 데이터셋",
        "webui.exports.retention.description": "{hours}시간 동안 작업/아티팩트를 보관한 뒤 자동 정리합니다.",
        "webui.exports.actions.all_datasets": "전체 데이터셋",
        "webui.exports.actions.analytics": "← 분석",
        "webui.exports.actions.delete_all_completed": "완료 작업 전체 삭제",
        "webui.exports.confirm.delete_all_completed": "완료된 export 작업을 모두 삭제할까요?",
        "webui.exports.inventory.eyebrow": "작업 인벤토리",
        "webui.exports.inventory.title": "Export 작업 목록",
        "webui.exports.inventory.hint": "실행중 작업은 pulse 표시로 강조됩니다.",
        "webui.exports.table.job_id": "작업 ID",
        "webui.exports.table.dataset": "데이터셋",
        "webui.exports.table.action": "액션",
        "webui.exports.table.status": "상태",
        "webui.exports.table.format": "포맷",
        "webui.exports.table.rows": "행 수",
        "webui.exports.table.created": "생성 시각",
        "webui.exports.table.updated": "갱신 시각",
        "webui.exports.table.expires": "만료 시각",
        "webui.exports.table.download": "다운로드",
        "webui.exports.table.error": "오류",
        "webui.exports.table.admin": "관리",
        "webui.exports.title": "Export 작업",
        "webui.exports.subtitle": "비동기 export 작업 상태, 보관 기간, 아티팩트 가용성을 확인합니다.",
        "webui.exports.hero.analytics": "분석",
        "webui.exports.hero.export_api": "Export API",
    },
}


def normalize_language(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip().lower()
    if not candidate:
        return None
    candidate = candidate.replace("_", "-")
    primary = candidate.split("-", maxsplit=1)[0]
    if primary in SUPPORTED_LANGUAGES:
        return primary
    return None


def parse_accept_language(value: str | None) -> str | None:
    if not value:
        return None

    best_language: str | None = None
    best_quality = -1.0
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        parts = [segment.strip() for segment in item.split(";")]
        language = normalize_language(parts[0])
        if language is None:
            continue

        quality = 1.0
        for parameter in parts[1:]:
            if not parameter.startswith("q="):
                continue
            try:
                quality = float(parameter[2:])
            except ValueError:
                quality = 0.0
        if quality > best_quality:
            best_quality = quality
            best_language = language
    return best_language


def resolve_language(
    *,
    query_language: str | None = None,
    default_language: str | None = None,
    accept_language: str | None = None,
) -> str:
    for candidate in (
        query_language,
        default_language,
        parse_accept_language(accept_language),
    ):
        normalized = normalize_language(candidate)
        if normalized:
            return normalized
    return DEFAULT_LANGUAGE


def require_supported_language(value: str, *, field_name: str) -> str:
    normalized = normalize_language(value)
    if normalized is None:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ValueError(f"지원되지 않는 언어 값입니다 ({field_name}): {value!r}. 지원값: {supported}")
    return normalized


def translate(key: str, language: str, **kwargs) -> str:
    normalized = normalize_language(language) or DEFAULT_LANGUAGE
    message = _TRANSLATIONS.get(normalized, {}).get(key)
    if message is None:
        message = _TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        return message.format(**kwargs)
    return message
