"""Tests for issue #95: Admin add-form toggle buttons must open hidden editors.

The forms use the HTML `hidden` attribute. Toggling a CSS class does not
remove that attribute, so the fix replaces classList.toggle('active') with
an inline handler that flips the `hidden` property directly.
"""
import re

import pytest


TEMPLATE_PATH = (
    "src/airflow_lite/api/templates/admin.html"
)


def _read_template(base: str) -> str:
    import pathlib
    return pathlib.Path(base).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "form_id",
    ["conn-add-form", "var-add-form", "pool-add-form"],
)
def test_toggle_buttons_use_hidden_property(form_id: str, pytestconfig):
    """Each add-form toggle button must flip the `hidden` property, not a class."""
    root = pytestconfig.rootdir
    html = _read_template(f"{root}/{TEMPLATE_PATH}")

    # The button that controls this form must reference `el.hidden` near getElementById
    pattern = re.compile(
        rf"el\.hidden.*?getElementById\(['\"]{ re.escape(form_id) }['\"]"
        rf"|getElementById\(['\"]{ re.escape(form_id) }['\"].*?el\.hidden",
        re.DOTALL,
    )
    assert pattern.search(html), (
        f"Button for #{form_id} does not toggle the `hidden` property. "
        "classList.toggle('active') alone cannot override the HTML hidden attribute."
    )


@pytest.mark.parametrize(
    "form_id",
    ["conn-add-form", "var-add-form", "pool-add-form"],
)
def test_add_forms_start_hidden(form_id: str, pytestconfig):
    """Each add-form must carry the HTML `hidden` attribute on initial load."""
    root = pytestconfig.rootdir
    html = _read_template(f"{root}/{TEMPLATE_PATH}")

    pattern = re.compile(
        rf'id=["\']{ re.escape(form_id) }["\'][^>]*hidden',
        re.DOTALL,
    )
    assert pattern.search(html), (
        f"#{form_id} is missing the `hidden` attribute on initial render."
    )
