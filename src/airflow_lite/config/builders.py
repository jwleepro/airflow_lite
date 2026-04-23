"""설정 타입별 빌더.

YAML dict → dataclass 변환 로직을 모은다. 공통 패턴
(빈 dict → 기본 인스턴스, 그 외 → int 강제 후 ``cls(**values)``)은
:func:`_build_config` 로 추출했다.
"""

from __future__ import annotations

from typing import Any, TypeVar

from ._coerce import coerce_int_fields
from .settings import (
    AlertingConfig,
    AlertingTriggersConfig,
    ApiConfig,
    EmailChannelConfig,
    ExportConfig,
    MartConfig,
    SchedulerConfig,
    WebUIConfig,
    WebhookChannelConfig,
)
from ..i18n import require_supported_language

__all__ = [
    "build_alerting_config",
    "build_api_config",
    "build_export_config",
    "build_mart_config",
    "build_scheduler_config",
    "build_webui_config",
]

T = TypeVar("T")


def _build_config(
    cls: type[T],
    data: dict | None,
    *,
    int_fields: tuple[str, ...] = (),
    prefix: str = "",
) -> T:
    """공통 빌더: 빈 dict 는 기본 인스턴스, 그 외는 int 강제 후 cls(**values)."""
    if not data:
        return cls()
    values: dict[str, Any] = dict(data)
    if int_fields:
        values = coerce_int_fields(values, int_fields, prefix)
    return cls(**values)


def build_api_config(data: dict | None) -> ApiConfig:
    return _build_config(ApiConfig, data, int_fields=("port",), prefix="api")


def build_mart_config(data: dict | None) -> MartConfig:
    return _build_config(MartConfig, data)


def build_scheduler_config(data: dict | None) -> SchedulerConfig:
    return _build_config(
        SchedulerConfig,
        data,
        int_fields=("max_instances", "misfire_grace_time_seconds", "dispatch_max_workers"),
        prefix="scheduler",
    )


def build_export_config(data: dict | None) -> ExportConfig:
    return _build_config(
        ExportConfig,
        data,
        int_fields=(
            "retention_hours",
            "cleanup_cooldown_seconds",
            "max_workers",
            "rows_per_batch",
        ),
        prefix="export",
    )


def _build_email_channel(data: dict) -> EmailChannelConfig:
    return _build_config(
        EmailChannelConfig,
        data,
        int_fields=("smtp_port",),
        prefix="alerting.channels[].smtp_port",
    )


def _build_webhook_channel(data: dict) -> WebhookChannelConfig:
    return _build_config(WebhookChannelConfig, data)


_ALERT_CHANNEL_BUILDERS: dict[str, Any] = {
    "email": _build_email_channel,
    "webhook": _build_webhook_channel,
}


def build_alerting_config(data: dict | None) -> AlertingConfig:
    if not data:
        return AlertingConfig()

    channels: list = []
    for channel_data in data.get("channels", []):
        channel_values = dict(channel_data)
        channel_type = channel_values.get("type")
        builder = _ALERT_CHANNEL_BUILDERS.get(channel_type)
        if builder is None:
            raise ValueError(f"알 수 없는 알림 채널 타입: {channel_type!r}")
        channels.append(builder(channel_values))

    triggers = AlertingTriggersConfig(**data.get("triggers", {}))
    return AlertingConfig(channels=channels, triggers=triggers)


_WEBUI_INT_FIELDS: tuple[str, ...] = (
    "monitor_refresh_seconds",
    "analytics_refresh_seconds",
    "exports_active_refresh_seconds",
    "exports_idle_refresh_seconds",
    "recent_runs_limit",
    "detail_preview_page_size",
    "analytics_export_jobs_limit",
    "export_jobs_page_limit",
    "error_message_max_length",
)


def build_webui_config(data: dict | None) -> WebUIConfig:
    if not data:
        return WebUIConfig()

    values = coerce_int_fields(dict(data), _WEBUI_INT_FIELDS, "webui")
    if "default_language" in values:
        values["default_language"] = require_supported_language(
            str(values["default_language"]), field_name="webui.default_language"
        )
    return WebUIConfig(**values)
