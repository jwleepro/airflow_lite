import threading
import logging
from pathlib import Path

import win32serviceutil
import win32service
import win32event
import servicemanager
import uvicorn

from airflow_lite.runtime import create_runner_factory

logger = logging.getLogger("airflow_lite.service")


class AirflowLiteService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AirflowLiteService"
    _svc_display_name_ = "Airflow Lite Pipeline Service"
    _svc_description_ = "MES 데이터 파이프라인 엔진"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.scheduler = None
        self.uvicorn_server = None
        self.api_thread = None

    def SvcDoRun(self):
        """서비스 시작.

        1. Settings 로드
        2. 로깅 설정
        3. DB 초기화 및 Repository 생성
        4. PipelineScheduler 시작 (APScheduler — BackgroundScheduler)
        5. uvicorn을 별도 스레드에서 실행 (FastAPI)
        6. 종료 이벤트 대기
        """
        try:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )

            # 1. Settings 로드
            from airflow_lite.config.settings import Settings
            settings = Settings.load("config/pipelines.yaml")

            # 2. 로깅 설정
            from airflow_lite.logging_config.setup import setup_logging
            setup_logging(settings.storage.log_path)

            # 3. DB 초기화 및 Repository 생성
            from airflow_lite.storage.database import Database
            from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository
            db = Database(settings.storage.sqlite_path)
            db.initialize()
            run_repo = PipelineRunRepository(db)
            step_repo = StepRunRepository(db)

            # 4. PipelineScheduler 시작
            runner_factory = self._create_runner_factory(settings, run_repo, step_repo)

            from airflow_lite.scheduler.scheduler import PipelineScheduler
            self.scheduler = PipelineScheduler(settings, runner_factory)
            self.scheduler.register_pipelines()
            self.scheduler.start()

            # 5. uvicorn을 별도 스레드에서 실행
            runner_map = {
                p.name: (lambda pipeline_name=p.name: runner_factory(pipeline_name))
                for p in settings.pipelines
            }
            from airflow_lite.engine.backfill import BackfillManager
            backfill_map = {
                p.name: (
                    lambda pipeline_name=p.name: BackfillManager(
                        pipeline_runner=runner_factory(pipeline_name),
                        parquet_base_path=settings.storage.parquet_base_path,
                    )
                )
                for p in settings.pipelines
            }

            from airflow_lite.api.app import create_app
            from airflow_lite.export import FilesystemAnalyticsExportService
            from airflow_lite.query import DuckDBAnalyticsQueryService

            mart_database_path = (
                Path(settings.mart.root_path)
                / "current"
                / settings.mart.database_filename
            )
            analytics_query_service = DuckDBAnalyticsQueryService(mart_database_path)
            analytics_export_service = FilesystemAnalyticsExportService(
                root_path=Path(settings.mart.root_path).parent / "exports",
                query_service=analytics_query_service,
            )
            app = create_app(
                settings,
                runner_map=runner_map,
                backfill_map=backfill_map,
                run_repo=run_repo,
                step_repo=step_repo,
                analytics_query_service=analytics_query_service,
                analytics_export_service=analytics_export_service,
            )

            config = uvicorn.Config(
                app=app,
                host=getattr(settings.api, "host", "0.0.0.0"),
                port=getattr(settings.api, "port", 8000),
                log_level="info",
            )
            self.uvicorn_server = uvicorn.Server(config)

            self.api_thread = threading.Thread(
                target=self.uvicorn_server.run,
                daemon=True,
            )
            self.api_thread.start()

            logger.info("Airflow Lite 서비스 시작됨")

            # 6. 종료 이벤트 대기
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

        except Exception as e:
            logger.error("서비스 시작 실패: %s", e)
            servicemanager.LogErrorMsg(f"서비스 시작 실패: {e}")

    def SvcStop(self):
        """Graceful shutdown.

        1. 서비스 상태를 STOP_PENDING으로 변경
        2. uvicorn 서버 종료
        3. PipelineScheduler shutdown(wait=True) — 실행 중인 파이프라인 완료 대기
        4. API 스레드 join (timeout=30초)
        5. 종료 이벤트 시그널
        """
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info("서비스 종료 요청 수신")

        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True

        if self.scheduler:
            self.scheduler.shutdown(wait=True)

        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=30)

        win32event.SetEvent(self.stop_event)
        logger.info("서비스 종료됨")

    def _create_runner_factory(self, settings, run_repo, step_repo):
        return create_runner_factory(settings, run_repo, step_repo)
