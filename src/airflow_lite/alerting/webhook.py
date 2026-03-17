import logging

import httpx

from airflow_lite.alerting.base import AlertChannel, AlertMessage

logger = logging.getLogger("airflow_lite.alerting.webhook")


class WebhookAlertChannel(AlertChannel):
    """httpx 기반 웹훅 알림 채널.

    사내 메신저(Teams, Slack 등)의 웹훅 URL로 JSON 페이로드를 POST한다.
    """

    def __init__(self, url: str, timeout: float = 10.0):
        self.url = url
        self.timeout = timeout

    def send(self, alert: AlertMessage) -> None:
        """웹훅 알림 발송.

        POST JSON 페이로드:
        {
            "pipeline_name": "...",
            "execution_date": "YYYY-MM-DD",
            "status": "failed",
            "error_message": "...",
            "timestamp": "ISO 8601"
        }
        """
        try:
            payload = {
                "pipeline_name": alert.pipeline_name,
                "execution_date": str(alert.execution_date),
                "status": alert.status,
                "error_message": alert.error_message,
                "timestamp": alert.timestamp.isoformat(),
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.url, json=payload)
                response.raise_for_status()

            logger.info(f"웹훅 알림 발송 완료: {alert.pipeline_name}")
        except Exception as e:
            logger.error(f"웹훅 알림 발송 실패: {e}")
