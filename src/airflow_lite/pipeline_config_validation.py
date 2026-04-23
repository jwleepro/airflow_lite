from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Mapping

from jinja2.nativetypes import NativeEnvironment

_LEGACY_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")
_BIND_NAME_PATTERN = re.compile(r":(\w+)")
_INTERVAL_PATTERN = re.compile(r"^interval:(\d+)([smhd]?)$", re.IGNORECASE)
_INTERVAL_UNIT_TO_KWARG = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
}
_NATIVE_ENV = NativeEnvironment()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def validate_data_interval_schedule(schedule: str | None) -> str:
    normalized = normalize_optional_text(schedule)
    if normalized is None:
        raise ValueError("data_interval 계산을 위해 schedule 값이 필요합니다.")

    interval_match = _INTERVAL_PATTERN.fullmatch(normalized)
    if interval_match:
        value = int(interval_match.group(1))
        if value <= 0:
            raise ValueError(
                "data_interval 계산을 위해 interval 값은 1 이상이어야 합니다: "
                f"{normalized}"
            )
        return normalized

    try:
        from apscheduler.triggers.cron import CronTrigger

        CronTrigger.from_crontab(normalized)
    except ValueError as exc:
        raise ValueError(
            "data_interval 계산을 위해 schedule 은 "
            "Airflow cron('분 시 일 월 요일', 예: '0 2 * * *') 또는 "
            "'interval:30m' 형식이어야 합니다: "
            f"{normalized}"
        ) from exc

    return normalized


