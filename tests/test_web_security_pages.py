"""Tests for Security page renderers.

Verifies that Security pages render with real page context (counts, table)
rather than relying on static placeholder text.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from airflow_lite.api.app import create_app
from airflow_lite.api.webui_security import (
    SecurityPermissionsContext,
    SecurityRolesContext,
    SecurityUsersContext,
    render_security_page,
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
        ("/monitor/security/users", "Security Users"),
        ("/monitor/security/roles", "Security Roles"),
        ("/monitor/security/permissions", "Security Permissions"),
    ],
)
def test_security_pages_render_with_real_context(path: str, title_text: str):
    """Security pages return 200 and include the expected title text."""
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    body = response.text
    assert title_text in body
    # Pages must NOT fall back to static placeholder text any more.
    assert "webui.security.placeholder" not in body


def test_security_pages_support_korean_language_query():
    app = create_app(_make_settings())
    client = TestClient(app)

    response = client.get("/monitor/security/users?lang=ko")

    assert response.status_code == 200
    assert '<html lang="ko">' in response.text
    # Korean title text is rendered
    assert "Security Users" in response.text


# ---------------------------------------------------------------------------
# Context dataclass defaults
# ---------------------------------------------------------------------------


def test_security_users_context_defaults():
    ctx = SecurityUsersContext()
    assert ctx.users == []
    assert ctx.total_count == 0
    assert ctx.active_count == 0
    assert ctx.search_query == ""


def test_security_roles_context_defaults():
    ctx = SecurityRolesContext()
    assert ctx.roles == []
    assert ctx.total_count == 0


def test_security_permissions_context_defaults():
    ctx = SecurityPermissionsContext()
    assert ctx.permissions == []
    assert ctx.total_count == 0


# ---------------------------------------------------------------------------
# render_security_page passes extra context to templates
# ---------------------------------------------------------------------------


def test_render_security_page_passes_context_to_template():
    """render_security_page forwards extra kwargs to the template."""
    html = render_security_page(
        "security/security_users.html",
        title_key="webui.security.users.title",
        subtitle_key="webui.security.users.subtitle",
        active_path="/monitor/security/users",
        total_count=3,
        active_count=2,
        search_query="",
        users=[],
    )
    assert "3 users" in html
    assert "2 active" in html
