"""webui 공통 유틸 단위 테스트.

리팩토링으로 새로 추출된 `build_url`과 `webui_status` 모듈의 동작을
고정한다. 렌더러가 의존하는 핵심 계약(상태 톤 매핑, 쿼리 파라미터 생성)
회귀를 방지하는 목적이다.
"""

from __future__ import annotations

from pathlib import Path

from airflow_lite.api.template_env import _ENV
from airflow_lite.api.webui_helpers import build_url
from airflow_lite.api.webui_status import (
    count_by_tone,
    latest_run_status,
    tone_of,
)


class TestBuildUrl:
    def test_no_params_returns_path(self):
        assert build_url("/monitor") == "/monitor"

    def test_none_values_dropped(self):
        assert build_url("/monitor", dataset=None) == "/monitor"

    def test_single_param(self):
        assert build_url("/monitor", dataset="orders") == "/monitor?dataset=orders"

    def test_multiple_params_order_preserved(self):
        url = build_url("/m", dataset="x", dashboard_id="d1")
        assert url == "/m?dataset=x&dashboard_id=d1"

    def test_special_chars_escaped(self):
        url = build_url("/m", dataset="a b&c")
        assert url == "/m?dataset=a+b%26c"

    def test_mixed_none_and_value(self):
        assert build_url("/m", a=None, b="1") == "/m?b=1"


class TestToneOf:
    def test_ok_tones(self):
        assert tone_of("success") == "ok"
        assert tone_of("completed") == "ok"
        assert tone_of("SUCCESS") == "ok"  # 대소문자 무관

    def test_warn_tones(self):
        for s in ("running", "pending", "queued"):
            assert tone_of(s) == "warn"

    def test_bad_tone(self):
        assert tone_of("failed") == "bad"

    def test_unknown_is_neutral(self):
        assert tone_of("skipped") == "neutral"
        assert tone_of(None) == "neutral"
        assert tone_of("") == "neutral"

class TestLatestRunStatus:
    def test_missing_latest_run(self):
        assert latest_run_status({}) == ""
        assert latest_run_status({"latest_run": None}) == ""

    def test_normal(self):
        assert latest_run_status({"latest_run": {"status": "Success"}}) == "success"


class TestCountByTone:
    def test_counts_include_all_groups_even_if_zero(self):
        result = count_by_tone([])
        assert result == {"ok": 0, "warn": 0, "bad": 0, "paused": 0}

    def test_mixed_rows(self):
        rows = [
            {"latest_run": {"status": "success"}},
            {"latest_run": {"status": "completed"}},
            {"latest_run": {"status": "running"}, "is_paused": True},
            {"latest_run": {"status": "failed"}},
            {"latest_run": None},  # no tone
            {},  # no tone
        ]
        result = count_by_tone(rows)
        assert result == {"ok": 2, "warn": 1, "bad": 1, "paused": 1}


def test_app_css_does_not_include_legacy_btn_delete_alias():
    css_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "airflow_lite"
        / "api"
        / "static"
        / "css"
        / "app.css"
    )

    css = css_path.read_text(encoding="utf-8")

    assert ".btn-delete" not in css


def test_template_env_does_not_register_unused_icon_globals():
    assert "ICON_API" not in _ENV.globals
    assert "ICON_HOME" in _ENV.globals
    assert "ICON_EXPORTS" in _ENV.globals
    assert "ICON_PIPELINES" in _ENV.globals
    assert "ICON_ANALYTICS" in _ENV.globals
    assert "ICON_ADMIN" in _ENV.globals
    assert "ICON_DOCS" in _ENV.globals


def test_template_env_exposes_admin_path_constants():
    """Admin sub-path constants must be available as Jinja globals."""
    assert "MONITOR_ADMIN_CONNECTIONS_PATH" in _ENV.globals
    assert "MONITOR_ADMIN_VARIABLES_PATH" in _ENV.globals
    assert "MONITOR_ADMIN_POOLS_PATH" in _ENV.globals
    assert "MONITOR_ADMIN_PROVIDERS_PATH" in _ENV.globals
    assert "MONITOR_ADMIN_PLUGINS_PATH" in _ENV.globals
    assert "MONITOR_ADMIN_CONFIG_PATH" in _ENV.globals
    assert "MONITOR_ADMIN_XCOMS_PATH" in _ENV.globals


def test_template_env_exposes_security_path_constants():
    """Security sub-path constants must be available as Jinja globals."""
    assert "MONITOR_SECURITY_PATH" in _ENV.globals
    assert "MONITOR_SECURITY_USERS_PATH" in _ENV.globals
    assert "MONITOR_SECURITY_ROLES_PATH" in _ENV.globals
    assert "MONITOR_SECURITY_PERMISSIONS_PATH" in _ENV.globals


def test_base_template_uses_path_constants_not_literals():
    """base.html sidebar links must use Jinja path constant variables, not raw strings."""
    template_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "airflow_lite"
        / "api"
        / "templates"
        / "base.html"
    )
    html = template_path.read_text(encoding="utf-8")

    # Admin sidebar links must reference constants
    assert "MONITOR_ADMIN_CONNECTIONS_PATH" in html
    assert "MONITOR_ADMIN_VARIABLES_PATH" in html
    assert "MONITOR_ADMIN_POOLS_PATH" in html
    # Security sidebar links must reference constants
    assert "MONITOR_SECURITY_USERS_PATH" in html
    assert "MONITOR_SECURITY_ROLES_PATH" in html
    assert "MONITOR_SECURITY_PERMISSIONS_PATH" in html
    # No bare literal admin paths in link/form targets
    assert 'href="{{ lang_url(\'/monitor/admin/connections\') }}"' not in html
    assert 'href="{{ lang_url(\'/monitor/security/users\') }}"' not in html


def test_browse_templates_use_path_constants_not_literals():
    """Browse form actions must reference Jinja path constants."""
    templates_dir = (
        Path(__file__).resolve().parents[1]
        / "src" / "airflow_lite" / "api" / "templates" / "browse"
    )
    for tmpl in templates_dir.glob("*.html"):
        html = tmpl.read_text(encoding="utf-8")
        assert 'action="/monitor/browse/' not in html, (
            f"{tmpl.name} still contains a hardcoded browse form action"
        )


def test_security_user_template_uses_path_constant_not_literal():
    """security_users.html form action must reference a Jinja path constant."""
    tmpl_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "airflow_lite" / "api" / "templates" / "security" / "security_users.html"
    )
    html = tmpl_path.read_text(encoding="utf-8")
    assert 'action="/monitor/security/users"' not in html


def test_base_template_contains_sidebar_redesign_structure():
    template_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "airflow_lite"
        / "api"
        / "templates"
        / "base.html"
    )
    html = template_path.read_text(encoding="utf-8")

    assert 'id="sidebar"' in html
    assert 'id="sidebar-toggle"' in html
    assert 'data-submenu-toggle="browse"' in html
    assert 'data-submenu-toggle="admin"' in html
    assert 'data-submenu-toggle="security"' in html
    assert 'class="sidebar-profile"' in html
