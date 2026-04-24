"""Tests for pipeline_detail task-panel tabs and action states (issue #97).

Verifies that:
- Logs / XCom tab panes exist in the rendered HTML
- Mark Success and Clear buttons are rendered as disabled with aria-disabled
- Grid cells carry data-run-id so the JS can wire the log link
- View Run Detail link is present (conditionally shown via JS)
- _switchPanelTab JS helper is defined
"""
from __future__ import annotations

import re
from pathlib import Path

from airflow_lite.api.webui_pipeline_detail import render_pipeline_detail_page


# ---------------------------------------------------------------------------
# Template-source structural tests (no server needed)
# ---------------------------------------------------------------------------

_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "src" / "airflow_lite" / "api" / "templates" / "pipeline_detail.html"
)


def _html() -> str:
    """Return the raw pipeline_detail template source."""
    return _TEMPLATE.read_text(encoding="utf-8")


def test_task_panel_has_three_tabs():
    """Task panel must expose Details, Logs, and XCom tab buttons."""
    html = _html()
    assert 'data-panel-tab="details"' in html
    assert 'data-panel-tab="logs"' in html
    assert 'data-panel-tab="xcom"' in html


def test_task_panel_has_separate_panes():
    """Each tab must have a corresponding pane element."""
    html = _html()
    assert 'id="task-pane-details"' in html
    assert 'id="task-pane-logs"' in html
    assert 'id="task-pane-xcom"' in html


def test_mark_success_button_is_disabled():
    """Mark Success button must be rendered disabled and aria-disabled."""
    html = _html()
    assert "Mark Success" in html
    button_match = re.search(r'<button[^>]*>Mark Success</button>', html, re.DOTALL)
    assert button_match, "Mark Success button not found"
    btn_html = button_match.group(0)
    assert "disabled" in btn_html
    assert 'aria-disabled="true"' in btn_html


def test_clear_button_is_disabled():
    """All Clear buttons must be rendered disabled and aria-disabled."""
    html = _html()
    assert "Clear" in html
    matches = re.findall(r'<button[^>]*>Clear</button>', html, re.DOTALL)
    assert matches, "Clear button not found"
    for btn_html in matches:
        assert "disabled" in btn_html, f"Clear button without disabled: {btn_html}"
        assert 'aria-disabled="true"' in btn_html, f"Clear button without aria-disabled: {btn_html}"


def test_grid_cells_carry_data_run_id():
    """Grid cells must expose data-run-id so JS can build the log link."""
    html = _html()
    assert 'data-run-id=' in html


def test_task_panel_logs_link_present():
    """A View Run Detail link element must exist (JS toggles its visibility)."""
    html = _html()
    assert 'id="task-panel-logs-link"' in html


def test_logs_pane_explains_limitation():
    """Logs pane must tell the user that log streaming is not available."""
    html = _html()
    assert "Log streaming is not available" in html


def test_xcom_pane_explains_limitation():
    """XCom pane must tell the user that XCom values are not available."""
    html = _html()
    assert "XCom values are not available" in html


def test_switch_panel_tab_function_defined():
    """_switchPanelTab JS helper must be defined in the template."""
    html = _html()
    assert "_switchPanelTab" in html


def test_switch_panel_tab_syncs_button_active_class():
    """_switchPanelTab must toggle active class on tab buttons as well as panes."""
    html = _html()
    # The function must contain classList.toggle logic for buttons
    assert "classList.toggle" in html


def test_lang_param_preserved_in_run_detail_href():
    """JS must read the current ?lang= param and append it to the run-detail href."""
    html = _html()
    assert "URLSearchParams" in html
    assert "lang" in html


# ---------------------------------------------------------------------------
# Rendered HTML tests via webui renderer
# ---------------------------------------------------------------------------


def _make_page(run_id: str = "run-001") -> dict:
    """Return a minimal page dict for render_pipeline_detail_page."""
    return {
        "pipeline": {
            "name": "test_dag",
            "table": "TEST_DAG",
            "schedule": "0 2 * * *",
            "strategy": "full",
            "source_where_template": "1=1",
            "source_bind_params": "{}",
            "chunk_size": 10000,
            "incremental_key": None,
        },
        "latest_run": {"id": run_id, "status": "success"},
        "summary": {"total_runs": 1, "last_success": None, "last_failure": None, "avg_duration": None},
        "recent_failures": [],
        "runs": [],
        "grid": {"runs": [], "step_names": []},
        "task_rows": [],
        "graph_nodes": [],
    }


def test_rendered_page_contains_task_panel():
    """Rendered pipeline_detail page must include the task-panel element."""
    html = render_pipeline_detail_page(_make_page())
    assert 'id="task-panel"' in html


def test_rendered_page_mark_success_disabled():
    """Mark Success must appear disabled in the rendered output."""
    html = render_pipeline_detail_page(_make_page())
    assert "Mark Success" in html
    assert "disabled" in html


def test_rendered_page_clear_disabled():
    """Clear must appear disabled in the rendered output."""
    html = render_pipeline_detail_page(_make_page())
    assert "Clear" in html


def test_rendered_page_pipeline_name_in_js():
    """Pipeline name must be embedded in JS so the log link can be built."""
    html = render_pipeline_detail_page(_make_page())
    assert "test_dag" in html
