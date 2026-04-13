"""webui 공통 유틸 단위 테스트.

리팩토링으로 새로 추출된 `build_url`과 `webui_status` 모듈의 동작을
고정한다. 렌더러가 의존하는 핵심 계약(상태 톤 매핑, 쿼리 파라미터 생성)
회귀를 방지하는 목적이다.
"""

from __future__ import annotations

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
        assert result == {"ok": 0, "warn": 0, "bad": 0}

    def test_mixed_rows(self):
        rows = [
            {"latest_run": {"status": "success"}},
            {"latest_run": {"status": "completed"}},
            {"latest_run": {"status": "running"}},
            {"latest_run": {"status": "failed"}},
            {"latest_run": None},  # no tone
            {},  # no tone
        ]
        result = count_by_tone(rows)
        assert result == {"ok": 2, "warn": 1, "bad": 1}
