from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from airflow_lite.alerting.base import AlertManager, AlertMessage
from airflow_lite.alerting.email import EmailAlertChannel
from airflow_lite.alerting.webhook import WebhookAlertChannel


@pytest.fixture
def failed_alert():
    return AlertMessage(
        pipeline_name="test_pipeline",
        execution_date=date(2026, 3, 17),
        status="failed",
        error_message="Something went wrong",
        timestamp=datetime(2026, 3, 17, 12, 0, 0),
    )


@pytest.fixture
def success_alert():
    return AlertMessage(
        pipeline_name="test_pipeline",
        execution_date=date(2026, 3, 17),
        status="success",
        error_message=None,
        timestamp=datetime(2026, 3, 17, 12, 0, 0),
    )


# --- EmailAlertChannel 테스트 ---

class TestEmailAlertChannel:
    def test_send_success(self, failed_alert):
        """정상 발송 확인."""
        channel = EmailAlertChannel(
            smtp_host="mail.internal",
            smtp_port=25,
            sender="airflow-lite@company.com",
            recipients=["ops@company.com"],
        )
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            channel.send(failed_alert)

            mock_smtp.assert_called_once_with("mail.internal", 25)
            mock_server.send_message.assert_called_once()

    def test_send_smtp_failure_no_exception(self, failed_alert, caplog):
        """SMTP 연결 실패 시 예외 미전파 + 로깅 확인."""
        channel = EmailAlertChannel(smtp_host="bad-host", recipients=["ops@company.com"])
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("연결 거부")):
            import logging
            with caplog.at_level(logging.ERROR, logger="airflow_lite.alerting.email"):
                channel.send(failed_alert)  # 예외가 전파되지 않아야 함

        assert any("이메일 알림 발송 실패" in r.message for r in caplog.records)

    def test_email_subject_format(self, failed_alert):
        """이메일 제목 포맷 확인."""
        channel = EmailAlertChannel(smtp_host="mail.internal", recipients=["ops@company.com"])
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            channel.send(failed_alert)

            sent_msg = mock_server.send_message.call_args[0][0]
            assert sent_msg["Subject"] == "[Airflow Lite] FAILED - test_pipeline"

    def test_email_body_contains_error(self, failed_alert):
        """에러 메시지가 본문에 포함되는지 확인."""
        channel = EmailAlertChannel(smtp_host="mail.internal", recipients=["ops@company.com"])
        body = channel._format_body(failed_alert)

        assert "test_pipeline" in body
        assert "2026-03-17" in body
        assert "failed" in body
        assert "Something went wrong" in body

    def test_email_body_no_error_when_success(self, success_alert):
        """에러 없는 경우 에러 줄 미포함 확인."""
        channel = EmailAlertChannel(smtp_host="mail.internal", recipients=["ops@company.com"])
        body = channel._format_body(success_alert)

        assert "에러:" not in body


# --- WebhookAlertChannel 테스트 ---

class TestWebhookAlertChannel:
    def test_send_success(self, failed_alert):
        """정상 발송 확인."""
        channel = WebhookAlertChannel(url="https://messenger.internal/webhook/xxx")
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_response = MagicMock()
            mock_client.post.return_value = mock_response

            channel.send(failed_alert)

            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[0][0] == "https://messenger.internal/webhook/xxx"
            payload = call_kwargs[1]["json"]
            assert payload["pipeline_name"] == "test_pipeline"
            assert payload["status"] == "failed"
            assert payload["error_message"] == "Something went wrong"
            assert payload["execution_date"] == "2026-03-17"

    def test_send_http_error_no_exception(self, failed_alert, caplog):
        """HTTP 에러 시 예외 미전파 + 로깅 확인."""
        import httpx
        channel = WebhookAlertChannel(url="https://messenger.internal/webhook/xxx")
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=MagicMock(),
                response=MagicMock(),
            )
            mock_client.post.return_value = mock_response

            import logging
            with caplog.at_level(logging.ERROR, logger="airflow_lite.alerting.webhook"):
                channel.send(failed_alert)  # 예외가 전파되지 않아야 함

        assert any("웹훅 알림 발송 실패" in r.message for r in caplog.records)

    def test_payload_timestamp_iso_format(self, failed_alert):
        """timestamp가 ISO 8601 형식인지 확인."""
        channel = WebhookAlertChannel(url="https://messenger.internal/webhook/xxx")
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = MagicMock()

            channel.send(failed_alert)

            payload = mock_client.post.call_args[1]["json"]
            assert payload["timestamp"] == "2026-03-17T12:00:00"


# --- AlertManager 테스트 ---

class TestAlertManager:
    def test_on_failure_true_sends_alert(self, failed_alert):
        """on_failure=true + failed 알림 → 발송."""
        mock_channel = MagicMock()
        manager = AlertManager(
            channels=[mock_channel],
            triggers={"on_failure": True, "on_success": False},
        )
        manager.notify(failed_alert)
        mock_channel.send.assert_called_once_with(failed_alert)

    def test_on_failure_false_suppresses_alert(self, failed_alert):
        """on_failure=false + failed 알림 → 미발송."""
        mock_channel = MagicMock()
        manager = AlertManager(
            channels=[mock_channel],
            triggers={"on_failure": False, "on_success": False},
        )
        manager.notify(failed_alert)
        mock_channel.send.assert_not_called()

    def test_on_success_false_suppresses_alert(self, success_alert):
        """on_success=false + success 알림 → 미발송."""
        mock_channel = MagicMock()
        manager = AlertManager(
            channels=[mock_channel],
            triggers={"on_failure": True, "on_success": False},
        )
        manager.notify(success_alert)
        mock_channel.send.assert_not_called()

    def test_on_success_true_sends_alert(self, success_alert):
        """on_success=true + success 알림 → 발송."""
        mock_channel = MagicMock()
        manager = AlertManager(
            channels=[mock_channel],
            triggers={"on_failure": True, "on_success": True},
        )
        manager.notify(success_alert)
        mock_channel.send.assert_called_once_with(success_alert)

    def test_multiple_channels_all_notified(self, failed_alert):
        """복수 채널 모두 알림 발송."""
        ch1 = MagicMock()
        ch2 = MagicMock()
        manager = AlertManager(
            channels=[ch1, ch2],
            triggers={"on_failure": True},
        )
        manager.notify(failed_alert)
        ch1.send.assert_called_once_with(failed_alert)
        ch2.send.assert_called_once_with(failed_alert)
