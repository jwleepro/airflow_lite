import threading
import logging

import win32serviceutil
import win32service
import win32event
import servicemanager
import uvicorn

from airflow_lite.bootstrap import build_runtime_services, get_api_bind, load_settings
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
            config_path, settings = load_settings()

            # 2. 로깅 설정
            from airflow_lite.logging_config.setup import setup_logging
            setup_logging(settings.storage.log_path)

            # 3. 런타임 구성 생성
            runtime = build_runtime_services(
                settings,
                runner_factory_builder=self._create_runner_factory,
            )

            from airflow_lite.scheduler.scheduler import PipelineScheduler
            self.scheduler = PipelineScheduler(
                settings,
                runtime.runner_factory,
                config_path=config_path,
            )
            self.scheduler.register_pipelines()
            self.scheduler.start()

            # 4. uvicorn을 별도 스레드에서 실행
            from airflow_lite.api.app import create_app
            app = create_app(
                settings,
                runner_map=runtime.runner_map,
                backfill_map=runtime.backfill_map,
                run_repo=runtime.run_repo,
                step_repo=runtime.step_repo,
                analytics_query_service=runtime.analytics_query_service,
                analytics_export_service=runtime.analytics_export_service,
            )
            host, port = get_api_bind(settings)

            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
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
