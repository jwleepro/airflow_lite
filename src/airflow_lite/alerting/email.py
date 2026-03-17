import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from airflow_lite.alerting.base import AlertChannel, AlertMessage

logger = logging.getLogger("airflow_lite.alerting.email")


class EmailAlertChannel(AlertChannel):
    """smtplib 기반 이메일 알림 채널.

    사내 SMTP 서버를 통해 알림 이메일을 발송한다.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 25,
        sender: str = "airflow-lite@company.com",
        recipients: list[str] = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients or []

    def send(self, alert: AlertMessage) -> None:
        """이메일 알림 발송.

        제목: [Airflow Lite] {status} - {pipeline_name}
        본문: 파이프라인명, 실행일, 상태, 에러 메시지 포함
        """
        try:
            subject = f"[Airflow Lite] {alert.status.upper()} - {alert.pipeline_name}"
            body = self._format_body(alert)

            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = ", ".join(self.recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.send_message(msg)

            logger.info(f"이메일 알림 발송 완료: {alert.pipeline_name}")
        except Exception as e:
            logger.error(f"이메일 알림 발송 실패: {e}")

    def _format_body(self, alert: AlertMessage) -> str:
        lines = [
            f"파이프라인: {alert.pipeline_name}",
            f"실행일: {alert.execution_date}",
            f"상태: {alert.status}",
            f"시간: {alert.timestamp}",
        ]
        if alert.error_message:
            lines.append(f"에러: {alert.error_message}")
        return "\n".join(lines)
