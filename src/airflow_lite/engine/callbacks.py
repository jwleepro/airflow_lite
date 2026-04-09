"""파이프라인 실행 콜백 — 알림 및 mart refresh 후처리.

runtime.py의 SRP 위반을 해소하기 위해 콜백 로직을 분리한 모듈.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from airflow_lite.alerting.base import AlertMessage

if TYPE_CHECKING:
    from airflow_lite.alerting.manager import AlertManager
    from airflow_lite.mart.factory import MartInfrastructure

logger = logging.getLogger("airflow_lite.engine.callbacks")


class PipelineCallbacks:
    """파이프라인 실행 결과에 따른 알림과 mart refresh를 처리한다."""

    def __init__(
        self,
        alert_manager: "AlertManager",
        mart_infra: "MartInfrastructure | None" = None,
    ):
        self._alert_manager = alert_manager
        self._mart_infra = mart_infra

    def notify(self, status: str, context, exc: Exception | None = None) -> None:
        self._alert_manager.notify(
            AlertMessage(
                pipeline_name=context.pipeline_name,
                execution_date=context.execution_date,
                status=status,
                error_message=str(exc) if exc else None,
                timestamp=datetime.now(),
            )
        )

    def on_failure(self, context, exc: Exception) -> None:
        self.notify("failed", context, exc)

    def on_success(self, context) -> None:
        self.notify("success", context)
        self._run_mart_refresh(context)

    def _run_mart_refresh(self, context) -> None:
        if self._mart_infra is None:
            return

        try:
            plan = self._mart_infra.coordinator.plan_refresh(context)
        except Exception as plan_exc:
            logger.exception(
                "Mart refresh planning failed: %s / %s",
                context.pipeline_name,
                context.execution_date,
            )
            self.notify("failed", context, plan_exc)
            return

        if plan is None:
            return

        try:
            result = self._mart_infra.executor.execute_refresh(plan)
        except Exception as mart_exc:
            logger.exception(
                "Mart refresh execution failed: %s / %s",
                context.pipeline_name,
                context.execution_date,
            )
            self.notify("failed", context, mart_exc)
            return

        if not result.validation_report.is_valid:
            issues = [issue.message for issue in result.validation_report.issues]
            logger.error(
                "Mart refresh validation failed: dataset=%s issues=%s",
                result.plan.request.dataset_name,
                issues,
            )
            self.notify("failed", context, RuntimeError(f"mart validation failed: {issues}"))
            return

        logger.info(
            "Mart refresh completed: dataset=%s mode=%s promoted=%s staging=%s current=%s snapshot=%s rows=%s files=%s",
            result.plan.request.dataset_name,
            result.plan.request.mode.value,
            result.promoted,
            result.plan.build_plan.paths.staging_db_path,
            result.plan.build_plan.paths.current_db_path,
            result.plan.build_plan.paths.snapshot_db_path,
            result.build_result.row_count,
            result.build_result.file_count,
        )
