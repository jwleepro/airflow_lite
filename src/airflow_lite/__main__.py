import sys


def _run_foreground():
    """Windows 서비스 등록 없이 포그라운드에서 실행 (개발/디버깅용)."""
    import logging
    import signal
    import threading
    from pathlib import Path

    import uvicorn

    from airflow_lite.config.settings import Settings
    from airflow_lite.logging_config.setup import setup_logging
    from airflow_lite.storage.database import Database
    from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository

    config_path = sys.argv[2] if len(sys.argv) > 2 else "config/pipelines.yaml"
    settings = Settings.load(config_path)
    setup_logging(settings.storage.log_path)
    logger = logging.getLogger("airflow_lite")

    db = Database(settings.storage.sqlite_path)
    db.initialize()
    run_repo = PipelineRunRepository(db)
    step_repo = StepRunRepository(db)

    # win_service와 동일한 runner factory 사용
    from airflow_lite.service.win_service import AirflowLiteService
    factory_fn = AirflowLiteService._create_runner_factory
    runner_factory = factory_fn(None, settings, run_repo, step_repo)

    from airflow_lite.scheduler.scheduler import PipelineScheduler
    scheduler = PipelineScheduler(settings, runner_factory)
    scheduler.register_pipelines()
    scheduler.start()

    runner_map = {
        p.name: (lambda pn=p.name: runner_factory(pn))
        for p in settings.pipelines
    }
    from airflow_lite.engine.backfill import BackfillManager
    backfill_map = {
        p.name: (lambda pn=p.name: BackfillManager(
            pipeline_runner=runner_factory(pn),
            parquet_base_path=settings.storage.parquet_base_path,
        ))
        for p in settings.pipelines
    }

    from airflow_lite.api.app import create_app
    from airflow_lite.export import FilesystemAnalyticsExportService
    from airflow_lite.query import DuckDBAnalyticsQueryService

    mart_database_path = (
        Path(settings.mart.root_path) / "current" / settings.mart.database_filename
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

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        logger.info("종료 시그널 수신 (signal=%s)", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    config = uvicorn.Config(
        app=app,
        host=getattr(settings.api, "host", "0.0.0.0"),
        port=getattr(settings.api, "port", 8000),
        log_level="info",
    )
    server = uvicorn.Server(config)
    api_thread = threading.Thread(target=server.run, daemon=True)
    api_thread.start()

    logger.info("Airflow Lite 포그라운드 모드 시작")
    stop_event.wait()

    server.should_exit = True
    scheduler.shutdown(wait=True)
    api_thread.join(timeout=30)
    logger.info("Airflow Lite 종료")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m airflow_lite <command>")
        print("Commands:")
        print("  run [config_path]                      포그라운드 실행 (개발/디버깅)")
        print("  service [install|remove|start|stop]     Windows 서비스 관리")
        sys.exit(1)

    command = sys.argv[1]

    if command == "run":
        _run_foreground()
    elif command == "service":
        import win32serviceutil
        from airflow_lite.service.win_service import AirflowLiteService
        win32serviceutil.HandleCommandLine(AirflowLiteService)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
