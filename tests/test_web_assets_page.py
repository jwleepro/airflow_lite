from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from airflow_lite.api.app import create_app
from airflow_lite.config.settings import ApiConfig, PipelineConfig, WebUIConfig


def _make_settings() -> MagicMock:
    settings = MagicMock()
    settings.pipelines = [
        PipelineConfig(
            name="test_pipeline",
            table="TEST_PIPELINE",
            source_where_template="DATE_COL >= :data_interval_start AND DATE_COL < :data_interval_end",
            strategy="full",
            schedule="0 2 * * *",
        )
    ]
    settings.api = ApiConfig()
    settings.webui = WebUIConfig()
    return settings


def test_assets_page_renders_placeholder_inventory_table():
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get("/monitor/assets")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "Assets" in body
    assert "Asset Inventory" in body
    assert "No assets configured" in body
    assert "Placeholder" in body


def test_assets_page_supports_korean_language_query():
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get("/monitor/assets?lang=ko")

    assert response.status_code == 200
    body = response.text
    assert '<html lang="ko">' in body
    assert "자산 인벤토리" in body
    assert "구성된 자산 없음" in body
