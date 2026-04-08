import pytest
from datetime import date

from airflow_lite.engine.stage import (
    RetryConfig,
    RetryableOracleError,
    StageDefinition,
    StageResult,
    StageState,
)
from airflow_lite.engine.state_machine import InvalidTransitionError, StageStateMachine
from airflow_lite.engine.pipeline import PipelineDefinition, PipelineRunner
from airflow_lite.storage.models import PipelineRun, StepRun


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def state_machine(step_repo):
    return StageStateMachine(step_repo)


@pytest.fixture
def make_runner(pipeline_repo, step_repo, state_machine):
    """PipelineRunner 팩토리 픽스처."""
    def _factory(stages, pipeline_name="test_pipeline", on_run_success=None):
        pipeline = PipelineDefinition(
            name=pipeline_name,
            stages=stages,
            strategy=None,
            chunk_size=1000,
        )
        return PipelineRunner(
            pipeline=pipeline,
            run_repo=pipeline_repo,
            step_repo=step_repo,
            state_machine=state_machine,
            on_run_success=on_run_success,
        )
    return _factory


def _make_pipeline_run(name="test_pipeline", exec_date=date(2024, 1, 1)) -> PipelineRun:
    return PipelineRun(pipeline_name=name, execution_date=exec_date)


def _make_step_run(pipeline_run_id: str, status: str = "pending") -> StepRun:
    return StepRun(pipeline_run_id=pipeline_run_id, step_name="test_step", status=status)


def _make_stage(name: str, fn, max_attempts: int = 1) -> StageDefinition:
    """재시도 없는 빠른 StageDefinition 헬퍼."""
    return StageDefinition(
        name=name,
        callable=fn,
        retry_config=RetryConfig(
            max_attempts=max_attempts,
            min_wait_seconds=0,
            max_wait_seconds=0,
        ),
    )


# ── StageState enum ────────────────────────────────────────────────────────────

def test_stage_state_has_five_states():
    assert {s.value for s in StageState} == {
        "pending", "running", "success", "failed", "skipped"
    }


def test_stage_state_is_string_enum():
    """str, Enum 다중 상속으로 문자열 비교 가능."""
    assert StageState.PENDING == "pending"
    assert StageState.RUNNING == "running"
    assert StageState.SUCCESS == "success"
    assert StageState.FAILED == "failed"
    assert StageState.SKIPPED == "skipped"


# ── StageStateMachine 유효 전이 ────────────────────────────────────────────────

@pytest.mark.parametrize("from_state,to_state", [
    ("pending", "running"),
    ("pending", "skipped"),
    ("running", "success"),
    ("running", "failed"),
    ("failed",  "pending"),
])
def test_valid_transitions(pipeline_repo, step_repo, state_machine, from_state, to_state):
    run = _make_pipeline_run(exec_date=date(2024, 1, 1))
    pipeline_repo.create(run)
    step = _make_step_run(run.id, status=from_state)
    step_repo.create(step)

    state_machine.transition(step, StageState(to_state))

    assert step.status == to_state


# ── StageStateMachine 무효 전이 (InvalidTransitionError) ─────────────────────

@pytest.mark.parametrize("from_state,to_state", [
    ("pending",  "success"),
    ("pending",  "failed"),
    ("pending",  "pending"),
    ("running",  "pending"),
    ("running",  "running"),
    ("running",  "skipped"),
    ("success",  "running"),
    ("success",  "pending"),
    ("success",  "failed"),
    ("skipped",  "running"),
    ("skipped",  "pending"),
    ("failed",   "success"),
    ("failed",   "failed"),
    ("failed",   "skipped"),
])
def test_invalid_transitions_raise(pipeline_repo, step_repo, state_machine, from_state, to_state):
    run = _make_pipeline_run(exec_date=date(2024, 2, 1))
    pipeline_repo.create(run)
    step = _make_step_run(run.id, status=from_state)
    step_repo.create(step)

    with pytest.raises(InvalidTransitionError):
        state_machine.transition(step, StageState(to_state))


# ── SQLite 영속화 확인 ──────────────────────────────────────────────────────────

def test_transition_persists_to_sqlite(pipeline_repo, step_repo, state_machine):
    run = _make_pipeline_run(exec_date=date(2024, 3, 1))
    pipeline_repo.create(run)
    step = _make_step_run(run.id, status="pending")
    step_repo.create(step)

    state_machine.transition(step, StageState.RUNNING)

    persisted = step_repo.find_by_pipeline_run(run.id)[0]
    assert persisted.status == "running"


def test_each_transition_persists_immediately(pipeline_repo, step_repo, state_machine):
    run = _make_pipeline_run(exec_date=date(2024, 3, 2))
    pipeline_repo.create(run)
    step = _make_step_run(run.id, status="pending")
    step_repo.create(step)

    state_machine.transition(step, StageState.RUNNING)
    assert step_repo.find_by_pipeline_run(run.id)[0].status == "running"

    state_machine.transition(step, StageState.SUCCESS)
    assert step_repo.find_by_pipeline_run(run.id)[0].status == "success"


