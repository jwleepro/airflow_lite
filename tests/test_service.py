"""
tests/test_service.py — TASK-009: Windows 서비스 테스트

pywin32가 미설치된 환경에서도 동작하도록 win32 모듈을 sys.modules에
stub으로 주입한 뒤 테스트한다. pywin32가 설치된 환경에서는 실제 모듈을 사용한다.
"""
import sys
from datetime import date
import pytest
from unittest.mock import MagicMock, patch


# ── win32 stub 설치 (모듈 임포트 전) ─────────────────────────────────────────

def _install_win32_stubs():
    """pywin32/uvicorn 미설치 환경에 최소 stub 주입. 이미 설치된 경우 건드리지 않는다."""
    if "uvicorn" not in sys.modules:
        m = MagicMock(name="uvicorn")
        m.Config = MagicMock(name="uvicorn.Config")
        m.Server = MagicMock(name="uvicorn.Server")
        sys.modules["uvicorn"] = m

    if "win32event" not in sys.modules:
        m = MagicMock(name="win32event")
        m.INFINITE = 0xFFFFFFFF
        sys.modules["win32event"] = m

    if "win32service" not in sys.modules:
        m = MagicMock(name="win32service")
        m.SERVICE_STOP_PENDING = 3
        sys.modules["win32service"] = m

    if "servicemanager" not in sys.modules:
        m = MagicMock(name="servicemanager")
        m.EVENTLOG_INFORMATION_TYPE = 4
        m.PYS_SERVICE_STARTED = "started"
        sys.modules["servicemanager"] = m

    if "win32serviceutil" not in sys.modules:
        # ServiceFramework 는 실제 클래스여야 상속이 가능하다
        class _ServiceFramework:
            """win32serviceutil.ServiceFramework 최소 stub."""
            def __init__(self, args):
                pass
            def ReportServiceStatus(self, status):
                pass

        m = MagicMock(name="win32serviceutil")
        m.ServiceFramework = _ServiceFramework
        sys.modules["win32serviceutil"] = m


_install_win32_stubs()

import win32event   # noqa: E402  (stub 또는 실제 모듈)
import win32service  # noqa: E402
import win32serviceutil  # noqa: E402


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _make_settings(pipelines=None):
    s = MagicMock(name="settings")
    s.storage.log_path = "/tmp/logs"
    s.storage.sqlite_path = "/tmp/test.db"
    s.storage.parquet_base_path = "/tmp/parquet"
    s.defaults.parquet.compression = "snappy"
    s.defaults.retry.max_attempts = 3
    s.defaults.retry.min_wait_seconds = 4
    s.defaults.retry.max_wait_seconds = 60
    s.defaults.chunk_size = 10000
    s.api.host = "127.0.0.1"
    s.api.port = 8000
    s.mart.enabled = False
    s.mart.refresh_on_success = False
    s.mart.root_path = "/tmp/mart"
    s.mart.database_filename = "analytics.duckdb"
    s.mart.pipeline_datasets = {}
    s.export.root_path = "/tmp/exports"
    s.export.retention_hours = 72
    s.export.cleanup_cooldown_seconds = 300
    s.export.max_workers = 2
    s.export.rows_per_batch = 10000
    s.export.parquet_compression = "snappy"
    s.export.zip_compression = "deflated"
    s.scheduler.coalesce = True
    s.scheduler.max_instances = 1
    s.scheduler.misfire_grace_time_seconds = 3600
    s.webui.monitor_refresh_seconds = 30
    s.webui.analytics_refresh_seconds = 60
    s.webui.exports_active_refresh_seconds = 10
    s.webui.exports_idle_refresh_seconds = 30
    s.webui.recent_runs_limit = 25
    s.webui.detail_preview_page_size = 8
    s.webui.analytics_export_jobs_limit = 8
    s.webui.export_jobs_page_limit = 50
    s.webui.error_message_max_length = 120
    s.webui.default_dataset = "mes_ops"
    s.webui.default_dashboard_id = "operations_overview"
    s.webui.default_language = "en"
    s.pipelines = pipelines if pipelines is not None else []
    return s


