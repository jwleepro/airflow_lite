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


# ---------------------------------------------------------------------------
# truncate_id helper — unit tests
# ---------------------------------------------------------------------------

from airflow_lite.api.template_env import truncate_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "-"),
        ("", "-"),
        ("short", "short"),
        ("exactly12char", "exactly12cha…"),  # 13 chars → truncated
        ("abcdefghijkl", "abcdefghijkl"),    # exactly 12 → no ellipsis
    ],
)
def test_truncate_id_basic(value, expected):
    assert truncate_id(value) == expected


def test_truncate_id_custom_fallback():
    assert truncate_id(None, fallback="N/A") == "N/A"


def test_truncate_id_custom_length():
    assert truncate_id("hello world", length=5) == "hello…"


# ---------------------------------------------------------------------------
# DAG Runs page null run_id regression
# ---------------------------------------------------------------------------

from airflow_lite.api.webui_browse import render_browse_dag_runs_page, render_browse_task_instances_page
from airflow_lite.api.paths import MONITOR_DAG_RUNS_PATH, MONITOR_BROWSE_TASK_INSTANCES_PATH


def _make_run(run_id):
    run = MagicMock()
    run.dag_id = "test_dag"
    run.run_id = run_id
    run.status = "success"
    run.start_time = "2024-01-01 00:00:00"
    run.duration = "10s"
    run.trigger_type = "manual"
    return run


def test_dag_runs_page_renders_with_null_run_id():
    """Page must not raise when run_id is None."""
    html = render_browse_dag_runs_page(
        active_path=MONITOR_DAG_RUNS_PATH,
        dag_runs=[_make_run(None)],
    )
    assert "-" in html
    # View button must be disabled (aria-disabled) when run_id is missing
    assert "aria-disabled" in html


def test_dag_runs_page_renders_with_empty_run_id():
    """Page must not raise when run_id is empty string."""
    html = render_browse_dag_runs_page(
        active_path=MONITOR_DAG_RUNS_PATH,
        dag_runs=[_make_run("")],
    )
    assert "-" in html


def test_dag_runs_page_truncates_long_run_id():
    """Long run_id must be truncated with ellipsis."""
    html = render_browse_dag_runs_page(
        active_path=MONITOR_DAG_RUNS_PATH,
        dag_runs=[_make_run("scheduled__2024-01-01T00:00:00+00:00")],
    )
    assert "scheduled__2" in html
    assert "…" in html


def _make_task(run_id):
    task = MagicMock()
    task.dag_id = "test_dag"
    task.task_id = "my_task"
    task.run_id = run_id
    task.status = "success"
    task.try_number = 1
    task.max_tries = 3
    task.start_date = "2024-01-01 00:00:00"
    task.duration = "5s"
    return task


def test_task_instances_page_renders_with_null_run_id():
    """Task instances page must not raise when run_id is None."""
    html = render_browse_task_instances_page(
        active_path=MONITOR_BROWSE_TASK_INSTANCES_PATH,
        task_instances=[_make_task(None)],
    )
    assert "-" in html
    assert "aria-disabled" in html


def test_task_instances_page_truncates_long_run_id():
    """Long run_id must be truncated in task instances table."""
    html = render_browse_task_instances_page(
        active_path=MONITOR_BROWSE_TASK_INSTANCES_PATH,
        task_instances=[_make_task("scheduled__2024-01-01T00:00:00+00:00")],
    )
    assert "scheduled__2" in html
    assert "…" in html
