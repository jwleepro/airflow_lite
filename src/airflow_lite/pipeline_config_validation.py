from __future__ import annotations

import json
import re
from datetime import date, datetime, time
from typing import Any, Mapping

from jinja2.nativetypes import NativeEnvironment

_LEGACY_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")
_NATIVE_ENV = NativeEnvironment()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


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


def build_query_render_context(execution_date: date) -> dict[str, Any]:
    logical_dt = datetime.combine(execution_date, time.min)
    data_interval_start = datetime(execution_date.year, execution_date.month, 1)
    if execution_date.month == 12:
        data_interval_end = datetime(execution_date.year + 1, 1, 1)
    else:
        data_interval_end = datetime(execution_date.year, execution_date.month + 1, 1)

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


def render_source_query(
    source_where_template: str | None,
    source_bind_params: Any,
    *,
    execution_date: date,
) -> tuple[str | None, dict[str, Any]]:
    normalized_template, custom_bind_params = validate_source_query_config(
        source_where_template,
        source_bind_params,
    )
    if normalized_template is None:
        return None, {}

    render_context = build_query_render_context(execution_date)
    rendered_where = _render_template_value(normalized_template, render_context)
    merged_params = build_default_bind_params(render_context)
    for key, value in custom_bind_params.items():
        merged_params[key] = _render_template_value(value, render_context)
    return str(rendered_where).strip(), merged_params


def _render_template_value(value: Any, context: dict[str, Any]) -> Any:
    if not isinstance(value, str):
        return value
    if "{{" not in value and "{%" not in value and "{#" not in value:
        return value
    return _NATIVE_ENV.from_string(value).render(**context)
