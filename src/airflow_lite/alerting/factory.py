"""Alert 채널 조립 팩토리.

Settings의 alerting 설정에서 AlertManager를 생성한다.
runtime.py의 SRP 위반을 해소하기 위해 분리.
"""
from airflow_lite.alerting.base import AlertChannel, AlertManager
from airflow_lite.alerting.email import EmailAlertChannel
from airflow_lite.alerting.webhook import WebhookAlertChannel


_CHANNEL_BUILDERS: dict[str, type] = {
    "email": EmailAlertChannel,
    "webhook": WebhookAlertChannel,
}


def _build_channel(ch_config) -> AlertChannel:
    channel_type = getattr(ch_config, "type", None)
    builder = _CHANNEL_BUILDERS.get(channel_type)
    if builder is None:
        raise ValueError(f"unsupported alert channel type: {channel_type}")
    kwargs = {k: v for k, v in ch_config.__dict__.items() if k != "type"}
    return builder(**kwargs)


def build_alert_manager(alerting_config) -> AlertManager:
    """alerting 설정에서 AlertManager를 생성한다."""
    alert_channels = [_build_channel(ch) for ch in alerting_config.channels]
    return AlertManager(
        channels=alert_channels,
        triggers={
            "on_failure": alerting_config.triggers.on_failure,
            "on_success": alerting_config.triggers.on_success,
        },
    )
