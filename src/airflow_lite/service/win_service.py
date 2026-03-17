import threading
import logging

import win32serviceutil
import win32service
import win32event
import servicemanager
import uvicorn

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
            runner_map = {p.name: runner_factory(p.name) for p in settings.pipelines}

            from airflow_lite.api.app import create_app
            app = create_app(
                settings,
                runner_map=runner_map,
                run_repo=run_repo,
                step_repo=step_repo,
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
        """pipeline_name을 받아 PipelineRunner를 생성하는 팩토리 함수 반환.

        공유 인프라(OracleClient, ParquetWriter, StageStateMachine)는 한 번 생성하고,
        PipelineRunner는 호출마다 새 인스턴스를 반환한다.
        """
        from airflow_lite.engine.pipeline import PipelineDefinition, PipelineRunner
        from airflow_lite.engine.stage import RetryConfig, StageDefinition, StageResult
        from airflow_lite.engine.state_machine import StageStateMachine
        from airflow_lite.engine.strategy import FullMigrationStrategy, IncrementalMigrationStrategy
        from airflow_lite.extract.chunked_reader import ChunkedReader
        from airflow_lite.extract.oracle_client import OracleClient
        from airflow_lite.transform.parquet_writer import ParquetWriter

        oracle_client = OracleClient(settings.oracle)
        parquet_writer = ParquetWriter(
            base_path=settings.storage.parquet_base_path,
            compression=settings.defaults.parquet.compression,
        )
        state_machine = StageStateMachine(step_repo)
        pipeline_config_map = {p.name: p for p in settings.pipelines}

        def factory(pipeline_name: str) -> PipelineRunner:
            pipeline_config = pipeline_config_map[pipeline_name]
            chunk_size = pipeline_config.chunk_size or settings.defaults.chunk_size
            chunked_reader = ChunkedReader(connection=None, chunk_size=chunk_size)

            if pipeline_config.strategy == "full":
                strategy = FullMigrationStrategy(oracle_client, chunked_reader, parquet_writer)
            else:
                strategy = IncrementalMigrationStrategy(oracle_client, chunked_reader, parquet_writer)

            retry_config = RetryConfig(
                max_attempts=settings.defaults.retry.max_attempts,
                min_wait_seconds=settings.defaults.retry.min_wait_seconds,
                max_wait_seconds=settings.defaults.retry.max_wait_seconds,
            )

            def etl_stage(context) -> StageResult:
                total = 0
                for chunk in strategy.extract(context):
                    arrow_table = strategy.transform(chunk, context)
                    total += strategy.load(arrow_table, context)
                return StageResult(records_processed=total)

            def verify_stage(context) -> StageResult:
                strategy.verify(context)
                return StageResult()

            stages = [
                StageDefinition(
                    name="extract_transform_load",
                    callable=etl_stage,
                    retry_config=retry_config,
                ),
                StageDefinition(
                    name="verify",
                    callable=verify_stage,
                    retry_config=RetryConfig(max_attempts=1),
                ),
            ]

            return PipelineRunner(
                pipeline=PipelineDefinition(
                    name=pipeline_name,
                    stages=stages,
                    strategy=strategy,
                    table_config=pipeline_config,
                    chunk_size=chunk_size,
                ),
                run_repo=run_repo,
                step_repo=step_repo,
                state_machine=state_machine,
            )

        return factory
