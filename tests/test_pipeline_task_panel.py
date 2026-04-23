"""Tests for issue #97: Pipeline detail task-panel tabs and unsupported actions.

Acceptance criteria:
- Logs and XCom tabs are disabled (not functional stubs that mislead users).
- Mark Success and Clear buttons are removed from the panel.
- View Run Detail link replaces the non-functional View Full Logs href="#".
- JS that drives the tab switcher skips disabled buttons.
"""
import pathlib
import re

import pytest

TEMPLATE_PATH = "src/airflow_lite/api/templates/pipeline_detail.html"


def _read(root: pathlib.Path) -> str:
    return (root / TEMPLATE_PATH).read_text(encoding="utf-8")


def test_logs_tab_is_disabled(pytestconfig):
    html = _read(pathlib.Path(pytestconfig.rootdir))
    # The Logs tab button must have the disabled attribute
    assert re.search(r'data-panel-tab="logs"[^>]*disabled', html), (
        "Logs tab must be marked disabled when log viewer is not yet implemented."
    )


def test_xcom_tab_is_disabled(pytestconfig):
    html = _read(pathlib.Path(pytestconfig.rootdir))
    assert re.search(r'data-panel-tab="xcom"[^>]*disabled', html), (
        "XCom tab must be marked disabled when XCom viewer is not yet implemented."
    )


def test_mark_success_button_removed(pytestconfig):
    html = _read(pathlib.Path(pytestconfig.rootdir))
    assert "Mark Success" not in html, (
        "Mark Success button must be removed from the task panel "
        "because the action is not implemented."
    )


def test_clear_button_removed(pytestconfig):
    html = _read(pathlib.Path(pytestconfig.rootdir))
    # Ensure no 'Clear' standalone action button remains inside the task panel actions block
    # We check the actions div specifically
    panel_section = html[html.find("dag-task-panel-actions"):html.find("dag-task-panel-actions") + 400]
    assert "btn-danger" not in panel_section, (
        "Clear (danger) button must be removed from the task panel actions."
    )


def test_run_detail_link_replaces_hash_href(pytestconfig):
    html = _read(pathlib.Path(pytestconfig.rootdir))
    # The old href="#" must be gone from the panel actions
    assert 'id="task-panel-logs-link"' not in html, (
        "Old task-panel-logs-link (href='#') must be replaced with a run-detail link."
    )
    assert 'id="task-panel-run-link"' in html, (
        "task-panel-run-link must be present so JS can set the real URL."
    )


def test_panel_tab_js_skips_disabled(pytestconfig):
    html = _read(pathlib.Path(pytestconfig.rootdir))
    # The JS must guard disabled tabs
    assert "btn.disabled" in html, (
        "Tab-switcher JS must skip buttons that are disabled."
    )
