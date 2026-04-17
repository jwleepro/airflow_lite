import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from airflow_lite.scheduler.scheduler import PipelineScheduler
from airflow_lite.config.settings import (
    DefaultConfig,
    OracleConfig,
    PipelineConfig,
    SchedulerConfig,
    Settings,
    StorageConfig,
)
from airflow_lite.service.dispatch_service import PipelineBusyError


# ── fixtures ───────────────────────────────────────────────────────────────────

def _make_settings(sqlite_path: str, pipelines: list) -> Settings:
    oracle = OracleConfig(
        host="localhost", port=1521, service_name="ORCL",
        user="scott", password="tiger"
    )
    storage = StorageConfig(
        parquet_base_path="/tmp/parquet",
        sqlite_path=sqlite_path,
        log_path="/tmp/logs",
    )
    return Settings(
        oracle=oracle,
        storage=storage,
        defaults=DefaultConfig(),
        pipelines=pipelines,
        scheduler=SchedulerConfig(),
    )


@pytest.fixture
def pipeline_configs():
    return [
        PipelineConfig(
            name="pipeline_a",
            table="TABLE_A",
            source_where_template="DATE_COL >= :data_interval_start AND DATE_COL < :data_interval_end",
            strategy="full",
            schedule="0 2 * * *",
        ),
        PipelineConfig(
            name="pipeline_b",
            table="TABLE_B",
            source_where_template="STATUS_DATE >= :data_interval_start AND STATUS_DATE < :data_interval_end",
            strategy="incremental",
            schedule="30 3 * * *",
            incremental_key="UPDATED_AT",
        ),
    ]


@pytest.fixture
def settings(tmp_path, pipeline_configs):
    return _make_settings(str(tmp_path / "test.db"), pipeline_configs)


@pytest.fixture
def dispatch_service():
    return MagicMock()


@pytest.fixture
def scheduler(settings, dispatch_service):
    sched = PipelineScheduler(settings=settings, dispatch_service=dispatch_service)
    yield sched
    if sched.scheduler.running:
        sched.scheduler.shutdown(wait=False)


# ── 생성자: APScheduler 설정 적용 확인 ────────────────────────────────────────

def test_scheduler_init_applies_job_defaults(scheduler):
    defaults = scheduler.scheduler._job_defaults
    assert defaults["coalesce"] is True
    assert defaults["max_instances"] == 1
    assert defaults["misfire_grace_time"] == 3600


def test_scheduler_init_uses_configured_job_defaults(tmp_path, pipeline_configs, dispatch_service):
    settings = _make_settings(str(tmp_path / "custom.db"), pipeline_configs)
    settings.scheduler = SchedulerConfig(
        coalesce=False,
        max_instances=3,
        misfire_grace_time_seconds=900,
    )

    scheduler = PipelineScheduler(settings=settings, dispatch_service=dispatch_service)

    defaults = scheduler.scheduler._job_defaults
    assert defaults["coalesce"] is False
    assert defaults["max_instances"] == 3
    assert defaults["misfire_grace_time"] == 900


def test_scheduler_init_uses_sqlalchemy_jobstore(scheduler):
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    jobstore = scheduler.scheduler._jobstores["default"]
    assert isinstance(jobstore, SQLAlchemyJobStore)


def test_scheduler_init_sqlite_url_matches_settings(settings, dispatch_service):
    sched = PipelineScheduler(settings=settings, dispatch_service=dispatch_service)
    jobstore = sched.scheduler._jobstores["default"]
    assert str(settings.storage.sqlite_path) in str(jobstore.engine.url)


# ── register_pipelines(): 잡 등록 ────────────────────────────────────────────

def test_register_pipelines_adds_all_jobs(scheduler):
    scheduler.register_pipelines()
    jobs = scheduler.scheduler.get_jobs()
    job_ids = {j.id for j in jobs}
    assert job_ids == {"pipeline_a", "pipeline_b"}


def test_register_pipelines_sets_correct_cron(scheduler):
    scheduler.register_pipelines()
    job_a = scheduler.scheduler.get_job("pipeline_a")
    job_b = scheduler.scheduler.get_job("pipeline_b")
    assert job_a is not None
    assert job_b is not None
    fields_a = {f.name: str(f) for f in job_a.trigger.fields}
    assert fields_a["hour"] == "2"
    assert fields_a["minute"] == "0"
    fields_b = {f.name: str(f) for f in job_b.trigger.fields}
    assert fields_b["hour"] == "3"
    assert fields_b["minute"] == "30"


