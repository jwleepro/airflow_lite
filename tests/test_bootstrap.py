from pathlib import Path
from unittest.mock import MagicMock

from airflow_lite.bootstrap import (
    CONFIG_PATH_ENV_VAR,
    build_runtime_services,
    get_api_bind,
    get_mart_database_path,
    load_settings,
    resolve_config_path,
)
from airflow_lite.config.settings import (
    ApiConfig,
    DefaultConfig,
    ExportConfig,
    MartConfig,
    OracleConfig,
    PipelineConfig,
    Settings,
    StorageConfig,
)


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        oracle=OracleConfig("localhost", 1521, "ORCL", "scott", "tiger"),
        storage=StorageConfig(
            parquet_base_path=str(tmp_path / "parquet"),
            sqlite_path=str(tmp_path / "runtime.db"),
            log_path=str(tmp_path / "logs"),
        ),
        defaults=DefaultConfig(),
        pipelines=[
            PipelineConfig(
                name="pipe_a",
                table="TABLE_A",
                partition_column="DATE_COL",
                strategy="full",
                schedule="0 2 * * *",
            )
        ],
        api=ApiConfig(host="127.0.0.1", port=8100),
        mart=MartConfig(enabled=False, root_path=str(tmp_path / "mart")),
        export=ExportConfig(root_path=str(tmp_path / "exports")),
    )


def test_resolve_config_path_prefers_cli_arg(monkeypatch):
    monkeypatch.setenv(CONFIG_PATH_ENV_VAR, "from-env.yaml")

    resolved = resolve_config_path("from-cli.yaml")

    assert resolved == "from-cli.yaml"


def test_resolve_config_path_uses_env_var(monkeypatch):
    monkeypatch.setenv(CONFIG_PATH_ENV_VAR, "from-env.yaml")

    resolved = resolve_config_path()

    assert resolved == "from-env.yaml"


def test_load_settings_uses_resolved_path(monkeypatch):
    mock_settings = MagicMock(name="settings")
    monkeypatch.setenv(CONFIG_PATH_ENV_VAR, "env-pipelines.yaml")
    monkeypatch.setattr("airflow_lite.bootstrap.Settings.load", lambda path: mock_settings)

    config_path, settings = load_settings()

    assert config_path == "env-pipelines.yaml"
    assert settings is mock_settings


def test_build_runtime_services_uses_export_root_path(tmp_path):
    settings = _make_settings(tmp_path)
    runner_factory = MagicMock(name="runner_factory")

    runtime = build_runtime_services(
        settings,
        "dummy_path.yaml",
        runner_factory_builder=lambda current_settings, run_repo, step_repo: runner_factory,
    )

    assert runtime.analytics_export_service.root_path == Path(settings.export.root_path)
    assert runtime.analytics_query_service.database_path == get_mart_database_path(settings)


def test_get_api_bind_returns_host_and_port(tmp_path):
    settings = _make_settings(tmp_path)

    host, port = get_api_bind(settings)

    assert host == "127.0.0.1"
    assert port == 8100
