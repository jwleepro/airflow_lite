"""runner_map / backfill_map 항목을 실제 객체로 풀어내는 공통 유틸.

app.state 의 map 에는 이미 생성된 인스턴스가 올 수도, 지연 생성용
factory(callable) 가 올 수도 있다. 라우트마다 같은 분기를 반복하지 않도록
한 곳으로 모았다.
"""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")

__all__ = ["resolve_factory", "resolve_runner", "resolve_backfill_manager"]


def resolve_factory(entry, method_name: str, map_label: str) -> object:
    """이미 인스턴스면 그대로, 아니면 호출해 생성. ``method_name`` 을 가져야 유효.

    Args:
        entry: map 에서 꺼낸 원본 값 (인스턴스 또는 factory callable).
        method_name: 대상 객체가 노출해야 할 메서드 이름 (존재로 인스턴스 판별).
        map_label: 에러 메시지에 쓰일 map 명 (예: ``"runner_map"``).
    """
    if hasattr(entry, method_name):
        return entry
    if callable(entry):
        return entry()
    raise TypeError(
        f"{map_label} 항목은 {method_name}() 를 가진 객체 또는 factory 여야 합니다."
    )


def resolve_runner(entry):
    return resolve_factory(entry, "run", "runner_map")


def resolve_backfill_manager(entry):
    return resolve_factory(entry, "run_backfill", "backfill_map")
