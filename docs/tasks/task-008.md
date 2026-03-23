# Task-008: 알림 시스템

## 목적

파이프라인 실패/완료 시 이메일 및 웹훅으로 알림을 발송하는 시스템을 구현한다. AlertChannel ABC로 채널을 추상화하고, 이메일(smtplib)과 웹훅(httpx) 구현체를 제공한다.

## 입력

- Task-003의 `on_failure_callback` 훅 (RetryConfig)
- Settings (알림 설정 — SMTP 서버, 웹훅 URL, 수신자 목록)

## 출력

- `src/airflow_lite/alerting/base.py` — AlertChannel ABC + AlertMessage dataclass
- `src/airflow_lite/alerting/email.py` — EmailAlertChannel
- `src/airflow_lite/alerting/webhook.py` — WebhookAlertChannel

## 구현 제약

- 사내 SMTP 서버 사용 (인증 불필요할 수 있음 — 설정 기반)
- 사내 메신저 웹훅 URL 사용
- 알림 실패가 파이프라인 실행에 영향을 주지 않아야 함 (알림 자체의 예외를 적절히 처리)

## 구현 상세

### base.py — AlertChannel ABC + AlertMessage

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

class AlertChannel(ABC):
    @abstractmethod
    def send(self, alert: AlertMessage) -> None:
        """알림 발송. 실패 시 로깅만 하고 예외를 전파하지 않는다."""

@dataclass
class AlertMessage:
    pipeline_name: str
    execution_date: date
    status: str              # "failed" | "success"
    error_message: str | None
    timestamp: datetime
```

### email.py — EmailAlertChannel

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

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
```

### webhook.py — WebhookAlertChannel

```python
import httpx
import logging

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
```

### 알림 트리거 조건

| 조건 | 설명 | 기본값 |
|------|------|--------|
| `on_failure` | 재시도 소진 후 최종 실패 (`on_failure_callback` 경유) | true |
| `on_success` | 파이프라인 전체 완료 | false |

### YAML 설정 예시

```yaml
alerting:
  channels:
    - type: "email"
      smtp_host: "mail.internal.company.com"
      smtp_port: 25
      recipients: ["ops-team@company.com"]
    - type: "webhook"
      url: "https://messenger.internal/webhook/xxx"
  triggers:
    on_failure: true
    on_success: false
```

### 알림 매니저 (채널 통합 관리)

```python
class AlertManager:
    """복수의 AlertChannel을 관리하고, 트리거 조건에 따라 알림을 발송한다."""

    def __init__(self, channels: list[AlertChannel], triggers: dict):
        self.channels = channels
        self.triggers = triggers  # {"on_failure": True, "on_success": False}

    def notify(self, alert: AlertMessage) -> None:
        """트리거 조건 확인 후 모든 채널로 알림 발송."""
        if alert.status == "failed" and not self.triggers.get("on_failure"):
            return
        if alert.status == "success" and not self.triggers.get("on_success"):
            return

        for channel in self.channels:
            channel.send(alert)
```

## 완료 조건

- [ ] `AlertChannel` ABC 정의 (send 메서드)
- [ ] `AlertMessage` dataclass 정의
- [ ] `EmailAlertChannel.send()` 테스트 (smtplib 모킹)
  - 정상 발송 확인
  - SMTP 연결 실패 시 예외 미전파 + 로깅 확인
- [ ] `WebhookAlertChannel.send()` 테스트 (httpx 모킹)
  - 정상 발송 확인
  - HTTP 에러 시 예외 미전파 + 로깅 확인
- [ ] `AlertManager.notify()` 트리거 조건 필터링 테스트
  - on_failure=true + failed 알림 → 발송
  - on_success=false + success 알림 → 미발송
- [ ] 이메일 제목/본문 포맷 확인

## 참고 (선택)

- 알림 설계: `docs/system_design/architecture.md` 섹션 8
- 트리거 조건: RetryConfig의 `on_failure_callback` 경유
