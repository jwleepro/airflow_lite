"""설정 dict 내 타입 강제 유틸리티.

settings.py 와 builders.py 양쪽에서 공유되는 변환 로직을 격리해
순환 참조를 막고 지연 import 를 제거한다.
"""

from __future__ import annotations

__all__ = ["coerce_int", "coerce_int_fields"]


def coerce_int(value: int | str, field_name: str) -> int:
    """문자열/정수를 int 로 변환. 실패 시 ValueError."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"정수 필드 '{field_name}'의 값이 올바르지 않습니다: {value!r}"
        ) from exc


def coerce_int_fields(
    values: dict, field_names: tuple[str, ...], prefix: str
) -> dict:
    """dict 내 지정된 필드를 int 로 변환한 새 dict 반환."""
    coerced = dict(values)
    for field_name in field_names:
        if field_name in coerced:
            coerced[field_name] = coerce_int(
                coerced[field_name], f"{prefix}.{field_name}"
            )
    return coerced
