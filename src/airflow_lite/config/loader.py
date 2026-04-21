"""SettingsLoader — 다중 소스(YAML + SQLite) 설정 로딩 전담.

Settings.load() 의 단일 메서드 책임을 분리한다.
"""

from __future__ import annotations

import yaml
from pathlib import Path

from airflow_lite.storage.crypto import Crypto

from .settings import (
    AlertingConfig,
    ApiConfig,
    DefaultConfig,
    ExportConfig,
    MartConfig,
    OracleConfig,
    PipelineConfig,
    SchedulerConfig,
    Settings,
    StorageConfig,
    WebUIConfig,
    _build_pipeline_configs,
    _load_oracle_from_sqlite,
    _load_pipelines_from_sqlite,
    _coerce_int,
    _coerce_int_fields,
    RetryDefaults,
    ParquetDefaults,
)


class SettingsLoader:
    """YAML + SQLite 다중 소스 설정 로딩을 오케스트레이션."""

    def __init__(self, config_path: str):
        self.config_path = config_path

    def load(self) -> Settings:
        raw = self._load_yaml()
        data = self._substitute(raw)
        storage = self._build_storage(data)
        crypto = self._resolve_crypto(data)
        oracle = self._load_oracle(data, storage, crypto)
        defaults = self._build_defaults(data)
        pipelines = self._load_pipelines(data, storage)
        api, alerting, mart, export, scheduler, webui = self._build_sections(data)
        return Settings(
            oracle=oracle,
            storage=storage,
            defaults=defaults,
            pipelines=pipelines,
            api=api,
            alerting=alerting,
            mart=mart,
            export=export,
            scheduler=scheduler,
            webui=webui,
            crypto=crypto,
        )

    def _load_yaml(self) -> dict:
        path = Path(self.config_path)
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @staticmethod
    def _substitute(data: dict) -> dict:
        from .settings import _walk_and_substitute
        return _walk_and_substitute(data)

    @staticmethod
    def _build_storage(data: dict) -> StorageConfig:
        return StorageConfig(**data["storage"])

    @staticmethod
    def _resolve_crypto(data: dict) -> Crypto:
        security_data = data.get("security") or {}
        return Crypto.from_key_or_env(security_data.get("fernet_key"))

    @staticmethod
    def _load_oracle(data: dict, storage: StorageConfig, crypto: Crypto) -> OracleConfig | None:
        oracle = _load_oracle_from_sqlite(storage.sqlite_path, crypto)
        if oracle is None and "oracle" in data:
            oracle_data = _coerce_int_fields(dict(data["oracle"]), ("port",), "oracle")
            oracle = OracleConfig(**oracle_data)
        return oracle

    @staticmethod
    def _build_defaults(data: dict) -> DefaultConfig:
        defaults_data = data.get("defaults", {})
        retry_data = _coerce_int_fields(
            dict(defaults_data.get("retry", {})),
            ("max_attempts", "min_wait_seconds", "max_wait_seconds"),
            "defaults.retry",
        )
        retry = RetryDefaults(**retry_data)
        parquet = ParquetDefaults(**defaults_data.get("parquet", {}))
        return DefaultConfig(
            chunk_size=_coerce_int(defaults_data.get("chunk_size", 10000), "defaults.chunk_size"),
            retry=retry,
            parquet=parquet,
        )

    @staticmethod
    def _load_pipelines(data: dict, storage: StorageConfig) -> list[PipelineConfig] | None:
        pipelines = _load_pipelines_from_sqlite(storage.sqlite_path)
        if pipelines is None:
            pipelines = _build_pipeline_configs(data.get("pipelines", []))
        return pipelines

    @staticmethod
    def _build_sections(data: dict):
        from .builders import (
            build_alerting_config,
            build_api_config,
            build_export_config,
            build_mart_config,
            build_scheduler_config,
            build_webui_config,
        )
        return (
            build_api_config(data.get("api")),
            build_alerting_config(data.get("alerting")),
            build_mart_config(data.get("mart")),
            build_export_config(data.get("export")),
            build_scheduler_config(data.get("scheduler")),
            build_webui_config(data.get("webui")),
        )
