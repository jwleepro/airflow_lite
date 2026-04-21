import pytest
import sqlite3
from datetime import date, datetime
from unittest.mock import patch

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


def test_initialize_rolls_back_invalid_schema_script(tmp_path):
    from airflow_lite.storage.database import Database

    db_path = tmp_path / "broken.db"
    database = Database(str(db_path))
    broken_schema = """
    CREATE TABLE broken_table (
        id INTEGER PRIMARY KEY
    );
    CREATE TABLE broken_table (
        id INTEGER PRIMARY KEY
    );
    """

    with patch("pathlib.Path.read_text", return_value=broken_schema):
        with pytest.raises(sqlite3.OperationalError):
            database.initialize()

    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='broken_table'"
        ).fetchall()
    finally:
        conn.close()

    assert tables == []


def test_execute_script_atomically_rolls_back_partial_statement_sequence(tmp_path):
    from airflow_lite.storage.database import Database

    db_path = tmp_path / "partial.db"
    database = Database(str(db_path))
    conn = database.get_connection()
    try:
        with pytest.raises(sqlite3.OperationalError):
            database._execute_script_atomically(
                conn,
                """
                CREATE TABLE safe_table (
                    id INTEGER PRIMARY KEY
                );
                INSERT INTO safe_table (id) VALUES (1);
                INSERT INTO missing_table (id) VALUES (1);
                """,
            )
    finally:
        conn.close()

    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='safe_table'"
        ).fetchall()
        rows = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='safe_table'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert tables == []
    assert rows == 0


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
    run2 = _make_run(status="failed")  # 같은 pipeline_name, execution_date, trigger_type
    pipeline_repo.create(run1)
    pipeline_repo.create(run2)

    results = pipeline_repo.find_by_pipeline("etl_sales")
    assert len(results) == 2


def test_pipeline_run_success_duplicates_allowed(pipeline_repo):
    run1 = _make_run(status="success")
    run2 = _make_run(status="success")
    pipeline_repo.create(run1)
    pipeline_repo.create(run2)

    results = pipeline_repo.find_by_pipeline("etl_sales")
    assert len(results) == 2


def test_pipeline_run_find_latest_success_by_execution_date(pipeline_repo):
    failed_run = _make_run(status="failed")
    success_run = _make_run(status="success", trigger_type="manual")
    pipeline_repo.create(failed_run)
    pipeline_repo.create(success_run)

    found = pipeline_repo.find_latest_success_by_execution_date("etl_sales", date(2024, 1, 15))
    assert found is not None
    assert found.id == success_run.id


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


def test_step_run_update_status_with_started_at(pipeline_repo, step_repo):
    run = _make_run()
    pipeline_repo.create(run)
    step = _make_step(run.id)
    step_repo.create(step)

    started = datetime(2024, 1, 15, 2, 0, 0)
    step_repo.update_status(step.id, "running", started_at=started)

    steps = step_repo.find_by_pipeline_run(run.id)
    assert steps[0].status == "running"
    assert steps[0].started_at == started


def test_initialize_migrates_old_pipeline_run_constraint(tmp_path):
    from airflow_lite.storage.database import Database
    from airflow_lite.storage.repository import PipelineRunRepository

    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE pipeline_runs (
                id TEXT PRIMARY KEY,
                pipeline_name TEXT NOT NULL,
                execution_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                finished_at TEXT,
                trigger_type TEXT NOT NULL DEFAULT 'scheduled',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(pipeline_name, execution_date, trigger_type)
            );

            CREATE TABLE step_runs (
                id TEXT PRIMARY KEY,
                pipeline_run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
                step_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                finished_at TEXT,
                records_processed INTEGER DEFAULT 0,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    database = Database(str(db_path))
    database.initialize()
    repo = PipelineRunRepository(database)

    repo.create(_make_run(status="failed"))
    repo.create(_make_run(status="failed"))
    repo.create(_make_run(status="success"))
    repo.create(_make_run(status="success"))

    assert len(repo.find_by_pipeline("etl_sales")) == 4


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
