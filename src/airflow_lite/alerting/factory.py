"""Alert 채널 조립 팩토리.

Settings의 alerting 설정에서 AlertManager를 생성한다.
runtime.py의 SRP 위반을 해소하기 위해 분리.
"""
from airflow_lite.alerting.base import AlertManager
from airflow_lite.alerting.email import EmailAlertChannel
from airflow_lite.alerting.webhook import WebhookAlertChannel
from airflow_lite.config.settings import EmailChannelConfig, WebhookChannelConfig


def build_alert_manager(alerting_config) -> AlertManager:
    """alerting 설정에서 AlertManager를 생성한다."""
    alert_channels = []
    for ch_config in alerting_config.channels:
        if isinstance(ch_config, EmailChannelConfig):
            alert_channels.append(
                EmailAlertChannel(
                    smtp_host=ch_config.smtp_host,
                    smtp_port=ch_config.smtp_port,
                    sender=ch_config.sender,
                    recipients=ch_config.recipients,
                )
            )
        elif isinstance(ch_config, WebhookChannelConfig):
            alert_channels.append(
                WebhookAlertChannel(
                    url=ch_config.url,
                    timeout=ch_config.timeout,
                )
            )
    return AlertManager(
        channels=alert_channels,
        triggers={
            "on_failure": alerting_config.triggers.on_failure,
            "on_success": alerting_config.triggers.on_success,
        },
    )
