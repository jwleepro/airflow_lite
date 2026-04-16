"""PipelineDispatchService / PipelineLocalExecutor 단위 테스트."""

from __future__ import annotations

import threading
import time
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from airflow_lite.executor.pipeline_local_executor import PipelineLocalExecutor
from airflow_lite.service.dispatch_service import PipelineBusyError, PipelineDispatchService
from airflow_lite.storage.models import PipelineRun


class _FakeRunner:
    """prepare_run/execute_prepared_run 동작을 모방한다."""

    def __init__(
        self,
        run_repo,
        *,
        pipeline_name: str = "demo",
        fail: bool = False,
        block: threading.Event | None = None,
    ):
        self._run_repo = run_repo
        self.pipeline_name = pipeline_name
        self.fail = fail
        self.block = block
        self.executions: list[str] = []

    def prepare_run(self, execution_date, trigger_type, force_rerun):  # noqa: D401
        existing_success = self._run_repo.find_latest_success_by_execution_date(
            self.pipeline_name, execution_date
        )
        if not force_rerun and existing_success:
            return existing_success
        existing_active = self._run_repo.find_active_by_execution_date(
            self.pipeline_name, execution_date
        )
        if not force_rerun and existing_active:
            return existing_active
        run = PipelineRun(
            pipeline_name=self.pipeline_name,
            execution_date=execution_date,
            status="queued",
            started_at=None,
            trigger_type=trigger_type,
        )
        self._run_repo.create(run)
        return run

    def execute_prepared_run(self, pipeline_run: PipelineRun) -> PipelineRun:
        if self.block is not None:
            self.block.wait(timeout=5)
        self._run_repo.mark_running(pipeline_run.id, started_at=datetime.now())
        pipeline_run.status = "running"
        if self.fail:
            self._run_repo.update_status(pipeline_run.id, "failed", finished_at=datetime.now())
            pipeline_run.status = "failed"
            self.executions.append(pipeline_run.id)
            raise RuntimeError("stage failed (test)")
        self._run_repo.update_status(pipeline_run.id, "success", finished_at=datetime.now())
        pipeline_run.status = "success"
        self.executions.append(pipeline_run.id)
        return pipeline_run


class _BlockingRunner:
    def __init__(self):
        self.entered: list[str] = []
        self.first_started = threading.Event()
        self.second_started = threading.Event()
        self.release_first = threading.Event()
        self._guard = threading.Lock()

    def execute_prepared_run(self, pipeline_run: PipelineRun) -> PipelineRun:
        with self._guard:
            self.entered.append(pipeline_run.id)
            index = len(self.entered)
        if index == 1:
            self.first_started.set()
            self.release_first.wait(timeout=5)
        else:
            self.second_started.set()
        return pipeline_run


@pytest.fixture
def executor():
    ex = PipelineLocalExecutor(max_workers=2)
    yield ex
    ex.shutdown(wait=True)


def _make_dispatcher(executor, runner, pipeline_repo, backfill_map=None):
    runner_map = {runner.pipeline_name: runner}
    return PipelineDispatchService(
        runner_map=runner_map,
        backfill_map=backfill_map or {},
        executor=executor,
        run_repo=pipeline_repo,
    )


def _make_running_run(
    pipeline_repo,
    *,
    pipeline_name: str = "demo",
    run_id: str = "run-active",
    execution_date: date = date(2026, 4, 16),
):
    run = PipelineRun(
        id=run_id,
        pipeline_name=pipeline_name,
        execution_date=execution_date,
        status="queued",
        started_at=None,
        trigger_type="manual",
    )
    pipeline_repo.create(run)
    pipeline_repo.mark_running(run.id, started_at=datetime.now())
    return pipeline_repo.find_by_id(run.id)


def test_submit_manual_run_returns_queued_immediately(executor, pipeline_repo):
    gate = threading.Event()
    runner = _FakeRunner(pipeline_repo, block=gate)
    dispatcher = _make_dispatcher(executor, runner, pipeline_repo)

    run = dispatcher.submit_manual_run("demo", date(2026, 4, 16))

    assert run.status == "queued"
    assert run.started_at is None
    persisted = pipeline_repo.find_by_id(run.id)
    assert persisted.status == "queued"
    assert persisted.started_at is None

    gate.set()
    executor.shutdown(wait=True)

    final = pipeline_repo.find_by_id(run.id)
    assert final.status == "success"
    assert final.started_at is not None
    assert runner.executions == [run.id]


