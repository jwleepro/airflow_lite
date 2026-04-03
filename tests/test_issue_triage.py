from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "issue_triage.py"
SPEC = importlib.util.spec_from_file_location("issue_triage", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
ISSUE_TRIAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ISSUE_TRIAGE)


def test_bug_issue_maps_area_and_priority_labels() -> None:
    body = """
### 문제 요약
백필 실행 실패

### 영향 범위
area:backend, area:ci

### 영향도
서비스 중단 또는 데이터 손상 가능
""".strip()

    plan = ISSUE_TRIAGE.compute_label_plan(
        body,
        ["bug", "status:needs-triage", "priority:medium"],
    )

    assert plan["desired_labels"] == ["area:backend", "area:ci", "priority:high"]
    assert sorted(plan["labels_to_add"]) == ["area:backend", "area:ci", "priority:high"]
    assert plan["labels_to_remove"] == ["priority:medium"]


def test_feature_issue_preserves_feature_type_and_rebalances_priority() -> None:
    body = """
### 요청 요약
새 대시보드 요청

### 관련 영역
area:frontend, area:docs

### 요청 긴급도
아이디어 탐색 또는 장기 후보
""".strip()

    plan = ISSUE_TRIAGE.compute_label_plan(
        body,
        ["enhancement", "type:feature", "priority:medium", "area:backend"],
    )

    assert plan["desired_labels"] == [
        "area:docs",
        "area:frontend",
        "priority:low",
        "type:feature",
    ]
    assert sorted(plan["labels_to_add"]) == ["area:docs", "area:frontend", "priority:low"]
    assert sorted(plan["labels_to_remove"]) == ["area:backend", "priority:medium"]


def test_task_request_maps_requested_type_and_removes_previous_managed_labels() -> None:
    body = """
### 작업 요약
문서 정리

### 요청 유형
documentation

### 관련 영역
area:docs

### 요청 긴급도
곧 필요하지만 우회 가능
""".strip()

    plan = ISSUE_TRIAGE.compute_label_plan(
        body,
        ["question", "priority:high", "area:backend"],
    )

    assert plan["desired_labels"] == ["area:docs", "documentation", "priority:medium"]
    assert sorted(plan["labels_to_add"]) == ["area:docs", "documentation", "priority:medium"]
    assert sorted(plan["labels_to_remove"]) == ["area:backend", "priority:high", "question"]


def test_human_review_signals_add_needs_human_without_managing_removal() -> None:
    body = """
### 요청 요약
운영 반영 필요한 개선

### 관련 영역
area:infra

### 수용 기준
- 운영 절차 문서 반영

### 사람 검토 필요 신호
- [x] 운영 반영 필요 (Windows 서비스, 스케줄, 배포 절차, 설정 변경 포함)
- [ ] 데이터 위험 있음 (삭제, 재적재, 백필, 마이그레이션, 스키마 영향 포함)
- [ ] 외부 시스템 영향 있음 (Oracle, 파일 저장소, 외부 API, 알림, 인증 시스템 포함)
- [ ] 사람 승인 또는 판단 필요 (우선순위, 정책, 위험 수용 판단 등)

### 요청 긴급도
가까운 시일 내 필요하지만 우회 가능
""".strip()

    plan = ISSUE_TRIAGE.compute_label_plan(
        body,
        ["enhancement", "type:feature", "priority:medium"],
    )

    assert plan["desired_labels"] == [
        "area:infra",
        "needs-human",
        "priority:medium",
        "type:feature",
    ]
    assert sorted(plan["labels_to_add"]) == ["area:infra", "needs-human"]
    assert plan["labels_to_remove"] == []


def test_needs_human_is_not_removed_when_signal_is_absent() -> None:
    body = """
### 문제 요약
문서만 보완 필요

### 영향 범위
area:docs

### 영향도
우회 가능한 문제 또는 제한적 영향
""".strip()

    plan = ISSUE_TRIAGE.compute_label_plan(
        body,
        ["bug", "needs-human", "priority:medium"],
    )

    assert plan["desired_labels"] == ["area:docs", "priority:low"]
    assert sorted(plan["labels_to_add"]) == ["area:docs", "priority:low"]
    assert plan["labels_to_remove"] == ["priority:medium"]
