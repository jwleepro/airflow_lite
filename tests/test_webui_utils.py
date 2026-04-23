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


# ---------------------------------------------------------------------------
# Accessible-name tests (issue #99)
# ---------------------------------------------------------------------------

def test_pipeline_detail_close_buttons_have_aria_labels():
    """Close buttons in node-panel and task-panel must carry aria-label."""
    template_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "airflow_lite" / "api" / "templates" / "pipeline_detail.html"
    )
    html = template_path.read_text(encoding="utf-8")
    assert 'aria-label="Close node panel"' in html
    assert 'aria-label="Close task panel"' in html


def test_admin_connections_icon_buttons_have_aria_labels():
    """✏ and ✕ action buttons in admin_connections must carry aria-label."""
    template_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "airflow_lite" / "api" / "templates" / "admin" / "admin_connections.html"
    )
    html = template_path.read_text(encoding="utf-8")
    # Each row action must have an aria-label pattern
    assert 'aria-label="Edit connection' in html
    assert 'aria-label="Delete connection' in html


def test_admin_variables_icon_buttons_have_aria_labels():
    """✏ and ✕ action buttons in admin_variables must carry aria-label."""
    template_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "airflow_lite" / "api" / "templates" / "admin" / "admin_variables.html"
    )
    html = template_path.read_text(encoding="utf-8")
    assert 'aria-label="Edit variable' in html
    assert 'aria-label="Delete variable' in html


def test_admin_pools_icon_buttons_have_aria_labels():
    """✏ and ✕ action buttons in admin_pools must carry aria-label."""
    template_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "airflow_lite" / "api" / "templates" / "admin" / "admin_pools.html"
    )
    html = template_path.read_text(encoding="utf-8")
    assert 'aria-label="Edit pool' in html
    assert 'aria-label="Delete pool' in html


def test_task_logs_attempt_buttons_have_aria_labels():
    """Attempt selector buttons in task_logs must carry aria-label."""
    template_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "airflow_lite" / "api" / "templates" / "task_logs.html"
    )
    html = template_path.read_text(encoding="utf-8")
    assert 'aria-label="Attempt' in html
    assert 'aria-label="Filter by log level' in html
