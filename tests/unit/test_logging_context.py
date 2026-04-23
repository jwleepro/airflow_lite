"""Tests for logging context management."""

from airflow_lite.logging_config.context import (
    bind_pipeline_context,
    bind_request_context,
    clear_request_context,
    get_context_dict,
    get_request_id,
    pipeline_name_var,
    request_id_var,
)


class TestRequestId:
    def test_generates_id_when_none(self):
        clear_request_context()
        rid = get_request_id()
        assert rid is not None
        assert len(rid) == 8

    def test_returns_existing_id(self):
        clear_request_context()
        rid1 = get_request_id()
        rid2 = get_request_id()
        assert rid1 == rid2


class TestBindRequestContext:
    def test_binds_request_id(self):
        clear_request_context()
        bind_request_context(request_id="test123")
        assert request_id_var.get() == "test123"

    def test_binds_pipeline_name(self):
        clear_request_context()
        bind_request_context(request_id="r1", pipeline_name="my_pipeline")
        assert pipeline_name_var.get() == "my_pipeline"


class TestBindPipelineContext:
    def test_binds_pipeline(self):
        clear_request_context()
        bind_pipeline_context("daily_etl")
        assert pipeline_name_var.get() == "daily_etl"


class TestClearRequestContext:
    def test_clears_all(self):
        bind_request_context(request_id="r1", pipeline_name="p1", user_id="u1")
        clear_request_context()

        ctx = get_context_dict()
        assert ctx["request_id"] is None
        assert ctx["pipeline"] is None
        assert ctx["user_id"] is None


class TestGetContextDict:
    def test_returns_dict(self):
        clear_request_context()
        bind_request_context(request_id="abc", pipeline_name="test")
        ctx = get_context_dict()

        assert ctx["request_id"] == "abc"
        assert ctx["pipeline"] == "test"