def _make_runtime(settings):
    runtime = MagicMock(name="runtime")
    runtime.settings = settings
    runtime.run_repo = MagicMock(name="run_repo")
    runtime.step_repo = MagicMock(name="step_repo")
    runtime.runner_factory = MagicMock(name="runner_factory")
    runtime.runner_map = {}
    runtime.backfill_map = {}
    runtime.analytics_query_service = MagicMock(name="analytics_query_service")
    runtime.analytics_export_service = MagicMock(name="analytics_export_service")
    return runtime


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def service_cls():
    from airflow_lite.service.win_service import AirflowLiteService
    return AirflowLiteService


@pytest.fixture
def mock_event():
    return MagicMock(name="stop_event_handle")


@pytest.fixture
def svc(service_cls, mock_event):
    """win32event.CreateEvent 를 고정 mock 으로 교체하여 인스턴스 생성."""
    with patch.object(win32event, "CreateEvent", return_value=mock_event):
        return service_cls([])


# ── 클래스 속성 검증 ──────────────────────────────────────────────────────────

class TestServiceClassAttributes:
    def test_svc_name(self, service_cls):
        assert service_cls._svc_name_ == "AirflowLiteService"

    def test_svc_display_name(self, service_cls):
        assert service_cls._svc_display_name_ == "Airflow Lite Pipeline Service"

    def test_svc_description_not_empty(self, service_cls):
        assert isinstance(service_cls._svc_description_, str)
        assert service_cls._svc_description_

    def test_inherits_service_framework(self, service_cls):
        assert issubclass(service_cls, win32serviceutil.ServiceFramework)


# ── __init__ 초기 상태 검증 ───────────────────────────────────────────────────

class TestServiceInit:
    def test_stop_event_is_assigned(self, svc, mock_event):
        assert svc.stop_event is mock_event

    def test_scheduler_initially_none(self, svc):
        assert svc.scheduler is None

    def test_uvicorn_server_initially_none(self, svc):
        assert svc.uvicorn_server is None

    def test_api_thread_initially_none(self, svc):
        assert svc.api_thread is None


# ── SvcDoRun() 실행 흐름 검증 ─────────────────────────────────────────────────

