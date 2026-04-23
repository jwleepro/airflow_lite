"""Tests for Security pages.

After issue #102 the placeholder renderer was replaced with per-page
renderers that pass real context variables (empty lists/counts by default).
Pages must render without the Placeholder text and expose table structure.
"""
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
        ("/monitor/security/users", "Users"),
        ("/monitor/security/roles", "Roles"),
        ("/monitor/security/permissions", "Permissions"),
    ],
)
def test_security_pages_render_with_real_context(path: str, expected_heading: str):
    """Security pages must render with real page context, not a placeholder stub."""
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    body = response.text
    assert expected_heading in body
    # Pages must no longer depend on the Placeholder stub text
    assert "Placeholder" not in body


@pytest.mark.parametrize(
    "path",
    [
        "/monitor/security/users",
        "/monitor/security/roles",
        "/monitor/security/permissions",
    ],
)
def test_security_pages_expose_table_structure(path: str):
    """Security pages must expose an air-table (real table structure)."""
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    assert "air-table" in response.text


def test_security_pages_support_korean_language_query():
    """Security pages must honour the lang= query parameter."""
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get("/monitor/security/users?lang=ko")

    assert response.status_code == 200
    assert '<html lang="ko">' in response.text
    # The subtitle is rendered via i18n and contains Korean text
    assert "사용자" in response.text
