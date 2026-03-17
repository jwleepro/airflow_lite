import pytest
import os
from airflow_lite.config.settings import (
    _substitute_env_vars,
    _walk_and_substitute,
    Settings,
)


class TestSubstituteEnvVars:
    def test_substitutes_single_var(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "hello")
        assert _substitute_env_vars("${MY_VAR}") == "hello"

    def test_substitutes_multiple_vars(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "5432")
        result = _substitute_env_vars("${HOST}:${PORT}")
        assert result == "localhost:5432"

    def test_no_substitution_needed(self):
        assert _substitute_env_vars("plain_value") == "plain_value"

    def test_raises_on_missing_var(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        with pytest.raises(EnvironmentError) as exc_info:
            _substitute_env_vars("${MISSING_VAR}")
        assert "MISSING_VAR" in str(exc_info.value)
        assert "설정되지 않았습니다" in str(exc_info.value)


class TestWalkAndSubstitute:
    def test_substitutes_in_dict(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "db.internal")
        data = {"host": "${DB_HOST}", "port": 5432}
        result = _walk_and_substitute(data)
        assert result == {"host": "db.internal", "port": 5432}

    def test_substitutes_in_list(self, monkeypatch):
        monkeypatch.setenv("ITEM", "value")
        result = _walk_and_substitute(["${ITEM}", "literal"])
        assert result == ["value", "literal"]

    def test_substitutes_nested(self, monkeypatch):
        monkeypatch.setenv("SECRET", "s3cr3t")
        data = {"outer": {"inner": "${SECRET}"}}
        result = _walk_and_substitute(data)
        assert result["outer"]["inner"] == "s3cr3t"

    def test_non_string_passthrough(self):
        assert _walk_and_substitute(42) == 42
        assert _walk_and_substitute(3.14) == 3.14
        assert _walk_and_substitute(None) is None


class TestSettingsLoad:
    def test_load_success(self, sample_yaml, oracle_env_vars):
        settings = Settings.load(str(sample_yaml))

        assert settings.oracle.host == "localhost"
        assert settings.oracle.port == 1521
        assert settings.oracle.service_name == "ORCL"
        assert settings.oracle.user == "scott"
        assert settings.oracle.password == "tiger"

        assert settings.storage.parquet_base_path == "/tmp/parquet"
        assert settings.storage.sqlite_path == "/tmp/airflow_lite.db"

        assert settings.defaults.chunk_size == 10000
        assert settings.defaults.retry.max_attempts == 3
        assert settings.defaults.parquet.compression == "snappy"

        assert len(settings.pipelines) == 1
        assert settings.pipelines[0].name == "test_pipeline"
        assert settings.pipelines[0].strategy == "full"

    def test_load_missing_env_var(self, sample_yaml, monkeypatch):
        monkeypatch.delenv("ORACLE_HOST", raising=False)
        with pytest.raises(EnvironmentError) as exc_info:
            Settings.load(str(sample_yaml))
        assert "ORACLE_HOST" in str(exc_info.value)
