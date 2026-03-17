import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: str, level: int = logging.INFO) -> None:
    """로깅 설정.

    - TimedRotatingFileHandler: 일별 로테이션, 30일 보관
    - 로거 네이밍: airflow_lite.{module}.{pipeline}.{stage}
    - 포맷: %(asctime)s [%(levelname)s] %(name)s - %(message)s
    - 로그 경로: {log_dir}/airflow_lite.log (suffix: YYYY-MM-DD)
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / "airflow_lite.log"

    handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger("airflow_lite")
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    root_logger.addHandler(console_handler)
