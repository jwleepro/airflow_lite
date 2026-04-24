from unittest.mock import MagicMock

import pytest
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


@pytest.mark.parametrize(
    ("path", "expected_heading"),
    [
        ("/monitor/admin/connections", "Connections"),
        ("/monitor/admin/variables", "Variables"),
        ("/monitor/admin/pools", "Pools"),
        ("/monitor/admin/providers", "Providers"),
        ("/monitor/admin/plugins", "Plugins"),
        ("/monitor/admin/config", "Configuration"),
        ("/monitor/admin/xcoms", "XComs"),
    ],
)
def test_admin_subpages_render(path: str, expected_heading: str):
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    assert expected_heading in response.text
    assert "Apache Airflow" in response.text
