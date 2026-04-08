"""T-032: /health 헬스체크 엔드포인트 테스트."""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from airflow_lite.api.app import create_app
from airflow_lite.config.settings import ApiConfig


def _make_settings():
    settings = MagicMock()
    settings.pipelines = []
    settings.api = ApiConfig(allowed_origins=["http://10.0.0.1"])
    settings.storage.parquet_base_path = "."
    return settings


def test_health_endpoint_returns_healthy():
    settings = _make_settings()
    app = create_app(settings)
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"healthy", "degraded"}
    assert len(body["checks"]) == 3
    names = {c["name"] for c in body["checks"]}
    assert names == {"scheduler", "mart_db", "disk"}


def test_health_disk_check_reports_free_space():
    settings = _make_settings()
    app = create_app(settings)
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    body = resp.json()
    disk_check = next(c for c in body["checks"] if c["name"] == "disk")
    assert "GB free" in disk_check["detail"]