# ── PipelineRunner.run() 순차 실행 ────────────────────────────────────────────

def test_run_all_stages_success(make_runner, step_repo):
    execution_order = []

    def make_fn(name):
        def fn(ctx):
            execution_order.append(name)
            return StageResult(records_processed=10)
        return fn

    stages = [
        _make_stage("extract",   make_fn("extract")),
        _make_stage("transform", make_fn("transform")),
        _make_stage("load",      make_fn("load")),
    ]
    r = make_runner(stages)
    pipeline_run = r.run(date(2024, 4, 1))

    assert pipeline_run.status == "success"
    assert execution_order == ["extract", "transform", "load"]

    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    assert all(s.status == "success" for s in steps)
    assert all(s.started_at is not None for s in steps)
    assert {s.step_name for s in steps} == {"extract", "transform", "load"}


def test_run_records_processed_persisted(make_runner, step_repo):
    def fn(ctx):
        return StageResult(records_processed=500)

    stages = [_make_stage("extract", fn)]
    r = make_runner(stages)
    pipeline_run = r.run(date(2024, 4, 2))

    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    assert steps[0].records_processed == 500


def test_run_sets_step_started_at(make_runner, step_repo):
    stages = [_make_stage("extract", lambda ctx: StageResult(records_processed=1))]
    runner = make_runner(stages)
    pipeline_run = runner.run(date(2024, 4, 3))

    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    assert steps[0].started_at is not None


# ── 단계 실패 시 후속 단계 SKIPPED 처리 ────────────────────────────────────────

def test_stage_failure_skips_subsequent_stages(make_runner, step_repo):
    called = []

    def extract_fn(ctx):
        called.append("extract")
        return StageResult()

    def failing_fn(ctx):
        raise RetryableOracleError("ORA-03113")

    def load_fn(ctx):
        called.append("load")
        return StageResult()

    stages = [
        _make_stage("extract",   extract_fn),
        _make_stage("transform", failing_fn),
        _make_stage("load",      load_fn),
    ]
    r = make_runner(stages)
    pipeline_run = r.run(date(2024, 5, 1))

    assert pipeline_run.status == "failed"
    assert "load" not in called

    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    statuses = {s.step_name: s.status for s in steps}
    assert statuses["extract"]   == "success"
    assert statuses["transform"] == "failed"
    assert statuses["load"]      == "skipped"


def test_first_stage_failure_skips_all_subsequent(make_runner, step_repo):
    def failing_fn(ctx):
        raise RetryableOracleError("ORA-03113")

    def ok_fn(ctx):
        return StageResult()

    stages = [
        _make_stage("extract",   failing_fn),
        _make_stage("transform", ok_fn),
        _make_stage("load",      ok_fn),
    ]
    r = make_runner(stages)
    pipeline_run = r.run(date(2024, 5, 2))

    assert pipeline_run.status == "failed"
    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    statuses = {s.step_name: s.status for s in steps}
    assert statuses["extract"]   == "failed"
    assert statuses["transform"] == "skipped"
    assert statuses["load"]      == "skipped"


# ── Tenacity 재시도 동작 ───────────────────────────────────────────────────────

def test_retry_succeeds_after_transient_failure(make_runner, step_repo):
    attempts = []

    def flaky_fn(ctx):
        attempts.append(1)
        if len(attempts) < 2:
            raise RetryableOracleError("ORA-03113")
        return StageResult(records_processed=42)

    stages = [
        StageDefinition(
            name="extract",
            callable=flaky_fn,
            retry_config=RetryConfig(max_attempts=3, min_wait_seconds=0, max_wait_seconds=0),
        )
    ]
    r = make_runner(stages)
    pipeline_run = r.run(date(2024, 6, 1))

    assert pipeline_run.status == "success"
    assert len(attempts) == 2

    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    assert steps[0].status == "success"
    assert steps[0].records_processed == 42


def test_retry_exhausted_marks_stage_failed(make_runner, step_repo):
    attempts = []

    def always_fails(ctx):
        attempts.append(1)
        raise RetryableOracleError("ORA-03113")

    stages = [
        StageDefinition(
            name="extract",
            callable=always_fails,
            retry_config=RetryConfig(max_attempts=3, min_wait_seconds=0, max_wait_seconds=0),
        ),
        _make_stage("transform", lambda ctx: StageResult()),
    ]
    r = make_runner(stages)
    pipeline_run = r.run(date(2024, 6, 2))

    assert pipeline_run.status == "failed"
    assert len(attempts) == 3  # max_attempts=3 → 3번 시도

    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    statuses = {s.step_name: s.status for s in steps}
    assert statuses["extract"]   == "failed"
    assert statuses["transform"] == "skipped"
    assert next(s for s in steps if s.step_name == "extract").retry_count == 2


