from datetime import date, datetime

from airflow_lite.storage.models import PipelineRun


def test_find_any_active_by_pipeline_returns_running(pipeline_repo):
    run = PipelineRun(
        id="run-running",
        pipeline_name="demo",
        execution_date=date(2026, 4, 16),
        status="queued",
        trigger_type="manual",
    )
    pipeline_repo.create(run)
    pipeline_repo.mark_running(run.id, started_at=datetime(2026, 4, 16, 9, 0, 0))

    active = pipeline_repo.find_any_active_by_pipeline("demo")

    assert active is not None
    assert active.id == "run-running"
    assert active.status == "running"


def test_find_any_active_by_pipeline_returns_none_when_all_terminal(pipeline_repo):
    run = PipelineRun(
        id="run-success",
        pipeline_name="demo",
        execution_date=date(2026, 4, 16),
        status="success",
        finished_at=datetime(2026, 4, 16, 10, 0, 0),
        trigger_type="manual",
    )
    pipeline_repo.create(run)

    active = pipeline_repo.find_any_active_by_pipeline("demo")

    assert active is None
