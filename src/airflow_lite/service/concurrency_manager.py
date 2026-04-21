"""Pipeline 컨커런시 제어 및 in-flight 추적 전담 모듈.

PipelineDispatchService 에서 컨커런시 락, active pipeline 추적,
in-flight run 추적을 분리한다.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airflow_lite.storage.repository import PipelineRunRepository


class ConcurrencyManager:
    """스레드 안전한 pipeline 컨커런시 제어 및 in-flight 추적."""

    def __init__(self, run_repo: "PipelineRunRepository"):
        self._run_repo = run_repo
        self._pipeline_locks: dict[str, threading.Lock] = {}
        self._pipeline_locks_guard = threading.Lock()
        self._active_pipelines: set[str] = set()
        self._in_flight: set[str] = set()
        self._in_flight_lock = threading.Lock()

    @property
    def run_repo(self) -> "PipelineRunRepository":
        return self._run_repo

    def reserve(self, pipeline_name: str) -> None:
        """pipeline 락 획득 + DB에서 활성 run 확인. 이미 active 면 RuntimeError 발생."""
        with self._pipeline_locks_guard:
            if pipeline_name in self._active_pipelines:
                raise RuntimeError(
                    f"Pipeline '{pipeline_name}' is already active."
                )
            self._active_pipelines.add(pipeline_name)
            lock = threading.Lock()
            self._pipeline_locks[pipeline_name] = lock

        active_run = self._run_repo.find_any_active_by_pipeline(pipeline_name)
        if active_run is not None:
            with self._pipeline_locks_guard:
                self._active_pipelines.discard(pipeline_name)
            raise RuntimeError(
                f"Pipeline '{pipeline_name}' is already active "
                f"(run_id={active_run.id}, status={active_run.status})."
            )

    def acquire_lock(self, pipeline_name: str) -> threading.Lock:
        """pipeline별 락 객체를 반환 (이미 존재하면 재사용)."""
        with self._pipeline_locks_guard:
            return self._pipeline_locks.get(pipeline_name)

    def release(self, pipeline_name: str) -> None:
        """pipeline 락 해제 및 active 목록에서 제거."""
        with self._pipeline_locks_guard:
            self._active_pipelines.discard(pipeline_name)

    def claim_in_flight(self, run_id: str) -> bool:
        """in-flight 에 run_id 등록. 이미 있으면 False."""
        with self._in_flight_lock:
            if run_id in self._in_flight:
                return False
            self._in_flight.add(run_id)
            return True

    def release_in_flight(self, run_id: str) -> None:
        """in-flight 에서 run_id 제거."""
        with self._in_flight_lock:
            self._in_flight.discard(run_id)

    def get_active_pipelines(self) -> tuple[str, ...]:
        with self._pipeline_locks_guard:
            return tuple(sorted(self._active_pipelines))
