"""실행(run/step) 상태 문자열의 단일 소스.

`status_tone`과 monitor 집계가 서로 다른 파일에서 같은 문자열 세트를
하드코딩하던 것을 여기로 모은다. 새 상태 추가 시 이 파일만 고치면 된다.
"""
from __future__ import annotations


# 톤 → 해당 톤으로 분류되는 상태 문자열(소문자) 집합
STATUS_GROUPS: dict[str, frozenset[str]] = {
    "ok": frozenset({"success", "completed"}),
    "warn": frozenset({"running", "pending", "queued"}),
    "bad": frozenset({"failed"}),
}


def _norm(status: str | None) -> str:
    return (status or "").lower()


def tone_of(status: str | None) -> str:
    """상태 문자열을 UI 톤(``ok``/``warn``/``bad``/``neutral``)으로 매핑."""
    s = _norm(status)
    for tone, members in STATUS_GROUPS.items():
        if s in members:
            return tone
    return "neutral"


def latest_run_status(row: dict) -> str:
    """파이프라인 행의 ``latest_run.status``를 소문자로 안전 추출."""
    return _norm((row.get("latest_run") or {}).get("status"))


def count_by_tone(rows: list[dict]) -> dict[str, int]:
    """pipeline 행 목록을 한 번만 순회해 톤별 카운트를 반환.

    누락된 톤은 0으로 채워 돌려준다.
    """
    counts = {tone: 0 for tone in STATUS_GROUPS}
    for row in rows:
        s = latest_run_status(row)
        for tone, members in STATUS_GROUPS.items():
            if s in members:
                counts[tone] += 1
                break
    return counts
