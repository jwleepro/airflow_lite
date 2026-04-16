import pytest
import sqlite3
from unittest.mock import mock_open, patch
from airflow_lite.config.settings import (
    _substitute_env_vars,
    _walk_and_substitute,
    AlertingConfig,
    EmailChannelConfig,
    ExportConfig,
    MartConfig,
    SchedulerConfig,
    WebhookChannelConfig,
    WebUIConfig,
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

    def test_load_coerces_numeric_env_values(self, tmp_path, monkeypatch):
        config_path = tmp_path / "pipelines.yaml"
        config_path.write_text(
            """\
oracle:
  host: ${ORACLE_HOST}
  port: ${ORACLE_PORT}
  service_name: ${ORACLE_SERVICE}
  user: ${ORACLE_USER}
  password: ${ORACLE_PASSWORD}

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

defaults:
  chunk_size: ${DEFAULT_CHUNK_SIZE}

api:
  port: ${API_PORT}

pipelines:
  - name: "test_pipeline"
    table: "TEST_TABLE"
    partition_column: "DATE_COL"
    strategy: "full"
    schedule: "0 2 * * *"
    chunk_size: ${PIPELINE_CHUNK_SIZE}
""",
            encoding="utf-8",
        )

        monkeypatch.setenv("ORACLE_HOST", "localhost")
        monkeypatch.setenv("ORACLE_PORT", "1521")
        monkeypatch.setenv("ORACLE_SERVICE", "ORCL")
        monkeypatch.setenv("ORACLE_USER", "scott")
        monkeypatch.setenv("ORACLE_PASSWORD", "tiger")
        monkeypatch.setenv("DEFAULT_CHUNK_SIZE", "20000")
        monkeypatch.setenv("API_PORT", "8100")
        monkeypatch.setenv("PIPELINE_CHUNK_SIZE", "40000")

        settings = Settings.load(str(config_path))

        assert settings.oracle.port == 1521
        assert isinstance(settings.oracle.port, int)
        assert settings.defaults.chunk_size == 20000
        assert settings.api.port == 8100
        assert settings.pipelines[0].chunk_size == 40000

    def test_load_uses_sqlite_oracle_and_pipelines_when_available(self, tmp_path):
        sqlite_path = tmp_path / "airflow_lite.db"
        with sqlite3.connect(sqlite_path) as connection:
            connection.execute(
                """
                CREATE TABLE connections (
                    conn_id TEXT PRIMARY KEY,
                    conn_type TEXT NOT NULL,
                    host TEXT,
                    port INTEGER,
                    schema TEXT,
                    login TEXT,
                    password TEXT,
                    extra TEXT,
                    description TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE pipeline_configs (
                    name TEXT PRIMARY KEY,
                    source_table TEXT NOT NULL,
                    partition_column TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    chunk_size INTEGER,
                    columns TEXT,
                    incremental_key TEXT
                )
                """
            )
            connection.execute(
                """
                INSERT INTO connections
                (conn_id, conn_type, host, port, schema, login, password)
                VALUES ('oracle', 'oracle', 'db.internal', 1521, 'ORCL', 'scott', 'tiger')
                """
            )
            connection.execute(
                """
                INSERT INTO pipeline_configs
                (name, source_table, partition_column, strategy, schedule, chunk_size, columns, incremental_key)
                VALUES
                ('production_log', 'PRODUCTION_LOG', 'LOG_DATE', 'incremental', '0 */6 * * *', 5000, 'LOG_ID, LOG_DATE, STATUS', 'UPDATED_AT')
                """
            )
            connection.commit()

        config_path = tmp_path / "pipelines.yaml"
        config_path.write_text(
            f"""\
storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "{sqlite_path.as_posix()}"
  log_path: "/tmp/logs"
""",
            encoding="utf-8",
        )

        settings = Settings.load(str(config_path))

        assert settings.oracle.host == "db.internal"
        assert settings.oracle.user == "scott"
        assert settings.oracle.password == "tiger"
        assert len(settings.pipelines) == 1
        assert settings.pipelines[0].name == "production_log"
        assert settings.pipelines[0].columns == ["LOG_ID", "LOG_DATE", "STATUS"]
        assert settings.pipelines[0].incremental_key == "UPDATED_AT"

    def test_load_falls_back_to_yaml_pipelines_when_sqlite_pipeline_table_empty(self, tmp_path):
        sqlite_path = tmp_path / "airflow_lite.db"
        with sqlite3.connect(sqlite_path) as connection:
            connection.execute(
                """
                CREATE TABLE connections (
                    conn_id TEXT PRIMARY KEY,
                    conn_type TEXT NOT NULL,
                    host TEXT,
                    port INTEGER,
                    schema TEXT,
                    login TEXT,
                    password TEXT,
                    extra TEXT,
                    description TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE pipeline_configs (
                    name TEXT PRIMARY KEY,
                    source_table TEXT NOT NULL,
                    partition_column TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    chunk_size INTEGER,
                    columns TEXT,
                    incremental_key TEXT
                )
                """
            )
            connection.execute(
                """
                INSERT INTO connections
                (conn_id, conn_type, host, port, schema, login, password)
                VALUES ('oracle', 'oracle', 'db.internal', 1521, 'ORCL', 'scott', 'tiger')
                """
            )
            connection.commit()

        config_path = tmp_path / "pipelines.yaml"
        config_path.write_text(
            f"""\
storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "{sqlite_path.as_posix()}"
  log_path: "/tmp/logs"

pipelines:
  - name: "from_yaml"
    table: "OPS_TABLE"
    partition_column: "DATE_COL"
    strategy: "full"
    schedule: "0 2 * * *"
""",
            encoding="utf-8",
        )

        settings = Settings.load(str(config_path))

        assert [pipeline.name for pipeline in settings.pipelines] == ["from_yaml"]


class TestAlertingConfig:
    """Settings.load()의 alerting 섹션 파싱 검증."""

    def _make_yaml(self, tmp_path, oracle_content, alerting_content=""):
        content = f"""\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []
{alerting_content}
"""
        yaml_file = tmp_path / "pipelines.yaml"
        yaml_file.write_text(content, encoding="utf-8")
        return yaml_file

    def test_load_email_channel(self, tmp_path):
        yaml_file = self._make_yaml(tmp_path, "", """\
alerting:
  channels:
    - type: "email"
      smtp_host: "mail.internal"
      smtp_port: 25
      recipients:
        - "ops@company.com"
  triggers:
    on_failure: true
    on_success: false
""")
        settings = Settings.load(str(yaml_file))
        assert len(settings.alerting.channels) == 1
        ch = settings.alerting.channels[0]
        assert isinstance(ch, EmailChannelConfig)
        assert ch.smtp_host == "mail.internal"
        assert ch.smtp_port == 25
        assert ch.recipients == ["ops@company.com"]

    def test_load_webhook_channel(self, tmp_path):
        yaml_file = self._make_yaml(tmp_path, "", """\
alerting:
  channels:
    - type: "webhook"
      url: "https://messenger.internal/webhook/abc"
""")
        settings = Settings.load(str(yaml_file))
        assert len(settings.alerting.channels) == 1
        ch = settings.alerting.channels[0]
        assert isinstance(ch, WebhookChannelConfig)
        assert ch.url == "https://messenger.internal/webhook/abc"

    def test_load_multiple_channels(self, tmp_path):
        yaml_file = self._make_yaml(tmp_path, "", """\
alerting:
  channels:
    - type: "email"
      smtp_host: "mail.internal"
      recipients: ["ops@company.com"]
    - type: "webhook"
      url: "https://messenger.internal/webhook/abc"
""")
        settings = Settings.load(str(yaml_file))
        assert len(settings.alerting.channels) == 2
        assert isinstance(settings.alerting.channels[0], EmailChannelConfig)
        assert isinstance(settings.alerting.channels[1], WebhookChannelConfig)

    def test_load_triggers_on_failure_true(self, tmp_path):
        yaml_file = self._make_yaml(tmp_path, "", """\
alerting:
  channels: []
  triggers:
    on_failure: true
    on_success: false
""")
        settings = Settings.load(str(yaml_file))
        assert settings.alerting.triggers.on_failure is True
        assert settings.alerting.triggers.on_success is False

    def test_load_triggers_defaults_when_omitted(self, tmp_path):
        yaml_file = self._make_yaml(tmp_path, "", """\
alerting:
  channels: []
""")
        settings = Settings.load(str(yaml_file))
        assert settings.alerting.triggers.on_failure is True
        assert settings.alerting.triggers.on_success is False

    def test_load_no_alerting_section_uses_defaults(self, tmp_path):
        yaml_file = self._make_yaml(tmp_path, "")
        settings = Settings.load(str(yaml_file))
        assert isinstance(settings.alerting, AlertingConfig)
        assert settings.alerting.channels == []
        assert settings.alerting.triggers.on_failure is True

    def test_load_unknown_channel_type_raises(self, tmp_path):
        yaml_file = self._make_yaml(tmp_path, "", """\
alerting:
  channels:
    - type: "sms"
      phone: "+82-10-1234-5678"
""")
        with pytest.raises(ValueError, match="알 수 없는 알림 채널 타입"):
            Settings.load(str(yaml_file))

    def test_load_smtp_port_coercion(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SMTP_PORT", "587")
        yaml_file = self._make_yaml(tmp_path, "", """\
alerting:
  channels:
    - type: "email"
      smtp_host: "mail.internal"
      smtp_port: ${SMTP_PORT}
      recipients: ["ops@company.com"]
""")
        settings = Settings.load(str(yaml_file))
        ch = settings.alerting.channels[0]
        assert ch.smtp_port == 587
        assert isinstance(ch.smtp_port, int)


class TestMartConfig:
    def test_load_mart_config(self):
        config_text = """\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []

mart:
  enabled: true
  root_path: "/tmp/mart"
  refresh_on_success: true
  pipeline_datasets:
    production_log: "mes_ops"
"""

        with patch("builtins.open", mock_open(read_data=config_text)):
            settings = Settings.load("pipelines.yaml")

        assert isinstance(settings.mart, MartConfig)
        assert settings.mart.enabled is True
        assert settings.mart.root_path == "/tmp/mart"
        assert settings.mart.pipeline_datasets["production_log"] == "mes_ops"

    def test_load_export_config(self):
        config_text = """\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []

export:
  retention_hours: 48
  cleanup_cooldown_seconds: 120
  root_path: "/tmp/exports"
"""

        with patch("builtins.open", mock_open(read_data=config_text)):
            settings = Settings.load("pipelines.yaml")

        assert isinstance(settings.export, ExportConfig)
        assert settings.export.retention_hours == 48
        assert settings.export.cleanup_cooldown_seconds == 120
        assert settings.export.root_path == "/tmp/exports"

    def test_export_config_defaults(self):
        config_text = """\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []
"""

        with patch("builtins.open", mock_open(read_data=config_text)):
            settings = Settings.load("pipelines.yaml")

        assert isinstance(settings.export, ExportConfig)
        assert settings.export.retention_hours == 72
        assert settings.export.cleanup_cooldown_seconds == 300

    def test_load_extended_export_scheduler_and_webui_config(self):
        config_text = """\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []

export:
  root_path: "/tmp/exports"
  max_workers: 4
  rows_per_batch: 4096
  parquet_compression: "zstd"
  zip_compression: "stored"

scheduler:
  coalesce: false
  max_instances: 2
  misfire_grace_time_seconds: 120
  dispatch_max_workers: 3

webui:
  monitor_refresh_seconds: 15
  analytics_refresh_seconds: 45
  exports_active_refresh_seconds: 5
  exports_idle_refresh_seconds: 25
  recent_runs_limit: 12
  detail_preview_page_size: 6
  analytics_export_jobs_limit: 4
  export_jobs_page_limit: 20
  error_message_max_length: 80
  default_dataset: "custom_ops"
  default_dashboard_id: "operations_overview"
  default_language: "ko"
"""

        with patch("builtins.open", mock_open(read_data=config_text)):
            settings = Settings.load("pipelines.yaml")

        assert settings.export.max_workers == 4
        assert settings.export.rows_per_batch == 4096
        assert settings.export.parquet_compression == "zstd"
        assert settings.export.zip_compression == "stored"
        assert isinstance(settings.scheduler, SchedulerConfig)
        assert settings.scheduler.coalesce is False
        assert settings.scheduler.max_instances == 2
        assert settings.scheduler.misfire_grace_time_seconds == 120
        assert settings.scheduler.dispatch_max_workers == 3
        assert isinstance(settings.webui, WebUIConfig)
        assert settings.webui.monitor_refresh_seconds == 15
        assert settings.webui.analytics_refresh_seconds == 45
        assert settings.webui.default_dataset == "custom_ops"
        assert settings.webui.default_language == "ko"

    def test_load_coerces_scheduler_dispatch_max_workers_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DISPATCH_MAX_WORKERS", "4")
        config_text = """\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []

scheduler:
  dispatch_max_workers: ${DISPATCH_MAX_WORKERS}
"""

        with patch("builtins.open", mock_open(read_data=config_text)):
            settings = Settings.load("pipelines.yaml")

        assert settings.scheduler.dispatch_max_workers == 4
        assert isinstance(settings.scheduler.dispatch_max_workers, int)

    def test_scheduler_and_webui_config_defaults(self):
        config_text = """\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []
"""

        with patch("builtins.open", mock_open(read_data=config_text)):
            settings = Settings.load("pipelines.yaml")

        assert isinstance(settings.scheduler, SchedulerConfig)
        assert settings.scheduler.max_instances == 1
        assert isinstance(settings.webui, WebUIConfig)
        assert settings.webui.default_dataset == "mes_ops"
        assert settings.webui.export_jobs_page_limit == 50
        assert settings.webui.default_language == "en"

    def test_webui_default_language_rejects_unsupported_values(self):
        config_text = """\
oracle:
  host: localhost
  port: 1521
  service_name: ORCL
  user: scott
  password: tiger

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

pipelines: []

webui:
  default_language: "jp"
"""

        with patch("builtins.open", mock_open(read_data=config_text)):
            with pytest.raises(ValueError, match="지원되지 않는 언어 값"):
                Settings.load("pipelines.yaml")
