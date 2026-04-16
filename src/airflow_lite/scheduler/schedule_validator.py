"""Schedule 문자열 검증 및 APScheduler Trigger 빌더.

웹 폼과 JSON API, 실제 스케줄러 등록 경로가 동일한 파서를 공유해
저장된 값과 런타임 해석이 어긋나지 않도록 한다.
"""

from __future__ import annotations

import re

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

INTERVAL_PATTERN = re.compile(r"^interval:(\d+)([smhd]?)$", re.IGNORECASE)
_UNIT_MAP = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


def build_trigger(schedule: str):
    """schedule 문자열을 APScheduler Trigger로 변환한다.

    지원 형식:
    - cron: '0 2 * * *' (분 시 일 월 요일)
    - interval: 'interval:30m', 'interval:6h', 'interval:15' (기본 초)

    유효하지 않으면 사용자 친화적인 한글 메시지로 ValueError를 raise한다.
    """
    if schedule is None or not str(schedule).strip():
        raise ValueError("schedule 값이 비어 있습니다.")

    text = str(schedule).strip()
    match = INTERVAL_PATTERN.fullmatch(text)
    if match:
        value = int(match.group(1))
        unit = (match.group(2) or "s").lower()
        if value <= 0:
            raise ValueError(f"interval 값은 1 이상이어야 합니다: {text}")
        return IntervalTrigger(**{_UNIT_MAP[unit]: value})

    try:
        return CronTrigger.from_crontab(text)
    except ValueError as exc:
        raise ValueError(
            f"schedule 형식이 올바르지 않습니다: '{text}'. "
            f"cron은 '분 시 일 월 요일' (예: '0 2 * * *'), "
            f"interval은 'interval:30m' 형태여야 합니다. ({exc})"
        ) from exc


def validate_schedule(schedule: str) -> None:
    """schedule이 유효하지 않으면 ValueError를 raise한다."""
    build_trigger(schedule)
