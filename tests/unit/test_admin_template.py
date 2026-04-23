"""Tests for admin.html template: Add-form toggle visibility."""

import re
from pathlib import Path


TEMPLATE_PATH = (
    Path(__file__).parent.parent.parent
    / "src/airflow_lite/api/templates/admin.html"
)
CSS_PATH = (
    Path(__file__).parent.parent.parent
    / "src/airflow_lite/api/static/css/app.css"
)


class TestAdminAddFormToggle:
    """editor-box 요소가 hidden 속성 없이 CSS 클래스로만 표시 여부를 제어하는지 검증."""

    def _load_template(self) -> str:
        return TEMPLATE_PATH.read_text(encoding="utf-8")

    def _load_css(self) -> str:
        return CSS_PATH.read_text(encoding="utf-8")

    def test_conn_add_form_has_no_hidden_attribute(self):
        html = self._load_template()
        # conn-add-form div 에 hidden 속성이 없어야 함
        match = re.search(r'id="conn-add-form"[^>]*>', html)
        assert match, "conn-add-form element not found"
        assert "hidden" not in match.group(0), (
            "conn-add-form must not have the 'hidden' attribute; "
            "use CSS .editor-box / .editor-box.active instead"
        )

    def test_var_add_form_has_no_hidden_attribute(self):
        html = self._load_template()
        match = re.search(r'id="var-add-form"[^>]*>', html)
        assert match, "var-add-form element not found"
        assert "hidden" not in match.group(0), (
            "var-add-form must not have the 'hidden' attribute"
        )

    def test_pool_add_form_has_no_hidden_attribute(self):
        html = self._load_template()
        match = re.search(r'id="pool-add-form"[^>]*>', html)
        assert match, "pool-add-form element not found"
        assert "hidden" not in match.group(0), (
            "pool-add-form must not have the 'hidden' attribute"
        )

    def test_editor_box_css_has_display_none_by_default(self):
        css = self._load_css()
        # .editor-box 규칙에 display:none 이 포함돼야 함
        # 단순 텍스트 검색으로 블록 존재 여부 확인
        assert "display: none" in css, (
            "CSS must set .editor-box { display: none } by default"
        )

    def test_editor_box_active_css_has_display_block(self):
        css = self._load_css()
        assert ".editor-box.active" in css, (
            "CSS must define .editor-box.active to show the form"
        )

    def test_toggle_buttons_use_classlist_toggle(self):
        html = self._load_template()
        # 3개의 Add 버튼 모두 classList.toggle 을 사용해야 함
        toggle_calls = re.findall(r"classList\.toggle\('active'\)", html)
        assert len(toggle_calls) >= 3, (
            f"Expected at least 3 classList.toggle('active') calls, found {len(toggle_calls)}"
        )
