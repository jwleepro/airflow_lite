"""Tests for Browse page renderers.

Verifies that Browse pages render with real page context (counts, table,
filter form) rather than relying on static placeholder text.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from airflow_lite.api.app import create_app
from airflow_lite.api.webui_browse import (
    BrowseAuditLogsContext,
    BrowseBackfillsContext,
    BrowseDagRunsContext,
    BrowseJobsContext,
    BrowseTaskInstancesContext,
    render_browse_page,
)
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
        ("/monitor/browse/backfills", "Browse Backfills"),
        ("/monitor/browse/jobs", "Browse Jobs"),
        ("/monitor/browse/audit-logs", "Browse Audit Logs"),
        ("/monitor/browse/task-instances", "Browse Task Instances"),
        ("/monitor/browse/dag-runs", "Browse Dag Runs"),
    ],
)
def test_browse_pages_render_with_real_context(path: str, title_text: str):
    """Browse pages return 200 and include the expected title text."""
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    body = response.text
    assert title_text in body
    # Pages must NOT fall back to static placeholder text any more.
    assert "webui.browse.placeholder" not in body


def test_browse_pages_support_korean_language_query():
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get("/monitor/browse/backfills?lang=ko")

    assert response.status_code == 200
    assert '<html lang="ko">' in response.text
    assert "백필 인벤토리" in response.text


# ---------------------------------------------------------------------------
# Context dataclass defaults
# ---------------------------------------------------------------------------


def test_browse_backfills_context_defaults():
    ctx = BrowseBackfillsContext()
    assert ctx.backfills == []
    assert ctx.total_count == 0
    assert ctx.running_count == 0
    assert ctx.pending_count == 0


def test_browse_jobs_context_defaults():
    ctx = BrowseJobsContext()
    assert ctx.jobs == []
    assert ctx.total_count == 0
    assert ctx.active_count == 0


def test_browse_audit_logs_context_defaults():
    ctx = BrowseAuditLogsContext()
    assert ctx.audit_logs == []
    assert ctx.users == []


def test_browse_task_instances_context_defaults():
    ctx = BrowseTaskInstancesContext()
    assert ctx.task_instances == []
    assert ctx.dag_ids == []


def test_browse_dag_runs_context_defaults():
    ctx = BrowseDagRunsContext()
    assert ctx.dag_runs == []
    assert ctx.dag_ids == []


# ---------------------------------------------------------------------------
# render_browse_page passes extra context to templates
# ---------------------------------------------------------------------------


def test_render_browse_page_passes_context_to_template():
    """render_browse_page forwards extra kwargs to the template."""
    html = render_browse_page(
        "browse/browse_backfills.html",
        title_key="webui.browse.backfills.title",
        subtitle_key="webui.browse.backfills.subtitle",
        active_path="/monitor/browse/backfills",
        total_count=5,
        running_count=2,
        pending_count=3,
        backfills=[],
    )
    assert "5 total" in html
    assert "2 running" in html