def test_non_retryable_exception_fails_immediately(make_runner, step_repo):
    attempts = []

    def raises_non_retryable(ctx):
        attempts.append(1)
        raise ValueError("data error")  # RETRYABLE_EXCEPTIONS에 미포함

    stages = [
        StageDefinition(
            name="extract",
            callable=raises_non_retryable,
            retry_config=RetryConfig(max_attempts=3, min_wait_seconds=0, max_wait_seconds=0),
        ),
    ]
    r = make_runner(stages)
    pipeline_run = r.run(date(2024, 6, 3))

    assert pipeline_run.status == "failed"
    assert len(attempts) == 1  # 재시도 없이 즉시 실패

    steps = step_repo.find_by_pipeline_run(pipeline_run.id)
    assert steps[0].retry_count == 0


# ── on_failure_callback 호출 ──────────────────────────────────────────────────

def test_on_failure_callback_called_on_stage_failure(make_runner):
    callback_calls = []

    def failing_fn(ctx):
        raise RetryableOracleError("connection lost")

    def callback(ctx, exc):
        callback_calls.append((ctx, exc))

    stages = [
        StageDefinition(
            name="extract",
            callable=failing_fn,
            retry_config=RetryConfig(
                max_attempts=1,
                min_wait_seconds=0,
                max_wait_seconds=0,
                on_failure_callback=callback,
            ),
        ),
    ]
    r = make_runner(stages)
    r.run(date(2024, 7, 1))

    assert len(callback_calls) == 1
    ctx, exc = callback_calls[0]
    assert ctx.pipeline_name == "test_pipeline"
    assert isinstance(exc, RetryableOracleError)


def test_on_failure_callback_not_called_on_success(make_runner):
    callback_calls = []

    def ok_fn(ctx):
        return StageResult()

    def callback(ctx, exc):
        callback_calls.append(1)

    stages = [
        StageDefinition(
            name="extract",
            callable=ok_fn,
            retry_config=RetryConfig(
                max_attempts=1,
                min_wait_seconds=0,
                max_wait_seconds=0,
                on_failure_callback=callback,
            ),
        ),
    ]
    r = make_runner(stages)
    r.run(date(2024, 7, 2))

    assert len(callback_calls) == 0


def test_on_failure_callback_receives_original_exception(make_runner):
    """RetryError에서 언래핑된 원본 예외가 콜백에 전달돼야 한다."""
    received_exceptions = []

    def always_fails(ctx):
        raise RetryableOracleError("ORA-03114")

    def callback(ctx, exc):
        received_exceptions.append(exc)

    stages = [
        StageDefinition(
            name="extract",
            callable=always_fails,
            retry_config=RetryConfig(
                max_attempts=2,
                min_wait_seconds=0,
                max_wait_seconds=0,
                on_failure_callback=callback,
            ),
        ),
    ]
    r = make_runner(stages)
    r.run(date(2024, 7, 3))

    assert len(received_exceptions) == 1
    assert isinstance(received_exceptions[0], RetryableOracleError)


def test_on_run_success_callback_called_on_pipeline_success(make_runner):
    callback_calls = []

    def ok_fn(ctx):
        return StageResult(records_processed=1)

    def success_callback(ctx):
        callback_calls.append(ctx)

    runner = make_runner(
        [_make_stage("extract", ok_fn)],
        on_run_success=success_callback,
    )
    runner.run(date(2024, 7, 4))

    assert len(callback_calls) == 1
    assert callback_calls[0].pipeline_name == "test_pipeline"


def test_run_passes_trigger_type_into_stage_context_and_success_callback(make_runner):
    observed_trigger_types = []

    def ok_fn(ctx):
        observed_trigger_types.append(("stage", ctx.trigger_type))
        return StageResult(records_processed=1)

    def success_callback(ctx):
        observed_trigger_types.append(("success", ctx.trigger_type))

    runner = make_runner(
        [_make_stage("extract", ok_fn)],
        on_run_success=success_callback,
    )
    pipeline_run = runner.run(date(2024, 7, 5), trigger_type="backfill")

    assert pipeline_run.trigger_type == "backfill"
    assert observed_trigger_types == [
        ("stage", "backfill"),
        ("success", "backfill"),
    ]


# ── 멱등성 (idempotency) ──────────────────────────────────────────────────────

def test_run_idempotent_returns_existing_success(make_runner):
    calls = []

    def fn(ctx):
        calls.append(1)
        return StageResult(records_processed=1)

    stages = [_make_stage("extract", fn)]
    r = make_runner(stages)

    run1 = r.run(date(2024, 8, 1))
    assert run1.status == "success"
    assert len(calls) == 1

    # 동일 execution_date 재실행 → 기존 성공 실행 반환, fn 재호출 없음
    run2 = r.run(date(2024, 8, 1))
    assert run2.id == run1.id
    assert len(calls) == 1  # fn이 다시 호출되지 않음


def test_run_force_rerun_creates_new_success(make_runner):
    calls = []

    def fn(ctx):
        calls.append(1)
        return StageResult(records_processed=1)

    runner = make_runner([_make_stage("extract", fn)])

    run1 = runner.run(date(2024, 8, 2))
    run2 = runner.run(date(2024, 8, 2), force_rerun=True)

    assert run1.id != run2.id
    assert len(calls) == 2