def test_register_pipelines_replace_existing(settings, dispatch_service):
    """재등록 시 replace_existing=True 동작 검증. MemoryJobStore 로 관찰한다."""
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.schedulers.background import BackgroundScheduler

    sched_mem = BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600},
    )
    scheduler_obj = PipelineScheduler.__new__(PipelineScheduler)
    scheduler_obj.settings = settings
    scheduler_obj.dispatch_service = dispatch_service
    scheduler_obj.config_path = "config/pipelines.yaml"
    scheduler_obj.scheduler = sched_mem

    sched_mem.start()
    scheduler_obj.register_pipelines()
    assert len(sched_mem.get_jobs()) == 2
    scheduler_obj.register_pipelines()
    assert len(sched_mem.get_jobs()) == 2
    sched_mem.shutdown(wait=False)


def test_register_pipelines_empty(tmp_path, dispatch_service):
    empty_settings = _make_settings(str(tmp_path / "empty.db"), [])
    sched = PipelineScheduler(settings=empty_settings, dispatch_service=dispatch_service)
    sched.register_pipelines()
    assert sched.scheduler.get_jobs() == []


def test_register_pipelines_supports_interval_schedule(tmp_path, dispatch_service):
    pipelines = [
        PipelineConfig(
            name="interval_pipeline",
            table="TABLE_C",
            source_where_template="DATE_COL >= :data_interval_start AND DATE_COL < :data_interval_end",
            strategy="full",
            schedule="interval:15m",
        )
    ]
    settings = _make_settings(str(tmp_path / "interval.db"), pipelines)
    sched = PipelineScheduler(settings=settings, dispatch_service=dispatch_service)

    sched.register_pipelines()

    job = sched.scheduler.get_job("interval_pipeline")
    assert job is not None
    assert job.trigger.__class__.__name__ == "IntervalTrigger"


# ── _scheduled_dispatcher_callback: dispatcher 경유 검증 ──────────────────────

def test_scheduled_dispatcher_callback_invokes_submit_manual_run(scheduler, dispatch_service):
    """스케줄 콜백이 dispatcher.submit_manual_run 을 올바른 인자로 호출하는지."""
    from airflow_lite.scheduler.scheduler import _scheduled_dispatcher_callback

    fixed_date = date(2024, 1, 15)
    with patch("airflow_lite.scheduler.scheduler.date") as mock_date_cls:
        mock_date_cls.today.return_value = fixed_date
        _scheduled_dispatcher_callback("pipeline_a")

    dispatch_service.submit_manual_run.assert_called_once_with(
        pipeline_name="pipeline_a",
        execution_date=fixed_date,
        force_rerun=False,
        trigger_type="scheduled",
    )


def test_scheduled_dispatcher_callback_logs_busy_skip(scheduler, dispatch_service, caplog):
    import logging

    from airflow_lite.scheduler.scheduler import _scheduled_dispatcher_callback

    dispatch_service.submit_manual_run.side_effect = PipelineBusyError(
        "pipeline_a",
    )

    with caplog.at_level(logging.INFO, logger="airflow_lite.scheduler"):
        _scheduled_dispatcher_callback("pipeline_a")

    assert any("스케줄 dispatcher 스킵" in r.message for r in caplog.records)


def test_scheduled_dispatcher_callback_swallows_exceptions(scheduler, dispatch_service, caplog):
    """dispatcher 예외는 APScheduler 로 전파되지 않고 로그로 남아야 한다."""
    import logging
    from airflow_lite.scheduler.scheduler import _scheduled_dispatcher_callback

    dispatch_service.submit_manual_run.side_effect = RuntimeError("dispatch failure")

    with caplog.at_level(logging.ERROR, logger="airflow_lite.scheduler"):
        _scheduled_dispatcher_callback("pipeline_a")

    assert any("스케줄 dispatcher 호출 실패" in r.message for r in caplog.records)


# ── start() / shutdown() 생명주기 ─────────────────────────────────────────────

def test_start_after_register_pipelines_succeeds(scheduler):
    scheduler.register_pipelines()
    try:
        scheduler.start()
        assert scheduler.scheduler.running
    finally:
        if scheduler.scheduler.running:
            scheduler.shutdown(wait=False)


def test_start_makes_scheduler_running(scheduler):
    assert not scheduler.scheduler.running
    scheduler.start()
    assert scheduler.scheduler.running


def test_shutdown_stops_scheduler(scheduler):
    scheduler.start()
    assert scheduler.scheduler.running
    scheduler.shutdown(wait=False)
    assert not scheduler.scheduler.running


def test_shutdown_wait_true(scheduler):
    """wait=True 호출 시 정상 종료 (실행 중 작업 없으므로 즉시 완료)."""
    scheduler.start()
    scheduler.shutdown(wait=True)
    assert not scheduler.scheduler.running
