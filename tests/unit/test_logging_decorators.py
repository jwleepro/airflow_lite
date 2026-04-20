"""Tests for logging decorators."""

import logging

import pytest

from airflow_lite.logging_config.decorators import (
    log_db_operation,
    log_execution,
    _mask_sensitive,
)


class TestMaskSensitive:
    def test_masks_password(self):
        result = _mask_sensitive({"password": "secret123"})
        assert result["password"] == "***"

    def test_masks_token(self):
        result = _mask_sensitive({"api_token": "abc123"})
        assert result["api_token"] == "***"

    def test_preserves_normal_keys(self):
        result = _mask_sensitive({"name": "test", "count": 42})
        assert result == {"name": "test", "count": 42}

    def test_case_insensitive(self):
        result = _mask_sensitive({"PASSWORD": "secret", "ApiToken": "abc"})
        assert result["PASSWORD"] == "***"
        assert result["ApiToken"] == "***"


class TestLogExecution:
    def test_returns_result(self):
        @log_execution("test.logger")
        def add(a, b):
            return a + b

        assert add(1, 2) == 3

    def test_reraises_exception(self):
        @log_execution("test.logger")
        def fail():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            fail()

    def test_logs_on_error(self, caplog):
        @log_execution("test.logger")
        def fail():
            raise RuntimeError("boom")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                fail()

        assert any("function_error" in str(r.message) for r in caplog.records)
        assert any("RuntimeError" in str(r.message) for r in caplog.records)

    def test_logs_entry_exit(self, caplog):
        @log_execution("test.logger", level=logging.INFO)
        def noop():
            return "done"

        with caplog.at_level(logging.INFO):
            result = noop()

        assert result == "done"
        messages = [str(r.message) for r in caplog.records]
        assert any("function_enter" in m for m in messages)
        assert any("function_exit" in m for m in messages)


class TestLogDbOperation:
    def test_returns_result(self):
        @log_db_operation("test_table")
        def query():
            return [1, 2, 3]

        assert query() == [1, 2, 3]

    def test_logs_operation(self, caplog):
        @log_db_operation("test_table")
        def create_item():
            return {"id": 1}

        with caplog.at_level(logging.DEBUG):
            result = create_item()

        assert result == {"id": 1}

    def test_logs_error_on_failure(self, caplog):
        @log_db_operation("test_table")
        def fail_query():
            raise Exception("DB error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception):
                fail_query()

        assert any("db_operation_error" in str(r.message) for r in caplog.records)
