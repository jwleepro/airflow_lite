from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class AlertMessage:
    pipeline_name: str
    execution_date: date
    status: str              # "failed" | "success"
    error_message: str | None
    timestamp: datetime


class AlertChannel(ABC):
    @abstractmethod
    def send(self, alert: AlertMessage) -> None:
        """알림 발송. 실패 시 로깅만 하고 예외를 전파하지 않는다."""


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
