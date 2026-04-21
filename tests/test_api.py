"""Task-007: FastAPI REST API TestClient 기반 통합 테스트."""
import pytest
import time
from datetime import date, datetime
from urllib.parse import parse_qs, urlparse
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from airflow_lite.api.app import create_app
from airflow_lite.api.analytics_contracts import (
    ChartGranularity,
    ChartQueryResponse,
    ChartSeries,
    ChartPoint,
    SummaryMetricCard,
    SummaryPrecision,
    SummaryQueryResponse,
)
from airflow_lite.query import DuckDBAnalyticsQueryService
from airflow_lite.export import FilesystemAnalyticsExportService
from airflow_lite.config.settings import ApiConfig, PipelineConfig, WebUIConfig
from airflow_lite.service.dispatch_service import PipelineBusyError
from airflow_lite.storage.models import PipelineRun, StepRun


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _make_settings(pipeline_names=("test_pipeline",)):
    """테스트용 Settings 객체 생성."""
    pipelines = [
        PipelineConfig(
            name=name,
            table=name.upper(),
            source_where_template="DATE_COL >= :data_interval_start AND DATE_COL < :data_interval_end",
            strategy="full",
            schedule="0 2 * * *",
        )
        for name in pipeline_names
    ]
    settings = MagicMock()
    settings.pipelines = pipelines
    settings.api = ApiConfig(allowed_origins=["http://10.0.0.1"])
    settings.webui = WebUIConfig()
    return settings


def _make_pipeline_run(
    pipeline_name="test_pipeline",
    run_id="run-001",
    execution_date=date(2026, 1, 1),
    status="success",
    trigger_type="manual",
) -> PipelineRun:
    return PipelineRun(
        id=run_id,
        pipeline_name=pipeline_name,
        execution_date=execution_date,
        status=status,
        started_at=datetime(2026, 1, 1, 2, 0, 0),
        finished_at=datetime(2026, 1, 1, 2, 30, 0),
        trigger_type=trigger_type,
    )


def _make_step_run(pipeline_run_id="run-001") -> StepRun:
    return StepRun(
        id="step-001",
        pipeline_run_id=pipeline_run_id,
        step_name="extract",
        status="success",
        started_at=datetime(2026, 1, 1, 2, 0, 0),
        finished_at=datetime(2026, 1, 1, 2, 10, 0),
        records_processed=1000,
        error_message=None,
        retry_count=0,
    )


def _wait_for_export_completion(client: TestClient, job_id: str) -> dict:
    for _ in range(40):
        response = client.get(f"/api/v1/analytics/exports/{job_id}")
        body = response.json()
        if body["status"] in {"completed", "failed"}:
            return body
        time.sleep(0.05)
    raise AssertionError(f"export job did not finish in time: {job_id}")


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_runner():
    runner = MagicMock()
    run = _make_pipeline_run()
    runner.run.return_value = run
    return runner


@pytest.fixture
def mock_backfill_manager():
    manager = MagicMock()
    manager.run_backfill.return_value = [
        _make_pipeline_run(run_id="run-001", execution_date=date(2026, 1, 1), trigger_type="backfill"),
        _make_pipeline_run(run_id="run-002", execution_date=date(2026, 2, 1), trigger_type="backfill"),
    ]
    return manager


@pytest.fixture
def mock_run_repo():
    repo = MagicMock()
    run = _make_pipeline_run()
    repo.find_by_id.return_value = run
    repo.find_by_pipeline_paginated.return_value = ([run], 1)
    repo.find_by_pipeline.return_value = [run]
    return repo


@pytest.fixture
def mock_step_repo():
    repo = MagicMock()
    repo.find_by_pipeline_run.return_value = [_make_step_run()]
    return repo


@pytest.fixture
def mock_dispatcher():
    """dispatch_service mock. submit_manual_run 은 queued 를 가장한 _make_pipeline_run 을 반환."""
    dispatcher = MagicMock()
    dispatcher.submit_manual_run.return_value = _make_pipeline_run()
    dispatcher.submit_backfill.return_value = None
    return dispatcher


@pytest.fixture
def client(mock_runner, mock_backfill_manager, mock_run_repo, mock_step_repo, mock_dispatcher):
    settings = _make_settings()
    app = create_app(
        settings=settings,
        runner_map={"test_pipeline": mock_runner},
        backfill_map={"test_pipeline": mock_backfill_manager},
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        dispatch_service=mock_dispatcher,
    )
    return TestClient(app)


# ── create_app ────────────────────────────────────────────────────────────────

def test_create_app_returns_fastapi_instance():
    settings = _make_settings()
    app = create_app(settings)
    assert app.title == "Airflow Lite API"


def test_create_app_cors_middleware_configured():
    settings = _make_settings()
    app = create_app(settings)
    middleware_types = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middleware_types