class TestSvcDoRun:
    """SvcDoRun() 실행 순서와 주요 호출을 검증한다."""

    @pytest.fixture
    def run_ctx(self, svc):
        """모든 의존성을 mock 하고 SvcDoRun() 을 한 번 실행, mock 딕셔너리를 yield."""
        mock_settings = _make_settings()
        mock_runtime = _make_runtime(mock_settings)
        mock_scheduler = MagicMock(name="scheduler")
        mock_uvicorn_server = MagicMock(name="uvicorn_server")
        mock_api_thread = MagicMock(name="api_thread")

        with patch("airflow_lite.service.win_service.load_settings") as mock_load_settings, \
             patch("airflow_lite.service.win_service.build_runtime_services", return_value=mock_runtime) as mock_build_runtime, \
             patch("airflow_lite.logging_config.setup.setup_logging") as mock_logging, \
             patch("airflow_lite.scheduler.scheduler.PipelineScheduler",
                   return_value=mock_scheduler), \
             patch("airflow_lite.api.app.create_app"), \
             patch("airflow_lite.service.win_service.uvicorn") as mock_uvicorn_mod, \
             patch("airflow_lite.service.win_service.threading") as mock_threading_mod, \
             patch("airflow_lite.service.win_service.servicemanager"), \
             patch.object(win32event, "WaitForSingleObject"):

            mock_load_settings.return_value = ("config/pipelines.yaml", mock_settings)
            mock_uvicorn_mod.Server.return_value = mock_uvicorn_server
            mock_threading_mod.Thread.return_value = mock_api_thread

            svc.SvcDoRun()

            yield {
                "load_settings": mock_load_settings,
                "build_runtime_services": mock_build_runtime,
                "setup_logging": mock_logging,
                "scheduler": mock_scheduler,
                "uvicorn_server": mock_uvicorn_server,
                "api_thread": mock_api_thread,
                "settings": mock_settings,
                "runtime": mock_runtime,
                "threading": mock_threading_mod,
            }

    def test_loads_settings_from_yaml(self, run_ctx):
        run_ctx["load_settings"].assert_called_once_with()

    def test_calls_setup_logging_with_log_path(self, run_ctx):
        run_ctx["setup_logging"].assert_called_once_with(
            run_ctx["settings"].storage.log_path
        )

    def test_builds_runtime_services(self, run_ctx):
        run_ctx["build_runtime_services"].assert_called_once()
        assert "runner_factory_builder" in run_ctx["build_runtime_services"].call_args.kwargs

    def test_registers_pipelines(self, run_ctx):
        run_ctx["scheduler"].register_pipelines.assert_called_once()

    def test_starts_scheduler(self, run_ctx):
        run_ctx["scheduler"].start.assert_called_once()

    def test_starts_api_thread(self, run_ctx):
        run_ctx["api_thread"].start.assert_called_once()

    def test_api_thread_is_daemon(self, run_ctx):
        """API 스레드는 daemon=True 로 생성되어야 한다."""
        _, call_kwargs = run_ctx["threading"].Thread.call_args
        assert call_kwargs.get("daemon") is True

    def test_passes_backfill_map_to_app(self, svc):
        pipeline = MagicMock(name="pipeline")
        pipeline.name = "test_pipeline"
        mock_settings = _make_settings(pipelines=[pipeline])
        mock_runtime = _make_runtime(mock_settings)
        mock_runtime.runner_map = {"test_pipeline": MagicMock(name="runner_entry")}
        mock_runtime.backfill_map = {"test_pipeline": MagicMock(name="backfill_entry")}
        create_app_mock = MagicMock()

        with patch("airflow_lite.service.win_service.load_settings") as mock_load_settings, \
             patch("airflow_lite.service.win_service.build_runtime_services", return_value=mock_runtime), \
             patch("airflow_lite.logging_config.setup.setup_logging"), \
             patch("airflow_lite.scheduler.scheduler.PipelineScheduler"), \
             patch("airflow_lite.api.app.create_app", create_app_mock), \
             patch("airflow_lite.service.win_service.uvicorn"), \
             patch("airflow_lite.service.win_service.threading"), \
             patch("airflow_lite.service.win_service.servicemanager"), \
             patch.object(win32event, "WaitForSingleObject"):

            mock_load_settings.return_value = ("config/pipelines.yaml", mock_settings)
            svc.SvcDoRun()

        _, kwargs = create_app_mock.call_args
        assert "backfill_map" in kwargs
        assert list(kwargs["backfill_map"].keys()) == ["test_pipeline"]
        assert callable(kwargs["backfill_map"]["test_pipeline"])
        assert callable(kwargs["runner_map"]["test_pipeline"])

    def test_waits_for_stop_event_with_infinite_timeout(self, svc):
        """WaitForSingleObject(stop_event, INFINITE) 로 종료 이벤트를 대기해야 한다."""
        mock_settings = _make_settings()
        mock_runtime = _make_runtime(mock_settings)
        with patch("airflow_lite.service.win_service.load_settings") as mock_load_settings, \
             patch("airflow_lite.service.win_service.build_runtime_services", return_value=mock_runtime), \
             patch("airflow_lite.logging_config.setup.setup_logging"), \
             patch("airflow_lite.scheduler.scheduler.PipelineScheduler"), \
             patch("airflow_lite.api.app.create_app"), \
             patch("airflow_lite.service.win_service.uvicorn"), \
             patch("airflow_lite.service.win_service.threading"), \
             patch("airflow_lite.service.win_service.servicemanager"), \
             patch.object(win32event, "WaitForSingleObject") as mock_wait:

            mock_load_settings.return_value = ("config/pipelines.yaml", mock_settings)
            svc.SvcDoRun()

        mock_wait.assert_called_once_with(svc.stop_event, win32event.INFINITE)

    def test_startup_failure_does_not_propagate_exception(self, svc):
        """Settings.load() 실패 시 예외가 밖으로 전파되지 않아야 한다."""
        with patch("airflow_lite.service.win_service.load_settings") as mock_load_settings, \
             patch("airflow_lite.service.win_service.servicemanager"), \
             patch.object(win32event, "WaitForSingleObject"):
            mock_load_settings.side_effect = FileNotFoundError("config not found")
            svc.SvcDoRun()  # should not raise


