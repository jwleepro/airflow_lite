"""PipelineDispatchService — 웹/API/스케줄러 공용 실행 디스패처.

역할:
- 수동/스케줄 트리거 요청을 받아 DB에 queued 레코드를 먼저 남긴다.
- 실제 실행은 PipelineLocalExecutor 스레드에 위임하여 호출자를 블로킹하지 않는다.
- 백필 요청 자체도 디스패처에 태워, 월별 child run 생성·실행이 요청 스레드에서 벌어지지 않게 한다.

Airflow 3.x 의 UI/API 서버가 DagRun 을 INSERT 만 하고 scheduler+executor 가 실행을 소비하는
구조를 단일 프로세스 수준으로 흉내낸 것이다.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable, TYPE_CHECKING

from airflow_lite.api._resolver import resolve_backfill_manager, resolve_factory
from airflow_lite.service.concurrency_manager import ConcurrencyManager
from airflow_lite.storage.models import PipelineRun

if TYPE_CHECKING:
    from airflow_lite.executor.pipeline_local_executor import PipelineLocalExecutor
    from airflow_lite.storage.repository import PipelineRunRepository

logger = logging.getLogger("airflow_lite.service.dispatch")


class PipelineBusyError(RuntimeError):
    """동일 pipeline 에 이미 active run/backfill 이 있어 신규 요청을 거부할 때 사용."""

    def __init__(self, pipeline_name: str, active_run: PipelineRun | None = None):
        self.pipeline_name = pipeline_name
        self.run_id = active_run.id if active_run else None
        self.status = active_run.status if active_run else None
        self.execution_date = active_run.execution_date if active_run else None

        if active_run is None:
            message = (
                f"Pipeline '{pipeline_name}' is already active. "
                "Finish the current run before retrying."
            )
        else:
            message = (
                f"Pipeline '{pipeline_name}' is already active "
                f"(run_id={active_run.id}, status={active_run.status})."
            )
        super().__init__(message)

    def to_detail(self) -> dict[str, str]:
        detail = {
            "message": str(self),
            "pipeline_name": self.pipeline_name,
        }
        if self.run_id is not None:
            detail["run_id"] = self.run_id
        if self.status is not None:
            detail["status"] = self.status
        if self.execution_date is not None:
            detail["execution_date"] = self.execution_date.isoformat()
        return detail


class PipelineDispatchService:
    def __init__(
        self,
        runner_map: dict[str, Callable],
        backfill_map: dict[str, Callable],
        executor: "PipelineLocalExecutor",
        run_repo: "PipelineRunRepository",
    ):
        self._runner_map = runner_map
        self._backfill_map = backfill_map
        self._executor = executor
        self._concurrency = ConcurrencyManager(run_repo)

    def has_pipeline(self, pipeline_name: str) -> bool:
        return pipeline_name in self._runner_map

    def has_backfill(self, pipeline_name: str) -> bool:
        return pipeline_name in self._backfill_map

    def get_active_pipelines(self) -> tuple[str, ...]:
        return self._concurrency.get_active_pipelines()

    def _raise_if_pipeline_busy(self, pipeline_name: str) -> None:
        active_run = self._concurrency.run_repo.find_any_active_by_pipeline(pipeline_name)
        if active_run is not None:
            raise PipelineBusyError(pipeline_name, active_run)
        if pipeline_name in self._concurrency.get_active_pipelines():
            raise PipelineBusyError(pipeline_name)

    def submit_manual_run(
        self,
        pipeline_name: str,
        execution_date: date,
        force_rerun: bool = False,
        trigger_type: str = "manual",
    ) -> PipelineRun:
        """run row 를 즉시 생성하고, queued 면 실행을 워커에 submit.

        반환 시점에 이미 DB 에 row 가 있으므로 호출자는 run.id 로 상세 페이지를 열 수 있다.
        """
        if pipeline_name not in self._runner_map:
            raise KeyError(f"파이프라인 '{pipeline_name}' 이 runner_map 에 없습니다.")

        if not force_rerun:
            existing_success = self._concurrency.run_repo.find_latest_success_by_execution_date(
                pipeline_name,
                execution_date,
            )
            if existing_success is not None:
                return existing_success

            existing_active = self._concurrency.run_repo.find_active_by_execution_date(
                pipeline_name,
                execution_date,
            )
            if existing_active is not None:
                return existing_active

        self._raise_if_pipeline_busy(pipeline_name)
        self._concurrency.reserve(pipeline_name)
        runner = _resolve_runner_for_dispatch(self._runner_map[pipeline_name])
        try:
            pipeline_run = runner.prepare_run(
                execution_date=execution_date,
                trigger_type=trigger_type,
                force_rerun=force_rerun,
            )
            if pipeline_run.status == "queued":
                if self._concurrency.claim_in_flight(str(pipeline_run.id)):
                    try:
                        self._executor.submit(self._safe_execute, runner, pipeline_run)
                    except Exception:
                        self._concurrency.release_in_flight(str(pipeline_run.id))
                        raise
            return pipeline_run
        except Exception:
            self._concurrency.release(pipeline_name)
            raise

    def submit_backfill(
        self,
        pipeline_name: str,
        start_date: date,
        end_date: date,
        force_rerun: bool = False,
    ) -> None:
        """백필 요청 자체를 워커에 태운다.

        월별 child run 의 생성과 실행은 모두 워커 스레드에서 이루어진다.
        호출자는 즉시 반환.
        """
        if pipeline_name not in self._backfill_map:
            raise KeyError(f"파이프라인 '{pipeline_name}' 이 backfill_map 에 없습니다.")
        if end_date < start_date:
            raise ValueError("end_date는 start_date보다 같거나 이후여야 합니다.")

        self._raise_if_pipeline_busy(pipeline_name)
        self._concurrency.reserve(pipeline_name)
        manager = resolve_backfill_manager(self._backfill_map[pipeline_name])
        try:
            self._executor.submit(
                self._safe_backfill,
                manager,
                pipeline_name,
                start_date,
                end_date,
                force_rerun,
            )
        except Exception:
            self._concurrency.release(pipeline_name)
            raise

    def _safe_execute(self, runner, pipeline_run: PipelineRun) -> None:
        pipeline_name = pipeline_run.pipeline_name
        lock = self._concurrency.acquire_lock(pipeline_name)
        with lock:
            try:
                runner.execute_prepared_run(pipeline_run)
            except Exception:
                logger.exception(
                    "dispatch execute 실패: pipeline=%s run_id=%s",
                    pipeline_name,
                    pipeline_run.id,
                )
                try:
                    self._concurrency.run_repo.update_status(
                        pipeline_run.id, "failed", finished_at=datetime.now()
                    )
                except Exception:
                    logger.exception("failed 상태 보정도 실패: run_id=%s", pipeline_run.id)
            finally:
                self._concurrency.release_in_flight(str(pipeline_run.id))
                self._concurrency.release(pipeline_name)

    def _safe_backfill(
        self,
        manager,
        pipeline_name: str,
        start_date: date,
        end_date: date,
        force_rerun: bool,
    ) -> None:
        lock = self._concurrency.acquire_lock(pipeline_name)
        with lock:
            try:
                manager.run_backfill(
                    pipeline_name=pipeline_name,
                    start_date=start_date,
                    end_date=end_date,
                    force_rerun=force_rerun,
                )
            except Exception:
                logger.exception(
                    "dispatch backfill 실패: pipeline=%s %s~%s",
                    pipeline_name,
                    start_date,
                    end_date,
                )
            finally:
                self._concurrency.release(pipeline_name)


def _resolve_runner_for_dispatch(entry):
    """prepare_run 노출 기준으로 runner 인스턴스를 얻는다."""
    return resolve_factory(entry, "prepare_run", "runner_map")