def test_create_app_default_cors_allows_internal_wildcard_origin():
    settings = MagicMock()
    settings.pipelines = []
    settings.api = ApiConfig()
    app = create_app(settings)
    client = TestClient(app)

    resp = client.options(
        "/api/v1/pipelines",
        headers={
            "Origin": "http://10.0.0.15",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://10.0.0.15"


def test_root_redirects_to_monitor():
    settings = _make_settings()
    app = create_app(settings)
    client = TestClient(app)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/monitor"


def test_root_redirects_to_monitor_with_non_default_language():
    settings = _make_settings()
    app = create_app(settings)
    client = TestClient(app)

    response = client.get("/?lang=ko", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/monitor?lang=ko"


def test_monitor_home_page_renders_html_with_system_summary(client):
    response = client.get("/monitor")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "Home" in body
    assert "Ops Console" in body
    assert "Environment overview" in body
    assert "Latest pipeline runs" in body
    assert "test_pipeline" in body
    assert "/monitor/pipelines" in body
    assert "/monitor/exports" in body
    assert "/monitor/pipelines/test_pipeline/runs/run-001" in body
    assert "manual" in body
    assert "success" in body


def test_monitor_pipeline_list_page_renders_html_with_pipeline_summary(client):
    response = client.get("/monitor/pipelines")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "DAGs" in body
    assert "Dag List" in body
    assert "test_pipeline" in body
    assert '/monitor/pipelines/test_pipeline"' in body
    assert "/monitor/pipelines/test_pipeline/runs/run-001" in body
    assert "run-grid" in body
    assert "Recent Runs (latest→oldest)" in body
    assert "manual" in body
    assert "success" in body
    assert "Trigger" in body
    assert "Force rerun" in body
    assert "Force rerun runs again for the latest run date." in body
    assert "/monitor/pipelines/test_pipeline/trigger" in body


def test_monitor_pipeline_list_page_recent_runs_render_latest_to_oldest():
    settings = _make_settings()
    older_run = _make_pipeline_run(run_id="run-001", execution_date=date(2026, 1, 1), status="failed")
    newer_run = _make_pipeline_run(run_id="run-002", execution_date=date(2026, 1, 2), status="success")

    run_repo = MagicMock()
    run_repo.find_by_id.return_value = newer_run
    run_repo.find_by_pipeline_paginated.return_value = ([newer_run, older_run], 2)
    run_repo.find_by_pipeline.return_value = [newer_run, older_run]

    step_repo = MagicMock()
    step_repo.find_by_pipeline_run.return_value = []

    app = create_app(settings=settings, run_repo=run_repo, step_repo=step_repo)
    local_client = TestClient(app)

    response = local_client.get("/monitor/pipelines")

    assert response.status_code == 200
    body = response.text
    assert body.index('title="2026-01-02 · success"') < body.index('title="2026-01-01 · failed"')


def test_monitor_page_uses_webui_refresh_setting(mock_run_repo, mock_step_repo):
    settings = _make_settings()
    settings.webui = WebUIConfig(monitor_refresh_seconds=15)
    app = create_app(settings=settings, run_repo=mock_run_repo, step_repo=mock_step_repo)
    client = TestClient(app)

    response = client.get("/monitor")

    assert response.status_code == 200
    assert 'content="15"' in response.text


def test_monitor_page_supports_korean_language_query(client):
    response = client.get("/monitor?lang=ko")

    assert response.status_code == 200
    body = response.text
    assert '<html lang="ko">' in body
    assert "운영 콘솔" in body
    assert "최신 파이프라인 실행" in body
    assert "/monitor/analytics?lang=ko" in body


def test_monitor_page_language_precedence_query_over_default_and_header(mock_run_repo, mock_step_repo):
    settings = _make_settings()
    settings.webui = WebUIConfig(default_language="ko")
    app = create_app(settings=settings, run_repo=mock_run_repo, step_repo=mock_step_repo)
    client = TestClient(app)

    default_response = client.get("/monitor", headers={"Accept-Language": "en-US,en;q=0.8"})
    assert default_response.status_code == 200
    assert '<html lang="ko">' in default_response.text
    assert "최신 파이프라인 실행" in default_response.text

    override_response = client.get("/monitor?lang=en", headers={"Accept-Language": "ko-KR,ko;q=0.9"})
    assert override_response.status_code == 200
    assert '<html lang="en">' in override_response.text
    assert "Latest pipeline runs" in override_response.text


def test_monitor_pipeline_list_page_filters_by_latest_run_state(
    mock_runner,
    mock_backfill_manager,
    mock_step_repo,
):
    settings = _make_settings(pipeline_names=("good_pipeline", "bad_pipeline"))
    run_repo = MagicMock()
    good_run = _make_pipeline_run(pipeline_name="good_pipeline", run_id="run-good", status="success")
    bad_run = _make_pipeline_run(pipeline_name="bad_pipeline", run_id="run-bad", status="failed")

    def _find_by_pipeline(name, limit):
        if name == "good_pipeline":
            return [good_run]
        if name == "bad_pipeline":
            return [bad_run]
        return []

    run_repo.find_by_pipeline.side_effect = _find_by_pipeline
    run_repo.find_by_id.return_value = bad_run
    run_repo.find_by_pipeline_paginated.return_value = ([bad_run], 1)
    app = create_app(
        settings=settings,
        runner_map={"good_pipeline": mock_runner},
        backfill_map={"good_pipeline": mock_backfill_manager},
        run_repo=run_repo,
        step_repo=mock_step_repo,
    )
    client = TestClient(app)

    response = client.get("/monitor/pipelines?state=bad")

    assert response.status_code == 200
    assert "bad_pipeline" in response.text
    assert "good_pipeline" not in response.text


def test_monitor_pipeline_detail_page_renders_dag_details_tabs(client):
    response = client.get("/monitor/pipelines/test_pipeline")

    assert response.status_code == 200
    assert "DAG Details" in response.text
    assert "Overview" in response.text
    assert "Grid View" in response.text
    assert "Graph View" in response.text
    assert "Runs" in response.text
    assert "Tasks" in response.text
    assert "Details" in response.text
    assert "Grid columns are ordered latest run → oldest run" in response.text
    assert "Trigger now" in response.text
    assert "Re-run latest" in response.text
    assert "Backfill control" in response.text
    assert "/monitor/pipelines/test_pipeline/runs/run-001" in response.text


def test_monitor_pipeline_detail_grid_view_uses_step_row_index_for_tones():
    settings = _make_settings()
    older_run = _make_pipeline_run(run_id="run-001", execution_date=date(2026, 1, 1), status="success")
    newer_run = _make_pipeline_run(run_id="run-002", execution_date=date(2026, 1, 2), status="running")

    run_repo = MagicMock()
    run_repo.find_by_id.return_value = newer_run
    run_repo.find_by_pipeline_paginated.return_value = ([newer_run, older_run], 2)
    run_repo.find_by_pipeline.return_value = [newer_run, older_run]

    step_repo = MagicMock()
    step_repo.find_by_pipeline_run.side_effect = lambda run_id: (
        [
            StepRun(id=f"{run_id}-extract", pipeline_run_id=run_id, step_name="extract", status="success"),
            StepRun(id=f"{run_id}-load", pipeline_run_id=run_id, step_name="load", status="failed"),
        ]
        if run_id == "run-001"
        else [
            StepRun(id=f"{run_id}-extract", pipeline_run_id=run_id, step_name="extract", status="failed"),
            StepRun(id=f"{run_id}-load", pipeline_run_id=run_id, step_name="load", status="success"),
        ]
    )

    app = create_app(
        settings=settings,
        runner_map={"test_pipeline": MagicMock()},
        backfill_map={"test_pipeline": MagicMock()},
        run_repo=run_repo,
        step_repo=step_repo,
    )
    local_client = TestClient(app)

    response = local_client.get("/monitor/pipelines/test_pipeline")

    assert response.status_code == 200
    body = response.text
    assert body.index('class="grid-col-header" title="2026-01-02"') < body.index(
        'class="grid-col-header" title="2026-01-01"'
    )
    assert 'class="run-block ok" title="2026-01-01 · extract"' in body
    assert 'class="run-block bad" title="2026-01-02 · extract"' in body
    assert 'class="run-block bad" title="2026-01-01 · load"' in body
    assert 'class="run-block ok" title="2026-01-02 · load"' in body

    run_response = local_client.get("/monitor/pipelines/test_pipeline/runs/run-002")
    assert run_response.status_code == 200
    run_body = run_response.text
    assert run_body.index('class="grid-col-header" title="2026-01-02"') < run_body.index(
        'class="grid-col-header" title="2026-01-01"'
    )


def test_monitor_pipeline_detail_page_supports_korean_language_query(client):
    response = client.get("/monitor/pipelines/test_pipeline?lang=ko")

    assert response.status_code == 200
    body = response.text
    assert '<html lang="ko">' in body
    assert "DAG 상세" in body
    assert "그리드 뷰" in body
    assert "태스크" in body
    assert "그리드 열 순서: 최신 실행 → 오래된 실행" in body
    assert "즉시 실행" in body
    assert "백필 제어" in body


def test_monitor_pipeline_detail_page_returns_404_for_unknown_pipeline(client):
    response = client.get("/monitor/pipelines/unknown_pipeline")

    assert response.status_code == 404
    assert "unknown_pipeline" in response.text


def test_monitor_run_detail_page_renders_dag_run_tabs(client):
    response = client.get("/monitor/pipelines/test_pipeline/runs/run-001")

    assert response.status_code == 200
    body = response.text
    assert "Dag Run" in body
    assert "Task Instances" in body
    assert "Events" in body
    assert "Code" in body
    assert "Details" in body
    assert "Graph View" in body
    assert "Persistent grid view" in body
    assert "Grid columns are ordered latest run → oldest run" in body
    assert "pipeline:" in body
    assert "dag_run:" in body
    assert "test_pipeline" in body
    assert '/monitor/pipelines/test_pipeline"' in body
    assert "/monitor" in body
    assert "Re-run this date" in body


def test_monitor_run_detail_page_supports_korean_language_query(client):
    response = client.get("/monitor/pipelines/test_pipeline/runs/run-001?lang=ko")

    assert response.status_code == 200
    body = response.text
    assert '<html lang="ko">' in body
    assert "실행 이벤트 피드" in body
    assert "그리드 열 순서: 최신 실행 → 오래된 실행" in body
    assert "파이프라인 스냅샷" in body
    assert "실행 메타데이터" in body
    assert "현재 날짜 재실행" in body


def test_monitor_trigger_action_redirects_to_run_detail(client, mock_dispatcher):
    response = client.post("/monitor/pipelines/test_pipeline/trigger", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/monitor/pipelines/test_pipeline/runs/run-001?action=triggered"
    call_kwargs = mock_dispatcher.submit_manual_run.call_args.kwargs
    assert call_kwargs["execution_date"] == date.today()
    assert call_kwargs["trigger_type"] == "manual"
    assert call_kwargs["force_rerun"] is False


def test_monitor_force_rerun_action_redirects_with_language(client, mock_dispatcher):
    response = client.post(
        "/monitor/pipelines/test_pipeline/trigger?lang=ko",
        content="execution_date=2026-01-01&force=true",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/monitor/pipelines/test_pipeline/runs/run-001?action=force_rerun&lang=ko"
    call_kwargs = mock_dispatcher.submit_manual_run.call_args.kwargs
    assert call_kwargs["execution_date"] == date(2026, 1, 1)
    assert call_kwargs["force_rerun"] is True


def test_monitor_trigger_action_returns_409_when_pipeline_busy(client, mock_dispatcher):
    active_run = _make_pipeline_run(run_id="run-busy", status="running")
    mock_dispatcher.submit_manual_run.side_effect = PipelineBusyError(
        "test_pipeline",
        active_run,
    )

    response = client.post("/monitor/pipelines/test_pipeline/trigger", follow_redirects=False)

    assert response.status_code == 409
    assert "Pipeline &#39;test_pipeline&#39; is already active." in response.text
    assert "run-busy" in response.text


def test_monitor_backfill_action_redirects_to_pipeline_detail(client, mock_dispatcher):
    response = client.post(
        "/monitor/pipelines/test_pipeline/backfill",
        content="start_date=2026-01-01&end_date=2026-02-28&force=true",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    # 비동기 백필: dispatcher 는 요청만 큐잉하고 즉시 반환. count 는 더 이상 라우트에서 계산하지 않는다.
    assert response.status_code == 303
    assert response.headers["location"] == "/monitor/pipelines/test_pipeline?action=backfill"
    mock_dispatcher.submit_backfill.assert_called_once_with(
        pipeline_name="test_pipeline",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 28),
        force_rerun=True,
    )


def test_monitor_backfill_returns_409_when_pipeline_busy(client, mock_dispatcher):
    active_run = _make_pipeline_run(run_id="run-busy", status="running")
    mock_dispatcher.submit_backfill.side_effect = PipelineBusyError(
        "test_pipeline",
        active_run,
    )

    response = client.post(
        "/monitor/pipelines/test_pipeline/backfill",
        content="start_date=2026-01-01&end_date=2026-02-28&force=true",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "Pipeline &#39;test_pipeline&#39; is already active." in response.text
    assert "run-busy" in response.text


def test_monitor_analytics_page_renders_dashboard_view(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    query_service = DuckDBAnalyticsQueryService(database_path)
    export_service = FilesystemAnalyticsExportService(tmp_path / "exports", query_service)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=query_service,
        analytics_export_service=export_service,
    )
    client = TestClient(app)

    response = client.get("/monitor/analytics?dataset=mes_ops&source=OPS_TABLE")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "Operations Overview" in body
    assert "Filter Bar" in body
    assert "Dataset Overview" in body
    assert "Rows by Month" in body
    assert "Queue Export" in body
    assert "Source Table: OPS_TABLE" in body
    assert "/monitor/exports?dataset=mes_ops" in body


def test_monitor_analytics_page_renders_korean_labels(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    query_service = DuckDBAnalyticsQueryService(database_path)
    export_service = FilesystemAnalyticsExportService(tmp_path / "exports", query_service)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=query_service,
        analytics_export_service=export_service,
    )
    client = TestClient(app)

    response = client.get("/monitor/analytics?dataset=mes_ops&source=OPS_TABLE&lang=ko")

    assert response.status_code == 200
    body = response.text
    assert '<html lang="ko">' in body
    assert "분석 대시보드" in body
    assert "필터 바" in body
    assert "월별 적재 행 수" in body
    assert "/monitor/exports?dataset=mes_ops&amp;lang=ko" in body


def test_monitor_analytics_page_uses_webui_defaults(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    settings.webui = WebUIConfig(
        analytics_refresh_seconds=45,
        default_dataset="mes_ops",
        default_dashboard_id="operations_overview",
    )
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    query_service = DuckDBAnalyticsQueryService(database_path)
    export_service = FilesystemAnalyticsExportService(tmp_path / "exports", query_service)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=query_service,
        analytics_export_service=export_service,
    )
    client = TestClient(app)

    response = client.get("/monitor/analytics")

    assert response.status_code == 200
    assert 'content="45"' in response.text
    assert "Operations Overview" in response.text


def test_monitor_export_page_creates_and_lists_jobs(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    query_service = DuckDBAnalyticsQueryService(database_path)
    export_service = FilesystemAnalyticsExportService(tmp_path / "exports", query_service)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=query_service,
        analytics_export_service=export_service,
    )
    client = TestClient(app)

    create_response = client.post(
        "/monitor/analytics/exports",
        content="dataset=mes_ops&dashboard_id=operations_overview&action_key=csv_zip_export&format=csv.zip&source=OPS_TABLE",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    assert create_response.status_code == 303
    location = create_response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    job_id = query["job_id"][0]

    status_body = _wait_for_export_completion(client, job_id)
    assert status_body["status"] == "completed"

    page_response = client.get(location)

    assert page_response.status_code == 200
    body = page_response.text
    assert "Export Job Monitor" in body
    assert "Job Inventory" in body
    assert job_id in body
    assert "completed" in body
    assert f"/api/v1/analytics/exports/{job_id}/download" in body


def test_monitor_export_delete_redirect_preserves_dataset_and_language(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    query_service = DuckDBAnalyticsQueryService(database_path)
    export_service = FilesystemAnalyticsExportService(tmp_path / "exports", query_service)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=query_service,
        analytics_export_service=export_service,
    )
    client = TestClient(app)

    create_response = client.post(
        "/monitor/analytics/exports?lang=ko",
        content="dataset=mes_ops&dashboard_id=operations_overview&action_key=csv_zip_export&format=csv.zip&source=OPS_TABLE&lang=ko",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    location = create_response.headers["location"]
    job_id = parse_qs(urlparse(location).query)["job_id"][0]

    delete_response = client.post(
        "/monitor/exports/delete-job?lang=ko",
        content=f"job_id={job_id}&dataset=mes_ops&lang=ko",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/monitor/exports?dataset=mes_ops&lang=ko"


# ── GET /api/v1/pipelines ─────────────────────────────────────────────────────

def test_list_pipelines_returns_all(client):
    resp = client.get("/api/v1/pipelines")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "test_pipeline"
    assert data[0]["strategy"] == "full"
    assert data[0]["schedule"] == "0 2 * * *"


def test_list_pipelines_multiple(mock_runner, mock_backfill_manager, mock_run_repo, mock_step_repo):
    settings = _make_settings(pipeline_names=("pipeline_a", "pipeline_b", "pipeline_c"))
    app = create_app(settings=settings, run_repo=mock_run_repo, step_repo=mock_step_repo)
    c = TestClient(app)
    resp = c.get("/api/v1/pipelines")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ── POST /api/v1/pipelines/{name}/trigger ────────────────────────────────────

def test_trigger_pipeline_success(client, mock_dispatcher):
    resp = client.post(
        "/api/v1/pipelines/test_pipeline/trigger",
        json={"execution_date": "2026-01-01"},
    )
    # 이미 성공 처리된 run 을 가장한 mock 이므로 200. 신규 queued 는 202 (별도 테스트에서 검증).
    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_name"] == "test_pipeline"
    assert data["trigger_type"] == "manual"
    assert data["status"] == "success"
    assert len(data["steps"]) == 1
    mock_dispatcher.submit_manual_run.assert_called_once_with(
        pipeline_name="test_pipeline",
        execution_date=date(2026, 1, 1),
        trigger_type="manual",
        force_rerun=False,
    )


def test_trigger_pipeline_no_date_uses_today(client, mock_dispatcher):
    resp = client.post("/api/v1/pipelines/test_pipeline/trigger", json={})
    assert resp.status_code == 200
    call_kwargs = mock_dispatcher.submit_manual_run.call_args.kwargs
    assert call_kwargs["execution_date"] == date.today()
    assert call_kwargs["force_rerun"] is False


def test_trigger_pipeline_returns_202_when_queued(client, mock_dispatcher):
    queued = _make_pipeline_run()
    queued.status = "queued"
    queued.started_at = None
    mock_dispatcher.submit_manual_run.return_value = queued
    resp = client.post("/api/v1/pipelines/test_pipeline/trigger", json={})
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"


def test_trigger_returns_409_when_pipeline_busy(client, mock_dispatcher):
    active_run = _make_pipeline_run(run_id="run-busy", status="running")
    mock_dispatcher.submit_manual_run.side_effect = PipelineBusyError(
        "test_pipeline",
        active_run,
    )

    resp = client.post(
        "/api/v1/pipelines/test_pipeline/trigger",
        json={"execution_date": "2026-01-02", "force": True},
    )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["pipeline_name"] == "test_pipeline"
    assert detail["run_id"] == "run-busy"
    assert detail["status"] == "running"


def test_trigger_pipeline_not_found(client):
    resp = client.post(
        "/api/v1/pipelines/unknown_pipeline/trigger",
        json={},
    )
    assert resp.status_code == 404
    assert "unknown_pipeline" in resp.json()["detail"]


def test_trigger_pipeline_can_enable_force(mock_run_repo, mock_step_repo):
    settings = _make_settings()
    mock_runner = MagicMock()
    dispatcher = MagicMock()
    dispatcher.submit_manual_run.return_value = _make_pipeline_run()
    app = create_app(
        settings=settings,
        runner_map={"test_pipeline": mock_runner},
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        dispatch_service=dispatcher,
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/pipelines/test_pipeline/trigger",
        json={"execution_date": "2026-01-01", "force": True},
    )

    assert resp.status_code == 200
    assert dispatcher.submit_manual_run.call_args.kwargs["force_rerun"] is True


# ── POST /api/v1/pipelines/{name}/backfill ───────────────────────────────────

def test_backfill_success(client, mock_dispatcher):
    """비동기 백필: dispatcher 에 태우고 즉시 queued 응답을 돌려준다."""
    resp = client.post(
        "/api/v1/pipelines/test_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-02-28"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    mock_dispatcher.submit_backfill.assert_called_once_with(
        pipeline_name="test_pipeline",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 28),
        force_rerun=False,
    )


def test_backfill_not_found(client, mock_dispatcher):
    mock_dispatcher.has_backfill.return_value = False
    resp = client.post(
        "/api/v1/pipelines/no_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    assert resp.status_code == 404


def test_backfill_can_disable_force(client, mock_dispatcher):
    resp = client.post(
        "/api/v1/pipelines/test_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-01-31", "force": False},
    )

    assert resp.status_code == 202
    assert mock_dispatcher.submit_backfill.call_args.kwargs["force_rerun"] is False


def test_backfill_rejects_invalid_date_range(client, mock_dispatcher):
    resp = client.post(
        "/api/v1/pipelines/test_pipeline/backfill",
        json={"start_date": "2026-02-01", "end_date": "2026-01-31"},
    )

    assert resp.status_code == 400
    assert "end_date" in resp.json()["detail"]
    mock_dispatcher.submit_backfill.assert_not_called()


def test_monitor_backfill_rejects_invalid_date_range(client, mock_dispatcher):
    response = client.post(
        "/monitor/pipelines/test_pipeline/backfill",
        content="start_date=2026-02-01&end_date=2026-01-31",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "end_date" in response.text
    mock_dispatcher.submit_backfill.assert_not_called()


def test_backfill_returns_409_when_pipeline_busy(client, mock_dispatcher):
    active_run = _make_pipeline_run(run_id="run-busy", status="running")
    mock_dispatcher.submit_backfill.side_effect = PipelineBusyError(
        "test_pipeline",
        active_run,
    )

    resp = client.post(
        "/api/v1/pipelines/test_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["pipeline_name"] == "test_pipeline"
    assert detail["run_id"] == "run-busy"
    assert detail["status"] == "running"


# ── GET /api/v1/pipelines/{name}/runs ────────────────────────────────────────

def test_list_runs_pagination(client, mock_run_repo):
    resp = client.get("/api/v1/pipelines/test_pipeline/runs?page=1&page_size=20")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    mock_run_repo.find_by_pipeline_paginated.assert_called_once_with(
        "test_pipeline", page=1, page_size=20
    )


def test_list_runs_default_pagination(client, mock_run_repo):
    resp = client.get("/api/v1/pipelines/test_pipeline/runs")
    assert resp.status_code == 200
    mock_run_repo.find_by_pipeline_paginated.assert_called_once_with(
        "test_pipeline", page=1, page_size=50
    )


def test_list_runs_not_found(client):
    resp = client.get("/api/v1/pipelines/no_pipeline/runs")
    assert resp.status_code == 404


def test_list_runs_includes_steps(client):
    resp = client.get("/api/v1/pipelines/test_pipeline/runs")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert len(items[0]["steps"]) == 1
    assert items[0]["steps"][0]["step_name"] == "extract"
    assert items[0]["steps"][0]["records_processed"] == 1000


# ── GET /api/v1/pipelines/{name}/runs/{run_id} ───────────────────────────────

def test_get_run_detail_success(client, mock_run_repo):
    resp = client.get("/api/v1/pipelines/test_pipeline/runs/run-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "run-001"
    assert data["pipeline_name"] == "test_pipeline"
    assert len(data["steps"]) == 1


def test_get_run_detail_not_found_wrong_id(client, mock_run_repo):
    mock_run_repo.find_by_id.return_value = None
    resp = client.get("/api/v1/pipelines/test_pipeline/runs/nonexistent")
    assert resp.status_code == 404


def test_get_run_detail_not_found_wrong_pipeline(client, mock_run_repo):
    """run_id는 존재하지만 pipeline_name 불일치 → 404."""
    run = _make_pipeline_run(pipeline_name="other_pipeline")
    mock_run_repo.find_by_id.return_value = run
    resp = client.get("/api/v1/pipelines/test_pipeline/runs/run-001")
    assert resp.status_code == 404


# ── TestClient 실제 DB 통합 테스트 ─────────────────────────────────────────────

def test_integration_with_real_db(db, pipeline_repo, step_repo):
    """실제 SQLite DB를 사용하는 통합 테스트."""
    from airflow_lite.storage.models import PipelineRun, StepRun

    # DB에 실제 데이터 삽입
    run = PipelineRun(
        id="integ-run-001",
        pipeline_name="test_pipeline",
        execution_date=date(2026, 3, 1),
        status="success",
        started_at=datetime(2026, 3, 1, 2, 0),
        finished_at=datetime(2026, 3, 1, 3, 0),
        trigger_type="manual",
    )
    pipeline_repo.create(run)

    step = StepRun(
        id="integ-step-001",
        pipeline_run_id="integ-run-001",
        step_name="extract",
        status="success",
        started_at=datetime(2026, 3, 1, 2, 0),
        finished_at=datetime(2026, 3, 1, 2, 30),
        records_processed=500,
    )
    step_repo.create(step)

    settings = _make_settings()
    app = create_app(
        settings=settings,
        runner_map={},
        backfill_map={},
        run_repo=pipeline_repo,
        step_repo=step_repo,
    )
    c = TestClient(app)

    # 실행 이력 조회
    resp = c.get("/api/v1/pipelines/test_pipeline/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "integ-run-001"
    assert data["items"][0]["steps"][0]["records_processed"] == 500

    # 상세 조회
    resp = c.get("/api/v1/pipelines/test_pipeline/runs/integ-run-001")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_summary_contract_serializes_metric_cards():
    response = SummaryQueryResponse(
        dataset="mes_ops",
        generated_at=datetime(2026, 3, 31, 9, 0, 0),
        filters_applied={"plant": ["P1"]},
        metrics=[
            SummaryMetricCard(
                key="throughput",
                label="Throughput",
                value=1280,
                precision=SummaryPrecision.INTEGER,
                unit="ea",
            )
        ],
    )

    data = response.model_dump(mode="json")

    assert data["dataset"] == "mes_ops"
    assert data["metrics"][0]["key"] == "throughput"
    assert data["metrics"][0]["unit"] == "ea"


def test_chart_contract_serializes_series_points():
    response = ChartQueryResponse(
        dataset="mes_ops",
        chart_id="daily_throughput",
        title="Daily Throughput",
        granularity=ChartGranularity.DAY,
        filters_applied={"line": ["L1"]},
        series=[
            ChartSeries(
                key="actual",
                label="Actual",
                points=[
                    ChartPoint(bucket="2026-03-01", value=100),
                    ChartPoint(bucket="2026-03-02", value=110),
                ],
            )
        ],
    )

    data = response.model_dump(mode="json")

    assert data["chart_id"] == "daily_throughput"
    assert data["granularity"] == "day"
    assert data["series"][0]["points"][1]["value"] == 110

def test_analytics_summary_endpoint_returns_mart_metrics(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=DuckDBAnalyticsQueryService(database_path),
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/analytics/summary",
        json={"dataset": "mes_ops", "filters": {"source": ["OPS_TABLE"]}},
    )

    assert response.status_code == 200
    body = response.json()
    metric_map = {metric["key"]: metric["value"] for metric in body["metrics"]}
    assert metric_map["rows_loaded"] == 15
    assert metric_map["source_files"] == 2


def test_analytics_chart_and_filter_endpoints_return_mart_data(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=DuckDBAnalyticsQueryService(database_path),
    )
    client = TestClient(app)

    chart_response = client.post(
        "/api/v1/analytics/charts/rows_by_month/query",
        json={
            "dataset": "mes_ops",
            "chart_id": "rows_by_month",
            "granularity": "month",
            "limit": 12,
            "filters": {},
        },
    )
    filters_response = client.get("/api/v1/analytics/filters?dataset=mes_ops")

    assert chart_response.status_code == 200
    assert [point["value"] for point in chart_response.json()["series"][0]["points"]] == [10, 10]
    assert filters_response.status_code == 200
    filter_keys = [item["key"] for item in filters_response.json()["filters"]]
    assert filter_keys == ["source", "partition_month"]


def test_analytics_dashboard_endpoint_returns_dashboard_definition(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=DuckDBAnalyticsQueryService(database_path),
    )
    client = TestClient(app)

    response = client.get("/api/v1/analytics/dashboards/operations_overview?dataset=mes_ops")

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "dashboard.v1"
    assert body["dashboard_id"] == "operations_overview"
    assert body["dataset"] == "mes_ops"
    assert [card["metric_key"] for card in body["cards"]] == [
        "rows_loaded",
        "source_files",
        "source_tables",
        "covered_months",
        "avg_rows_per_file",
    ]
    assert body["cards"][0]["request_method"] == "POST"
    assert body["cards"][0]["filter_keys"] == ["source", "partition_month"]
    assert [chart["chart_id"] for chart in body["charts"]] == [
        "rows_by_month",
        "files_by_source",
    ]
    assert body["charts"][1]["request_method"] == "POST"
    assert body["charts"][1]["filter_keys"] == ["source", "partition_month"]
    assert body["drilldown_actions"][0]["scope"] == "chart"
    assert body["drilldown_actions"][0]["target_key"] == "files_by_source"
    assert body["drilldown_actions"][0]["endpoint"] == "/api/v1/analytics/details/source-files/query"
    assert body["drilldown_actions"][0]["status"] == "available"
    assert body["export_actions"][0]["status"] == "available"
    assert body["export_actions"][0]["endpoint"] == "/api/v1/analytics/exports"
    assert body["warnings"] == []


def test_analytics_endpoints_localize_labels_with_lang_query(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=DuckDBAnalyticsQueryService(database_path),
    )
    client = TestClient(app)

    filters_response = client.get("/api/v1/analytics/filters?dataset=mes_ops&lang=ko")
    dashboard_response = client.get("/api/v1/analytics/dashboards/operations_overview?dataset=mes_ops&lang=ko")
    summary_response = client.post(
        "/api/v1/analytics/summary?lang=ko",
        json={"dataset": "mes_ops", "filters": {"source": ["OPS_TABLE"]}},
    )
    chart_response = client.post(
        "/api/v1/analytics/charts/rows_by_month/query?lang=ko",
        json={
            "dataset": "mes_ops",
            "chart_id": "rows_by_month",
            "granularity": "month",
            "limit": 12,
            "filters": {},
        },
    )
    detail_response = client.post(
        "/api/v1/analytics/details/source-files/query?lang=ko",
        json={
            "dataset": "mes_ops",
            "detail_key": "source-files",
            "filters": {},
            "page": 1,
            "page_size": 2,
        },
    )

    assert filters_response.status_code == 200
    assert dashboard_response.status_code == 200
    assert summary_response.status_code == 200
    assert chart_response.status_code == 200
    assert detail_response.status_code == 200

    filter_map = {item["key"]: item["label"] for item in filters_response.json()["filters"]}
    assert filter_map["source"] == "원본 테이블"
    assert filter_map["partition_month"] == "파티션 월"

    dashboard_body = dashboard_response.json()
    assert dashboard_body["title"] == "MES 운영 개요"
    assert dashboard_body["cards"][0]["label"] == "적재 행 수"
    assert dashboard_body["charts"][0]["title"] == "월별 적재 행 수"

    summary_body = summary_response.json()
    summary_metric_map = {metric["key"]: metric for metric in summary_body["metrics"]}
    assert summary_metric_map["rows_loaded"]["label"] == "적재 행 수"
    assert summary_metric_map["rows_loaded"]["unit"] == "행"

    chart_body = chart_response.json()
    assert chart_body["title"] == "월별 적재 행 수"
    assert chart_body["series"][0]["label"] == "적재 행 수"

    detail_body = detail_response.json()
    assert detail_body["columns"][0]["label"] == "원본 테이블"


def test_analytics_detail_endpoint_returns_paginated_rows(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=DuckDBAnalyticsQueryService(database_path),
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/analytics/details/source-files/query",
        json={
            "dataset": "mes_ops",
            "detail_key": "source-files",
            "filters": {},
            "page": 1,
            "page_size": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["detail_key"] == "source-files"
    assert body["total"] == 3
    assert len(body["rows"]) == 2
    assert body["rows"][0]["source_name"] == "EQUIPMENT_STATUS"


def test_analytics_export_endpoints_create_poll_and_download_artifact(
    tmp_path,
    mock_run_repo,
    mock_step_repo,
    analytics_mart_builder,
):
    settings = _make_settings()
    database_path = tmp_path / "analytics.duckdb"
    analytics_mart_builder(database_path)
    query_service = DuckDBAnalyticsQueryService(database_path)
    export_service = FilesystemAnalyticsExportService(tmp_path / "exports", query_service)
    app = create_app(
        settings=settings,
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
        analytics_query_service=query_service,
        analytics_export_service=export_service,
    )
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/analytics/exports",
        json={
            "dataset": "mes_ops",
            "action_key": "csv_zip_export",
            "format": "csv.zip",
            "filters": {"source": ["OPS_TABLE"]},
        },
    )

    assert create_response.status_code == 200
    job_id = create_response.json()["job_id"]
    status_body = _wait_for_export_completion(client, job_id)
    assert status_body["status"] == "completed"
    assert status_body["file_name"].endswith(".zip")
    assert status_body["download_endpoint"] == f"/api/v1/analytics/exports/{job_id}/download"

    download_response = client.get(f"/api/v1/analytics/exports/{job_id}/download")
    assert download_response.status_code == 200
    assert "zip" in download_response.headers["content-type"]

