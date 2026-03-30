"""Task-007: FastAPI REST API TestClient 기반 통합 테스트."""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from airflow_lite.api.app import create_app
from airflow_lite.config.settings import ApiConfig, PipelineConfig, Settings
from airflow_lite.storage.models import PipelineRun, StepRun


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _make_settings(pipeline_names=("test_pipeline",)):
    """테스트용 Settings 객체 생성."""
    pipelines = [
        PipelineConfig(
            name=name,
            table=name.upper(),
            partition_column="DATE_COL",
            strategy="full",
            schedule="0 2 * * *",
        )
        for name in pipeline_names
    ]
    settings = MagicMock()
    settings.pipelines = pipelines
    settings.api = ApiConfig(allowed_origins=["http://10.0.0.1"])
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
    return repo


@pytest.fixture
def mock_step_repo():
    repo = MagicMock()
    repo.find_by_pipeline_run.return_value = [_make_step_run()]
    return repo


@pytest.fixture
def client(mock_runner, mock_backfill_manager, mock_run_repo, mock_step_repo):
    settings = _make_settings()
    app = create_app(
        settings=settings,
        runner_map={"test_pipeline": mock_runner},
        backfill_map={"test_pipeline": mock_backfill_manager},
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
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

def test_trigger_pipeline_success(client, mock_runner):
    resp = client.post(
        "/api/v1/pipelines/test_pipeline/trigger",
        json={"execution_date": "2026-01-01"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_name"] == "test_pipeline"
    assert data["trigger_type"] == "manual"
    assert data["status"] == "success"
    assert len(data["steps"]) == 1
    mock_runner.run.assert_called_once_with(
        execution_date=date(2026, 1, 1), trigger_type="manual", force_rerun=False
    )


def test_trigger_pipeline_no_date_uses_today(client, mock_runner):
    resp = client.post("/api/v1/pipelines/test_pipeline/trigger", json={})
    assert resp.status_code == 200
    call_kwargs = mock_runner.run.call_args.kwargs
    assert call_kwargs["execution_date"] == date.today()
    assert call_kwargs["force_rerun"] is False


def test_trigger_pipeline_not_found(client):
    resp = client.post(
        "/api/v1/pipelines/unknown_pipeline/trigger",
        json={},
    )
    assert resp.status_code == 404
    assert "unknown_pipeline" in resp.json()["detail"]


def test_trigger_pipeline_accepts_runner_factory(mock_runner, mock_run_repo, mock_step_repo):
    settings = _make_settings()
    app = create_app(
        settings=settings,
        runner_map={"test_pipeline": lambda: mock_runner},
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/pipelines/test_pipeline/trigger",
        json={"execution_date": "2026-01-01"},
    )

    assert resp.status_code == 200
    mock_runner.run.assert_called_once()


def test_trigger_pipeline_can_enable_force(mock_run_repo, mock_step_repo):
    settings = _make_settings()
    mock_runner = MagicMock()
    mock_runner.run.return_value = _make_pipeline_run()
    app = create_app(
        settings=settings,
        runner_map={"test_pipeline": mock_runner},
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/pipelines/test_pipeline/trigger",
        json={"execution_date": "2026-01-01", "force": True},
    )

    assert resp.status_code == 200
    assert mock_runner.run.call_args.kwargs["force_rerun"] is True


# ── POST /api/v1/pipelines/{name}/backfill ───────────────────────────────────

def test_backfill_success(client, mock_backfill_manager):
    resp = client.post(
        "/api/v1/pipelines/test_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-02-28"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["trigger_type"] == "backfill"
    mock_backfill_manager.run_backfill.assert_called_once_with(
        pipeline_name="test_pipeline",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 28),
        force_rerun=True,
    )


def test_backfill_not_found(client):
    resp = client.post(
        "/api/v1/pipelines/no_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    assert resp.status_code == 404


def test_backfill_accepts_manager_factory(mock_backfill_manager, mock_run_repo, mock_step_repo):
    settings = _make_settings()
    app = create_app(
        settings=settings,
        backfill_map={"test_pipeline": lambda: mock_backfill_manager},
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/pipelines/test_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-02-28"},
    )

    assert resp.status_code == 200
    mock_backfill_manager.run_backfill.assert_called_once()


def test_backfill_can_disable_force(mock_run_repo, mock_step_repo):
    settings = _make_settings()
    mock_manager = MagicMock()
    mock_manager.run_backfill.return_value = [
        _make_pipeline_run(run_id="run-001", execution_date=date(2026, 1, 1), trigger_type="backfill")
    ]
    app = create_app(
        settings=settings,
        backfill_map={"test_pipeline": mock_manager},
        run_repo=mock_run_repo,
        step_repo=mock_step_repo,
    )
    client = TestClient(app)

    resp = client.post(
        "/api/v1/pipelines/test_pipeline/backfill",
        json={"start_date": "2026-01-01", "end_date": "2026-01-31", "force": False},
    )

    assert resp.status_code == 200
    assert mock_manager.run_backfill.call_args.kwargs["force_rerun"] is False


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
