import pytest
import sqlite3
from datetime import date, datetime

from airflow_lite.storage.models import PipelineRun, StepRun


# ── Database ──────────────────────────────────────────────────────────────────

def test_initialize_creates_tables(db):
    conn = db.get_connection()
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    assert "pipeline_runs" in tables
    assert "step_runs" in tables


def test_wal_mode_enabled(db):
    conn = db.get_connection()
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"


def test_foreign_keys_enabled(db):
    conn = db.get_connection()
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.close()
    assert fk == 1


# ── PipelineRunRepository ─────────────────────────────────────────────────────

def _make_run(**kwargs) -> PipelineRun:
    defaults = dict(
        pipeline_name="etl_sales",
        execution_date=date(2024, 1, 15),
        status="pending",
        trigger_type="scheduled",
    )
    defaults.update(kwargs)
    return PipelineRun(**defaults)


def test_pipeline_run_create_and_find_by_id(pipeline_repo):
    run = _make_run()
    pipeline_repo.create(run)
    fetched = pipeline_repo.find_by_id(run.id)
    assert fetched is not None
    assert fetched.id == run.id
    assert fetched.pipeline_name == "etl_sales"
    assert fetched.execution_date == date(2024, 1, 15)
    assert fetched.status == "pending"


def test_pipeline_run_find_by_id_not_found(pipeline_repo):
    assert pipeline_repo.find_by_id("nonexistent-id") is None


def test_pipeline_run_update_status(pipeline_repo):
    run = _make_run()
    pipeline_repo.create(run)

    finished = datetime(2024, 1, 15, 3, 0, 0)
    pipeline_repo.update_status(run.id, "success", finished_at=finished)

    fetched = pipeline_repo.find_by_id(run.id)
    assert fetched.status == "success"
    assert fetched.finished_at == finished


def test_pipeline_run_find_by_pipeline(pipeline_repo):
    for d in [date(2024, 1, 10), date(2024, 1, 11), date(2024, 1, 12)]:
        pipeline_repo.create(_make_run(execution_date=d))

    results = pipeline_repo.find_by_pipeline("etl_sales")
    assert len(results) == 3
    assert all(r.pipeline_name == "etl_sales" for r in results)


def test_pipeline_run_find_by_pipeline_limit(pipeline_repo):
    for i in range(5):
        pipeline_repo.create(_make_run(execution_date=date(2024, 1, i + 1)))

    results = pipeline_repo.find_by_pipeline("etl_sales", limit=3)
    assert len(results) == 3


def test_pipeline_run_find_by_execution_date(pipeline_repo):
    run = _make_run(execution_date=date(2024, 2, 20))
    pipeline_repo.create(run)

    found = pipeline_repo.find_by_execution_date("etl_sales", date(2024, 2, 20))
    assert found is not None
    assert found.id == run.id

    not_found = pipeline_repo.find_by_execution_date("etl_sales", date(2024, 2, 21))
    assert not_found is None


def test_pipeline_run_unique_constraint(pipeline_repo):
    run1 = _make_run()
    run2 = _make_run()  # 같은 pipeline_name, execution_date, trigger_type
    pipeline_repo.create(run1)
    with pytest.raises(Exception):
        pipeline_repo.create(run2)


# ── StepRunRepository ─────────────────────────────────────────────────────────

def _make_step(pipeline_run_id: str, step_name: str = "extract") -> StepRun:
    return StepRun(
        pipeline_run_id=pipeline_run_id,
        step_name=step_name,
        status="pending",
    )


def test_step_run_create_and_find_by_pipeline_run(pipeline_repo, step_repo):
    run = _make_run()
    pipeline_repo.create(run)

    s1 = _make_step(run.id, "extract")
    s2 = _make_step(run.id, "transform")
    step_repo.create(s1)
    step_repo.create(s2)

    steps = step_repo.find_by_pipeline_run(run.id)
    assert len(steps) == 2
    names = {s.step_name for s in steps}
    assert names == {"extract", "transform"}


def test_step_run_update_status(pipeline_repo, step_repo):
    run = _make_run()
    pipeline_repo.create(run)
    step = _make_step(run.id)
    step_repo.create(step)

    finished = datetime(2024, 1, 15, 2, 30, 0)
    step_repo.update_status(
        step.id,
        "success",
        finished_at=finished,
        records_processed=5000,
    )

    steps = step_repo.find_by_pipeline_run(run.id)
    assert steps[0].status == "success"
    assert steps[0].records_processed == 5000
    assert steps[0].finished_at == finished


def test_step_run_update_status_with_error(pipeline_repo, step_repo):
    run = _make_run()
    pipeline_repo.create(run)
    step = _make_step(run.id)
    step_repo.create(step)

    step_repo.update_status(step.id, "failed", error_message="Connection timeout")

    steps = step_repo.find_by_pipeline_run(run.id)
    assert steps[0].status == "failed"
    assert steps[0].error_message == "Connection timeout"


def test_step_run_foreign_key_violation(step_repo):
    with pytest.raises(Exception):
        step_repo.create(_make_step("nonexistent-pipeline-run-id"))


def test_step_run_find_by_pipeline_run_empty(step_repo):
    assert step_repo.find_by_pipeline_run("no-such-id") == []