def parse_source_bind_params(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return {}
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise ValueError("source_bind_params 는 JSON 객체여야 합니다.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("source_bind_params 는 JSON 객체여야 합니다.")
        return {str(key): item for key, item in parsed.items()}
    raise ValueError("source_bind_params 는 JSON 객체 또는 문자열만 허용합니다.")


def serialize_source_bind_params(value: Any) -> str | None:
    params = parse_source_bind_params(value)
    if not params:
        return None
    return json.dumps(params, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def validate_source_query_config(
    source_where_template: str | None,
    source_bind_params: Any = None,
    *,
    strategy: str | None = None,
) -> tuple[str | None, dict[str, Any]]:
    normalized_template = normalize_optional_text(source_where_template)
    bind_params = parse_source_bind_params(source_bind_params)

    if normalized_template is None and bind_params:
        raise ValueError(
            "source_bind_params 는 source_where_template 이 있을 때만 설정할 수 있습니다."
        )
    if strategy == "full" and normalized_template is None:
        raise ValueError("full 전략은 source_where_template 이 필요합니다.")

    return normalized_template, bind_params


def coerce_source_query_from_mapping(
    mapping: Mapping[str, Any],
    *,
    strategy: str | None = None,
) -> tuple[str | None, dict[str, Any]]:
    """dict-like 입력에서 source_where_template / source_bind_params 를 꺼내 정규화.

    source_where_template 이 비어있으면 레거시 partition_column 을 템플릿으로 폴백한다.
    sqlite3.Row 등 Mapping 미준수 객체는 호출 측에서 dict(row) 로 변환 후 전달.
    """
    template = mapping.get("source_where_template")
    if not normalize_optional_text(template):
        template = build_legacy_source_where_template(mapping.get("partition_column"))
    return validate_source_query_config(
        template,
        mapping.get("source_bind_params"),
        strategy=strategy,
    )


def coerce_source_query_for_storage(
    source_where_template: str | None,
    source_bind_params: Any = None,
    *,
    strategy: str | None = None,
) -> tuple[str | None, str | None]:
    """저장 직전 경로용: validate 후 bind_params 를 JSON 문자열로 직렬화해 반환."""
    template, bind_params = validate_source_query_config(
        source_where_template, source_bind_params, strategy=strategy
    )
    return template, serialize_source_bind_params(bind_params)


def build_legacy_source_where_template(partition_column: str | None) -> str | None:
    identifier = normalize_optional_text(partition_column)
    if identifier is None:
        return None
    if not _LEGACY_IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(
            "기존 partition_column 값을 source_where_template 로 변환할 수 없습니다: "
            f"{identifier}"
        )
    return (
        f"{identifier} >= :data_interval_start "
        f"AND {identifier} < :data_interval_end"
    )


def _to_naive_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(value.tzinfo).replace(tzinfo=None)


def _resolve_interval_window(schedule: str) -> timedelta | None:
    match = _INTERVAL_PATTERN.fullmatch(schedule)
    if match is None:
        return None
    value = int(match.group(1))
    unit = (match.group(2) or "s").lower()
    return timedelta(**{_INTERVAL_UNIT_TO_KWARG[unit]: value})


def _resolve_cron_interval(execution_date: date, schedule: str) -> tuple[datetime, datetime]:
    from apscheduler.triggers.cron import CronTrigger

    trigger = CronTrigger.from_crontab(schedule)
    tzinfo = trigger.timezone
    if tzinfo is None:
        day_start = datetime.combine(execution_date, time.min)
    else:
        day_start = datetime.combine(execution_date, time.min, tzinfo=tzinfo)

    current_fire = trigger.get_next_fire_time(None, day_start - timedelta(seconds=1))
    if current_fire is None or _to_naive_datetime(current_fire).date() != execution_date:
        raise ValueError(
            "data_interval 계산 실패: execution_date 가 schedule fire 시점과 맞지 않습니다. "
            f"execution_date={execution_date.isoformat()} schedule={schedule}"
        )

    lookback_days = _estimate_cron_lookback_days(schedule)
    search_start = day_start - timedelta(days=lookback_days)
    previous_fire = None
    cursor = trigger.get_next_fire_time(None, search_start)
    guard = 0
    while cursor is not None and cursor < current_fire:
        previous_fire = cursor
        cursor = trigger.get_next_fire_time(cursor, cursor + timedelta(seconds=1))
        guard += 1
        if guard > 200000:
            raise ValueError(
                "data_interval 계산 실패: schedule 구간 탐색이 비정상적으로 길어졌습니다. "
                f"execution_date={execution_date.isoformat()} schedule={schedule}"
            )

    if previous_fire is None:
        raise ValueError(
            "data_interval 계산 실패: 이전 스케줄 구간을 찾지 못했습니다. "
            f"execution_date={execution_date.isoformat()} schedule={schedule}"
        )

    return _to_naive_datetime(previous_fire), _to_naive_datetime(current_fire)


def resolve_data_interval(execution_date: date, schedule: str) -> tuple[datetime, datetime]:
    normalized_schedule = validate_data_interval_schedule(schedule)
    interval_window = _resolve_interval_window(normalized_schedule)
    if interval_window is not None:
        data_interval_end = datetime.combine(execution_date, time.min)
        data_interval_start = data_interval_end - interval_window
        return data_interval_start, data_interval_end
    return _resolve_cron_interval(execution_date, normalized_schedule)


def _estimate_cron_lookback_days(schedule: str) -> int:
    minute, hour, day, month, weekday = schedule.split()
    if day != "*" or month != "*" or weekday != "*":
        return 400
    if hour != "*" or minute != "*":
        return 3
    return 1


def build_query_render_context(execution_date: date, schedule: str) -> dict[str, Any]:
    data_interval_start, data_interval_end = resolve_data_interval(execution_date, schedule)
    logical_dt = data_interval_start

    return {
        "logical_date": logical_dt,
        "data_interval_start": data_interval_start,
        "data_interval_end": data_interval_end,
    }


def build_default_bind_params(context: dict[str, Any]) -> dict[str, Any]:
    bind_params: dict[str, Any] = {}
    for key in ("logical_date", "data_interval_start", "data_interval_end"):
        value = context[key]
        bind_params[key] = value
        bind_params[f"{key}_year"] = value.year
        bind_params[f"{key}_month"] = value.month
        bind_params[f"{key}_day"] = value.day
        bind_params[f"{key}_hour"] = value.hour
        bind_params[f"{key}_minute"] = value.minute
        bind_params[f"{key}_second"] = value.second
    return bind_params


def build_interval_bind_params(execution_date: date, schedule: str) -> dict[str, Any]:
    context = build_query_render_context(execution_date, schedule)
    return build_default_bind_params(context)


def render_source_query(
    source_where_template: str | None,
    source_bind_params: Any,
    *,
    execution_date: date,
    schedule: str,
) -> tuple[str | None, dict[str, Any]]:
    normalized_template, custom_bind_params = validate_source_query_config(
        source_where_template,
        source_bind_params,
    )
    if normalized_template is None:
        return None, {}

    render_context = build_query_render_context(execution_date, schedule)
    rendered_where = _render_template_value(normalized_template, render_context)
    merged_params = build_default_bind_params(render_context)
    for key, value in custom_bind_params.items():
        merged_params[key] = _render_template_value(value, render_context)

    where_str = str(rendered_where).strip()
    used_names = set(_BIND_NAME_PATTERN.findall(where_str))
    filtered_params = {k: v for k, v in merged_params.items() if k in used_names}
    return where_str, filtered_params


def _render_template_value(value: Any, context: dict[str, Any]) -> Any:
    if not isinstance(value, str):
        return value
    if "{{" not in value and "{%" not in value and "{#" not in value:
        return value
    return _NATIVE_ENV.from_string(value).render(**context)