# ── SvcStop() graceful shutdown 검증 ─────────────────────────────────────────

class TestSvcStop:
    """SvcStop() 종료 순서와 각 분기 조건을 검증한다."""

    def test_reports_stop_pending_status(self, svc):
        with patch.object(svc, "ReportServiceStatus") as mock_report, \
             patch.object(win32event, "SetEvent"):
            svc.SvcStop()
        mock_report.assert_called_once_with(win32service.SERVICE_STOP_PENDING)

    def test_sets_uvicorn_should_exit_true(self, svc):
        mock_uvicorn = MagicMock()
        svc.uvicorn_server = mock_uvicorn

        with patch.object(svc, "ReportServiceStatus"), \
             patch.object(win32event, "SetEvent"):
            svc.SvcStop()

        assert mock_uvicorn.should_exit is True

    def test_shuts_down_scheduler_with_wait_true(self, svc):
        mock_scheduler = MagicMock()
        svc.scheduler = mock_scheduler

        with patch.object(svc, "ReportServiceStatus"), \
             patch.object(win32event, "SetEvent"):
            svc.SvcStop()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    def test_joins_api_thread_with_30s_timeout(self, svc):
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        svc.api_thread = mock_thread

        with patch.object(svc, "ReportServiceStatus"), \
             patch.object(win32event, "SetEvent"):
            svc.SvcStop()

        mock_thread.join.assert_called_once_with(timeout=30)

    def test_skips_join_when_thread_already_stopped(self, svc):
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        svc.api_thread = mock_thread

        with patch.object(svc, "ReportServiceStatus"), \
             patch.object(win32event, "SetEvent"):
            svc.SvcStop()

        mock_thread.join.assert_not_called()

    def test_signals_stop_event(self, svc):
        with patch.object(svc, "ReportServiceStatus"), \
             patch.object(win32event, "SetEvent") as mock_set_event:
            svc.SvcStop()

        mock_set_event.assert_called_once_with(svc.stop_event)

    def test_no_crash_when_all_none(self, svc):
        """scheduler/uvicorn_server/api_thread 가 모두 None 이어도 예외 없이 종료."""
        svc.scheduler = None
        svc.uvicorn_server = None
        svc.api_thread = None

        with patch.object(svc, "ReportServiceStatus"), \
             patch.object(win32event, "SetEvent"):
            svc.SvcStop()  # should not raise

    def test_skips_scheduler_shutdown_when_none(self, svc):
        svc.scheduler = None

        with patch.object(svc, "ReportServiceStatus"), \
             patch.object(win32event, "SetEvent"):
            svc.SvcStop()  # should not raise


# ── _create_runner_factory() 검증 ─────────────────────────────────────────────

