"""Tests for Browse pages.

After issue #101 the placeholder renderer was replaced with per-page
renderers that pass real context variables (empty lists/counts by default).
Pages must render without the Placeholder text and expose filter/table
structure to the browser.
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
        ("/monitor/browse/backfills", "Backfills"),
        ("/monitor/browse/jobs", "Jobs"),
        ("/monitor/browse/audit-logs", "Audit Logs"),
        ("/monitor/browse/task-instances", "Task Instances"),
        ("/monitor/browse/dag-runs", "DAG Runs"),
    ],
)
def test_browse_pages_render_with_real_context(path: str, expected_heading: str):
    """Browse pages must render with real page context, not a placeholder stub."""
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
        "/monitor/browse/backfills",
        "/monitor/browse/jobs",
        "/monitor/browse/audit-logs",
        "/monitor/browse/task-instances",
        "/monitor/browse/dag-runs",
    ],
)
def test_browse_pages_expose_table_structure(path: str):
    """Browse pages must expose an air-table (real table structure)."""
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    assert "air-table" in response.text


def test_browse_pages_support_korean_language_query():
    """Browse pages must honour the lang= query parameter."""
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get("/monitor/browse/backfills?lang=ko")

    assert response.status_code == 200
    assert '<html lang="ko">' in response.text
    # The subtitle is rendered via i18n and contains Korean text
    assert "백필" in response.text
