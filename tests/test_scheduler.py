import time
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from airflow_lite.scheduler.scheduler import PipelineScheduler
from airflow_lite.config.settings import PipelineConfig, Settings, StorageConfig, OracleConfig, DefaultConfig


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
    return Settings(oracle=oracle, storage=storage, defaults=DefaultConfig(), pipelines=pipelines)


@pytest.fixture
def pipeline_configs():
    return [
        PipelineConfig(
            name="pipeline_a",
            table="TABLE_A",
            partition_column="DATE_COL",
            strategy="full",
            schedule="0 2 * * *",
        ),
        PipelineConfig(
            name="pipeline_b",
            table="TABLE_B",
            partition_column="DATE_COL",
            strategy="incremental",
            schedule="30 3 * * *",
            incremental_key="UPDATED_AT",
        ),
    ]


@pytest.fixture
def settings(tmp_path, pipeline_configs):
    return _make_settings(str(tmp_path / "test.db"), pipeline_configs)


@pytest.fixture
def runner_factory():
    return MagicMock()


@pytest.fixture
def scheduler(settings, runner_factory):
    sched = PipelineScheduler(settings=settings, runner_factory=runner_factory)
    yield sched
    # 시작된 경우 종료
    if sched.scheduler.running:
        sched.scheduler.shutdown(wait=False)


# ── 생성자: APScheduler 설정 적용 확인 ────────────────────────────────────────

def test_scheduler_init_applies_job_defaults(scheduler):
    defaults = scheduler.scheduler._job_defaults
    assert defaults["coalesce"] is True
    assert defaults["max_instances"] == 1
    assert defaults["misfire_grace_time"] == 3600


def test_scheduler_init_uses_sqlalchemy_jobstore(scheduler):
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    jobstore = scheduler.scheduler._jobstores["default"]
    assert isinstance(jobstore, SQLAlchemyJobStore)


def test_scheduler_init_sqlite_url_matches_settings(settings, runner_factory):
    sched = PipelineScheduler(settings=settings, runner_factory=runner_factory)
    jobstore = sched.scheduler._jobstores["default"]
    assert str(settings.storage.sqlite_path) in str(jobstore.engine.url)


# ── register_pipelines(): CronTrigger 등록 ────────────────────────────────────

def test_register_pipelines_adds_all_jobs(scheduler, pipeline_configs):
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
    # CronTrigger 필드 검증: hour/minute 확인
    fields_a = {f.name: str(f) for f in job_a.trigger.fields}
    assert fields_a["hour"] == "2"
    assert fields_a["minute"] == "0"
    fields_b = {f.name: str(f) for f in job_b.trigger.fields}
    assert fields_b["hour"] == "3"
    assert fields_b["minute"] == "30"


def test_register_pipelines_replace_existing(settings, runner_factory):
    """재등록 시 replace_existing=True 동작: 동일 id 잡이 교체된다.

    SQLite jobstore는 pickle 직렬화를 사용하므로 MemoryJobStore로 검증한다.
    register_pipelines()를 두 번 호출해도 같은 id 잡이 교체되어 개수가 유지된다.
    """
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.schedulers.background import BackgroundScheduler

    sched_mem = BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600},
    )
    scheduler_obj = PipelineScheduler.__new__(PipelineScheduler)
    scheduler_obj.settings = settings
    scheduler_obj.runner_factory = runner_factory
    scheduler_obj.scheduler = sched_mem

    # start() 후에야 jobstore가 활성화되어 replace_existing이 즉시 적용됨
    sched_mem.start()
    scheduler_obj.register_pipelines()
    assert len(sched_mem.get_jobs()) == 2

    # 재등록해도 개수 유지 (replace_existing=True)
    scheduler_obj.register_pipelines()
    assert len(sched_mem.get_jobs()) == 2

    sched_mem.shutdown(wait=False)


def test_register_pipelines_empty(tmp_path, runner_factory):
    settings = _make_settings(str(tmp_path / "empty.db"), [])
    sched = PipelineScheduler(settings=settings, runner_factory=runner_factory)
    sched.register_pipelines()
    assert sched.scheduler.get_jobs() == []


# ── start() / shutdown() 생명주기 ─────────────────────────────────────────────

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


# ── _run_pipeline(): runner_factory 호출 ─────────────────────────────────────

def test_run_pipeline_calls_factory_with_name(scheduler, runner_factory):
    mock_runner = MagicMock()
    runner_factory.return_value = mock_runner

    scheduler._run_pipeline("pipeline_a")

    runner_factory.assert_called_once_with("pipeline_a")


def test_run_pipeline_calls_runner_run_with_today(scheduler, runner_factory):
    mock_runner = MagicMock()
    runner_factory.return_value = mock_runner

    fixed_date = date(2024, 1, 15)
    with patch("airflow_lite.scheduler.scheduler.date") as mock_date_cls:
        mock_date_cls.today.return_value = fixed_date
        scheduler._run_pipeline("pipeline_a")

    mock_runner.run.assert_called_once_with(
        execution_date=fixed_date,
        trigger_type="scheduled",
    )


def test_run_pipeline_trigger_type_is_scheduled(scheduler, runner_factory):
    mock_runner = MagicMock()
    runner_factory.return_value = mock_runner

    scheduler._run_pipeline("pipeline_b")

    _, kwargs = mock_runner.run.call_args
    assert kwargs["trigger_type"] == "scheduled"


# ── max_instances=1 동시 실행 방지 확인 ──────────────────────────────────────

def test_max_instances_is_one_in_job_defaults(scheduler):
    """job_defaults에 max_instances=1이 설정되어 있는지 확인."""
    assert scheduler.scheduler._job_defaults["max_instances"] == 1


# ── coalesce=True 누적 실행 병합 확인 ────────────────────────────────────────

def test_coalesce_is_true_in_job_defaults(scheduler):
    """job_defaults에 coalesce=True가 설정되어 있는지 확인."""
    assert scheduler.scheduler._job_defaults["coalesce"] is True


# ── misfire_grace_time 확인 ──────────────────────────────────────────────────

def test_misfire_grace_time_is_3600(scheduler):
    """misfire_grace_time이 3600초(1시간)인지 확인."""
    assert scheduler.scheduler._job_defaults["misfire_grace_time"] == 3600


# ── graceful shutdown: 실행 중 작업 완료 대기 ────────────────────────────────

def test_graceful_shutdown_waits_for_running_job(tmp_path, runner_factory):
    """shutdown(wait=True) 호출 시 실행 중인 작업이 완료될 때까지 대기한다.

    APScheduler의 BackgroundScheduler는 내부 스레드풀을 사용한다.
    wait=True 시 실행 중인 작업이 완료될 때까지 블로킹됨을 직접 검증한다.
    """
    import threading
    from apscheduler.schedulers.background import BackgroundScheduler

    job_started = threading.Event()
    job_finished = threading.Event()

    # 직접 BackgroundScheduler에 실행 시간이 있는 잡을 등록하여 검증
    sched_internal = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600}
    )

    def long_job():
        job_started.set()
        time.sleep(0.3)
        job_finished.set()

    sched_internal.add_job(long_job, "interval", seconds=1)
    sched_internal.start()

    # 잡이 시작될 때까지 대기
    job_started.wait(timeout=3)

    # 잡 실행 중에 shutdown(wait=True) 호출 → 잡 완료까지 블로킹
    sched_internal.shutdown(wait=True)

    # shutdown 완료 후 잡도 완료되어 있어야 함
    assert job_finished.is_set()