class TestCreateRunnerFactory:
    """_create_runner_factory() 반환값이 callable 이고 올바른 객체를 생성한다."""

    @pytest.fixture
    def real_settings(self, tmp_path):
        from airflow_lite.config.settings import (
            OracleConfig, StorageConfig, DefaultConfig, PipelineConfig, Settings,
        )
        return Settings(
            oracle=OracleConfig("localhost", 1521, "ORCL", "scott", "tiger"),
            storage=StorageConfig(
                str(tmp_path / "parquet"),
                str(tmp_path / "test.db"),
                str(tmp_path),
            ),
            defaults=DefaultConfig(),
            pipelines=[
                PipelineConfig(
                    name="full_pipe",
                    table="T_FULL",
                    partition_column="DT",
                    strategy="full",
                    schedule="0 2 * * *",
                ),
                PipelineConfig(
                    name="inc_pipe",
                    table="T_INC",
                    partition_column="DT",
                    strategy="incremental",
                    schedule="0 */6 * * *",
                    incremental_key="UPDATED_AT",
                ),
            ],
        )

    @pytest.fixture
    def repos(self, tmp_path):
        from airflow_lite.storage.database import Database
        from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository
        db = Database(str(tmp_path / "test.db"))
        db.initialize()
        return PipelineRunRepository(db), StepRunRepository(db)

    def test_returns_callable(self, svc, real_settings, repos):
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        assert callable(factory)

    def test_factory_returns_pipeline_runner(self, svc, real_settings, repos):
        from airflow_lite.engine.pipeline import PipelineRunner
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")
        assert isinstance(runner, PipelineRunner)

    def test_factory_uses_full_strategy_for_full_config(self, svc, real_settings, repos):
        from airflow_lite.engine.strategy import FullMigrationStrategy
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")
        assert isinstance(runner.pipeline.strategy, FullMigrationStrategy)

    def test_factory_uses_incremental_strategy_for_incremental_config(self, svc, real_settings, repos):
        from airflow_lite.engine.strategy import IncrementalMigrationStrategy
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("inc_pipe")
        assert isinstance(runner.pipeline.strategy, IncrementalMigrationStrategy)

    def test_factory_sets_correct_pipeline_name(self, svc, real_settings, repos):
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")
        assert runner.pipeline.name == "full_pipe"

    def test_factory_sets_on_failure_callback(self, svc, real_settings, repos):
        """RetryConfig.on_failure_callback이 None이 아니어야 한다."""
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")
        etl_stage = runner.pipeline.stages[0]
        assert etl_stage.retry_config.on_failure_callback is not None
        assert callable(etl_stage.retry_config.on_failure_callback)

    def test_factory_on_failure_callback_calls_alert_manager(self, svc, real_settings, repos):
        """on_failure_callback 호출 시 AlertManager.notify()가 실행된다."""
        from datetime import date as date_cls
        from airflow_lite.engine.stage import StageContext

        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")
        callback = runner.pipeline.stages[0].retry_config.on_failure_callback

        context = StageContext(
            pipeline_name="full_pipe",
            execution_date=date_cls(2026, 1, 1),
            table_config=real_settings.pipelines[0],
            run_id="test-run-id",
            chunk_size=10000,
        )
        exc = RuntimeError("테스트 오류")

        with patch("airflow_lite.alerting.base.AlertManager.notify") as mock_notify:
            callback(context, exc)

        mock_notify.assert_called_once()
        alert_arg = mock_notify.call_args[0][0]
        assert alert_arg.pipeline_name == "full_pipe"
        assert alert_arg.status == "failed"
        assert "테스트 오류" in alert_arg.error_message

    def test_factory_marks_run_failed_when_verify_returns_false(self, svc, real_settings, repos):
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")

        runner.pipeline.strategy.extract = MagicMock(return_value=iter([]))
        runner.pipeline.strategy.transform = MagicMock()
        runner.pipeline.strategy.load = MagicMock()
        runner.pipeline.strategy.verify = MagicMock(return_value=False)

        result = runner.run(date(2026, 1, 1))
        steps = step_repo.find_by_pipeline_run(result.id)
        statuses = {step.step_name: step.status for step in steps}

        assert result.status == "failed"
        assert statuses["extract_transform_load"] == "success"
        assert statuses["verify"] == "failed"

    def test_factory_sets_on_run_success_callback(self, svc, real_settings, repos):
        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")

        assert runner.on_run_success is not None
        assert callable(runner.on_run_success)

    def test_factory_on_run_success_calls_alert_manager(self, svc, real_settings, repos):
        from datetime import date as date_cls
        from airflow_lite.engine.stage import StageContext

        run_repo, step_repo = repos
        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")

        context = StageContext(
            pipeline_name="full_pipe",
            execution_date=date_cls(2026, 1, 1),
            table_config=real_settings.pipelines[0],
            run_id="test-run-id",
            chunk_size=10000,
        )

        with patch("airflow_lite.alerting.base.AlertManager.notify") as mock_notify:
            runner.on_run_success(context)

        mock_notify.assert_called_once()
        alert_arg = mock_notify.call_args[0][0]
        assert alert_arg.pipeline_name == "full_pipe"
        assert alert_arg.status == "success"

    def test_factory_on_run_success_plans_mart_refresh_when_enabled(self, svc, real_settings, repos):
        from datetime import date as date_cls
        from airflow_lite.engine.stage import StageContext
        from airflow_lite.mart import MartRefreshMode

        run_repo, step_repo = repos
        real_settings.mart.enabled = True
        real_settings.mart.refresh_on_success = True
        real_settings.mart.pipeline_datasets = {"full_pipe": "ops_dataset"}

        factory = svc._create_runner_factory(real_settings, run_repo, step_repo)
        runner = factory("full_pipe")
        context = StageContext(
            pipeline_name="full_pipe",
            execution_date=date_cls(2026, 1, 1),
            table_config=real_settings.pipelines[0],
            run_id="test-run-id",
            chunk_size=10000,
        )

        mock_plan = MagicMock()
        mock_plan.request.dataset_name = "ops_dataset"
        mock_plan.request.mode = MartRefreshMode.FULL
        mock_plan.request.source_paths = ("source.parquet",)
        mock_plan.build_plan.paths.staging_db_path = "staging.duckdb"
        mock_plan.build_plan.paths.snapshot_db_path = "snapshot.duckdb"

        refresh_result = MagicMock()
        refresh_result.validation_report.is_valid = True
        refresh_result.promoted = True
        refresh_result.plan = mock_plan
        refresh_result.build_result.row_count = 10
        refresh_result.build_result.file_count = 1

        with patch("airflow_lite.alerting.base.AlertManager.notify"), \
             patch("airflow_lite.mart.orchestration.MartRefreshCoordinator.plan_refresh", return_value=mock_plan) as mock_refresh, \
             patch("airflow_lite.mart.refresh.MartRefreshExecutor.execute_refresh", return_value=refresh_result) as mock_execute:
            runner.on_run_success(context)

        mock_refresh.assert_called_once_with(context)
        mock_execute.assert_called_once_with(mock_plan)


# ── CLI __main__.py 검증 ──────────────────────────────────────────────────────

class TestCLI:
    """python -m airflow_lite service ... CLI 라우팅을 검증한다."""

    def test_service_command_calls_handle_command_line(self):
        from airflow_lite.__main__ import main
        from airflow_lite.service.win_service import AirflowLiteService

        with patch.object(win32serviceutil, "HandleCommandLine") as mock_handle, \
             patch("sys.argv", ["airflow_lite", "service", "install"]):
            main()

        mock_handle.assert_called_once_with(AirflowLiteService)

    def test_unknown_command_exits_with_code_1(self):
        from airflow_lite.__main__ import main

        with patch("sys.argv", ["airflow_lite", "unknown_cmd"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    def test_no_args_exits_with_code_1(self):
        from airflow_lite.__main__ import main

        with patch("sys.argv", ["airflow_lite"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
