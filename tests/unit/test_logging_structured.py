"""Tests for structlog integration."""

import logging
import re

import structlog

from airflow_lite.logging_config import structured as structured_logging


def test_setup_structlog_file_log_has_no_ansi_escape(tmp_path):
    root_logger = logging.getLogger("airflow_lite")
    uvicorn_logger = logging.getLogger("uvicorn")

    original_root_handlers = list(root_logger.handlers)
    original_root_level = root_logger.level
    original_uvicorn_handlers = list(uvicorn_logger.handlers)
    original_uvicorn_propagate = uvicorn_logger.propagate
    original_configured = structured_logging._logging_configured

    try:
        root_logger.handlers.clear()
        uvicorn_logger.handlers.clear()
        structured_logging._logging_configured = False

        structured_logging.setup_structlog(str(tmp_path), json_output=False)
        structlog.get_logger("airflow_lite.test").info("ansi_check", flag=True)

        for handler in root_logger.handlers:
            handler.flush()

        log_text = (tmp_path / "airflow_lite.log").read_text(encoding="utf-8")
        assert "\x1b[" not in log_text
        assert "ansi_check" in log_text
        line = next((row for row in log_text.splitlines() if "ansi_check" in row), "")
        assert re.search(
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \[INFO\] airflow_lite\.test - ansi_check",
            line,
        )
    finally:
        for handler in root_logger.handlers:
            try:
                handler.close()
            except Exception:
                pass
        root_logger.handlers.clear()
        root_logger.handlers.extend(original_root_handlers)
        root_logger.setLevel(original_root_level)

        for handler in uvicorn_logger.handlers:
            try:
                handler.close()
            except Exception:
                pass
        uvicorn_logger.handlers.clear()
        uvicorn_logger.handlers.extend(original_uvicorn_handlers)
        uvicorn_logger.propagate = original_uvicorn_propagate

        structured_logging._logging_configured = original_configured