def test_submit_manual_run_failure_marks_failed(executor, pipeline_repo):
    runner = _FakeRunner(pipeline_repo, fail=True)
    dispatcher = _make_dispatcher(executor, runner, pipeline_repo)

    run = dispatcher.submit_manual_run("demo", date(2026, 4, 16))
    executor.shutdown(wait=True)

    final = pipeline_repo.find_by_id(run.id)
    assert final.status == "failed"


def test_duplicate_active_trigger_returns_existing_run(executor, pipeline_repo):
    gate = threading.Event()
    runner = _FakeRunner(pipeline_repo, block=gate)
    dispatcher = _make_dispatcher(executor, runner, pipeline_repo)

    first = dispatcher.submit_manual_run("demo", date(2026, 4, 16))
    second = dispatcher.submit_manual_run("demo", date(2026, 4, 16))

    assert first.id == second.id
    gate.set()
    executor.shutdown(wait=True)

    assert runner.executions == [first.id]


def test_force_rerun_rejected_when_pipeline_active(pipeline_repo):
    executor = MagicMock()
    runner = _FakeRunner(pipeline_repo)
    dispatcher = _make_dispatcher(executor, runner, pipeline_repo)
    active_run = _make_running_run(pipeline_repo)

    with pytest.raises(PipelineBusyError) as exc_info:
        dispatcher.submit_manual_run("demo", date(2026, 4, 17), force_rerun=True)

    exc = exc_info.value
    assert exc.run_id == active_run.id
    assert exc.status == "running"
    executor.submit.assert_not_called()


def test_force_rerun_allowed_when_no_active_run(pipeline_repo):
    executor = MagicMock()
    runner = _FakeRunner(pipeline_repo)
    dispatcher = _make_dispatcher(executor, runner, pipeline_repo)

    run = dispatcher.submit_manual_run("demo", date(2026, 4, 16), force_rerun=True)

    assert run.status == "queued"
    executor.submit.assert_called_once()


def test_backfill_rejected_when_pipeline_active(pipeline_repo):
    executor = MagicMock()
    runner = _FakeRunner(pipeline_repo)
    manager = MagicMock()
    dispatcher = PipelineDispatchService(
        runner_map={runner.pipeline_name: runner},
        backfill_map={runner.pipeline_name: manager},
        executor=executor,
        run_repo=pipeline_repo,
    )
    active_run = _make_running_run(pipeline_repo)

    with pytest.raises(PipelineBusyError) as exc_info:
        dispatcher.submit_backfill(
            "demo",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            force_rerun=True,
        )

    exc = exc_info.value
    assert exc.run_id == active_run.id
    executor.submit.assert_not_called()


def test_pipeline_lock_serializes_concurrent_executions(executor, pipeline_repo):
    runner = _BlockingRunner()
    fake_runner = _FakeRunner(pipeline_repo)
    dispatcher = _make_dispatcher(executor, fake_runner, pipeline_repo)
    first = PipelineRun(
        id="run-1",
        pipeline_name="demo",
        execution_date=date(2026, 4, 16),
        status="queued",
        trigger_type="manual",
    )
    second = PipelineRun(
        id="run-2",
        pipeline_name="demo",
        execution_date=date(2026, 4, 17),
        status="queued",
        trigger_type="manual",
    )

    future_one = executor.submit(dispatcher._safe_execute, runner, first)
    assert runner.first_started.wait(timeout=2)

    future_two = executor.submit(dispatcher._safe_execute, runner, second)
    time.sleep(0.2)
    assert runner.second_started.is_set() is False

    runner.release_first.set()
    future_one.result(timeout=2)
    future_two.result(timeout=2)

    assert runner.entered == ["run-1", "run-2"]


def test_unknown_pipeline_raises(executor, pipeline_repo):
    runner = _FakeRunner(pipeline_repo)
    dispatcher = _make_dispatcher(executor, runner, pipeline_repo)

    with pytest.raises(KeyError):
        dispatcher.submit_manual_run("not-found", date(2026, 4, 16))


def test_local_executor_rejects_invalid_max_workers():
    with pytest.raises(ValueError):
        PipelineLocalExecutor(max_workers=0)
