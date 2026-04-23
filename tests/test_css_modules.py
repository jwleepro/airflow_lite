"""Tests for issue #100: Split monolithic app.css into maintainable modules.

Acceptance criteria:
- Each module file must exist in the css directory.
- base.html must load every module via a separate <link> tag.
- app.css must import every module (backward-compat shim).
- No module file may be empty.
"""
import pathlib
import pytest

CSS_DIR = pathlib.Path("src/airflow_lite/api/static/css")
BASE_TEMPLATE = pathlib.Path("src/airflow_lite/api/templates/base.html")

EXPECTED_MODULES = [
    "tokens.css",
    "layout.css",
    "components.css",
    "pages.css",
    "utilities.css",
    "pipeline-detail.css",
    "task-logs.css",
    "search.css",
]


@pytest.mark.parametrize("module", EXPECTED_MODULES)
def test_module_file_exists(module: str, pytestconfig):
    path = pathlib.Path(pytestconfig.rootdir) / CSS_DIR / module
    assert path.exists(), f"CSS module {module} does not exist at {path}"


@pytest.mark.parametrize("module", EXPECTED_MODULES)
def test_module_file_not_empty(module: str, pytestconfig):
    path = pathlib.Path(pytestconfig.rootdir) / CSS_DIR / module
    assert path.stat().st_size > 0, f"CSS module {module} is empty"


@pytest.mark.parametrize("module", EXPECTED_MODULES)
def test_base_html_loads_module(module: str, pytestconfig):
    html = (pathlib.Path(pytestconfig.rootdir) / BASE_TEMPLATE).read_text(encoding="utf-8")
    assert module in html, (
        f"base.html does not load {module} via a <link> tag."
    )


@pytest.mark.parametrize("module", EXPECTED_MODULES)
def test_app_css_imports_module(module: str, pytestconfig):
    css = (pathlib.Path(pytestconfig.rootdir) / CSS_DIR / "app.css").read_text(encoding="utf-8")
    assert module in css, (
        f"app.css does not @import {module}. The legacy shim is incomplete."
    )
