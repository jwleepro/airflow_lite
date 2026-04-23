"""Tests for issue #96: Browse DAG Runs page must not crash when run_id is None.

The template sliced run.run_id[:12] unconditionally; if run_id is None
this raises a TypeError.  The fix wraps the value with `or '-'` before slicing.
"""
import re
import pathlib

import pytest


TEMPLATE_PATH = "src/airflow_lite/api/templates/browse/browse_dag_runs.html"


def _read_template(root: pathlib.Path) -> str:
    return (root / TEMPLATE_PATH).read_text(encoding="utf-8")


def test_run_id_slice_is_null_safe(pytestconfig):
    """The template must not slice run.run_id directly; it must guard against None."""
    html = _read_template(pathlib.Path(pytestconfig.rootdir))

    # The old unsafe pattern: run.run_id[:12] without a guard
    unsafe = re.compile(r"run\.run_id\[:12\]")
    assert not unsafe.search(html), (
        "Template still contains the unsafe 'run.run_id[:12]' slice. "
        "Guard against None before slicing."
    )


def test_run_id_fallback_present(pytestconfig):
    """The template must provide a safe fallback when run_id is absent."""
    html = _read_template(pathlib.Path(pytestconfig.rootdir))

    # After the fix the template assigns: {% set rid = run.run_id or '-' %}
    assert "run.run_id or" in html, (
        "Template does not contain a null-safe fallback for run_id."
    )


def test_view_link_guarded_by_run_id(pytestconfig):
    """The View link must only be emitted when run_id is present."""
    html = _read_template(pathlib.Path(pytestconfig.rootdir))

    # The fix wraps the link in {% if run.run_id %}
    assert "{% if run.run_id %}" in html, (
        "View link is not guarded by '{% if run.run_id %}'; "
        "URL construction will fail when run_id is None."
    )
