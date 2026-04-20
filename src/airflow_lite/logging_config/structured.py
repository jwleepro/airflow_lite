"""Structlog configuration with stdlib logging integration.

기존 logging.getLogger() 호출이 structlog를 경유하도록 브릿지합니다.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

import structlog

from .context import get_context_dict

_logging_configured = False


def add_request_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """모든 로그에 request_id, pipeline_name 자동 추가."""
    ctx = get_context_dict()
    for key, value in ctx.items():
        if value is not None:
            event_dict[key] = value
    return event_dict


def mask_sensitive_data(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """민감정보(password, token, secret) 마스킹."""
    sensitive_keys = {"password", "token", "secret", "api_key", "credential"}
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            event_dict[key] = "***"
    return event_dict


def setup_structlog(
    log_dir: str,
    level: int = logging.INFO,
    json_output: bool = False,
) -> None:
    """Structlog + 표준 logging 통합 설정.

    Args:
        log_dir: 로그 파일 저장 디렉토리
        level: 로그 레벨 (기본 INFO)
        json_output: True면 JSON Lines 포맷 (운영 환경), False면 컬러 콘솔 (개발)
    """
    global _logging_configured
    if _logging_configured:
        return
    _logging_configured = True

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=str(log_path / "airflow_lite.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"

    console_handler = logging.StreamHandler(sys.stdout)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_request_context,
        mask_sensitive_data,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        renderer: structlog.typing.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger("airflow_lite")
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(console_handler)
    uvicorn_logger.propagate = False
