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
    ("path", "title_text"),
    [
        ("/monitor/security/users", "Security Users"),
        ("/monitor/security/roles", "Security Roles"),
        ("/monitor/security/permissions", "Security Permissions"),
    ],
)
def test_security_placeholder_pages_render(path: str, title_text: str):
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    body = response.text
    assert title_text in body
    assert "Placeholder" in body


def test_security_placeholder_pages_support_korean_language_query():
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get("/monitor/security/users?lang=ko")

    assert response.status_code == 200
    assert '<html lang="ko">' in response.text
    assert "사용자 인벤토리" in response.text
