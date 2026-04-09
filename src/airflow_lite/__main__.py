import sys

from airflow_lite.bootstrap import build_runtime_services, get_api_bind, load_settings

def _run_foreground():
    """Windows 서비스 등록 없이 포그라운드에서 실행 (개발/디버깅용)."""
    import logging
    import signal
    import threading

    import uvicorn

    from airflow_lite.logging_config.setup import setup_logging

    config_path, settings = load_settings(sys.argv[2] if len(sys.argv) > 2 else None)
    setup_logging(settings.storage.log_path)
    logger = logging.getLogger("airflow_lite")
    runtime = build_runtime_services(settings, config_path)

    from airflow_lite.scheduler.scheduler import PipelineScheduler
    scheduler = PipelineScheduler(settings, runtime.runner_factory, config_path=config_path)
    scheduler.register_pipelines()
    scheduler.start()

    from airflow_lite.api.app import create_app
    app = create_app(
        settings,
        runner_map=runtime.runner_map,
        backfill_map=runtime.backfill_map,
        run_repo=runtime.run_repo,
        step_repo=runtime.step_repo,
        admin_repo=runtime.admin_repo,
        analytics_query_service=runtime.analytics_query_service,
        analytics_export_service=runtime.analytics_export_service,
    )
    host, port = get_api_bind(settings)

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        logger.info("종료 시그널 수신 (signal=%s)", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
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
