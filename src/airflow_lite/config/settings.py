import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from airflow_lite.pipeline_config_validation import (
    coerce_source_query_from_mapping,
    validate_data_interval_schedule,
)
from airflow_lite.storage._helpers import decode_password
from airflow_lite.storage._sqlite_schema import table_exists
from airflow_lite.storage.crypto import Crypto
from ._coerce import coerce_int as _coerce_int

# 환경변수 치환 패턴: ${VAR_NAME}
ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _substitute_env_vars(value: str) -> str:
    """YAML 문자열 내 ${VAR_NAME} 패턴을 os.environ에서 조회하여 치환.
    미설정 시 EnvironmentError를 발생시켜 시작 단계에서 명확하게 실패."""
    def replacer(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise EnvironmentError(
                f"환경변수 '{var_name}'이 설정되지 않았습니다. "
                f"YAML 설정에서 ${{{var_name}}}을 참조하고 있습니다."
            )
        return env_value
    return ENV_VAR_PATTERN.sub(replacer, value)


def _walk_and_substitute(obj):
    """YAML 파싱 결과를 재귀 순회하며 문자열 값의 환경변수를 치환."""
    if isinstance(obj, str):
        return _substitute_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: _walk_and_substitute(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_walk_and_substitute(item) for item in obj]
    return obj


@dataclass
class OracleConfig:
    host: str
    port: int
    service_name: str
    user: str
    password: str
    oracle_home: str | None = None  # oracledb thick mode용 Oracle Client 경로


@dataclass
class StorageConfig:
    parquet_base_path: str
    sqlite_path: str
    log_path: str


@dataclass
class RetryDefaults:
    max_attempts: int = 3
    min_wait_seconds: int = 4
    max_wait_seconds: int = 60


@dataclass
class ParquetDefaults:
    compression: str = "snappy"


@dataclass
class DefaultConfig:
    chunk_size: int = 10000
    retry: RetryDefaults = field(default_factory=RetryDefaults)
    parquet: ParquetDefaults = field(default_factory=ParquetDefaults)


@dataclass
class PipelineConfig:
    name: str
    table: str
    paused: bool = False
    source_where_template: str | None = None
    source_bind_params: dict[str, Any] = field(default_factory=dict)
    strategy: str = "full"  # "full" | "incremental"
    schedule: str = "0 2 * * *"
    chunk_size: int | None = None
    columns: list[str] | None = None
    incremental_key: str | None = None


@dataclass
class ApiConfig:
    allowed_origins: list = field(default_factory=lambda: ["http://10.0.0.*", "http://192.168.1.*"])
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class EmailChannelConfig:
    type: str
    smtp_host: str
    smtp_port: int = 25
    sender: str = "airflow-lite@company.com"
    recipients: list = field(default_factory=list)


@dataclass
class WebhookChannelConfig:
    type: str
    url: str
    timeout: float = 10.0


@dataclass
class AlertingTriggersConfig:
    on_failure: bool = True
    on_success: bool = False


@dataclass
class AlertingConfig:
    channels: list = field(default_factory=list)
    triggers: AlertingTriggersConfig = field(default_factory=AlertingTriggersConfig)


@dataclass
class ExportConfig:
    retention_hours: int = 72
    cleanup_cooldown_seconds: int = 300
    root_path: str = "data/exports"
    max_workers: int = 2
    rows_per_batch: int = 10000
    parquet_compression: str = "snappy"
    zip_compression: str = "deflated"


@dataclass
class SchedulerConfig:
    coalesce: bool = True
    max_instances: int = 1
    misfire_grace_time_seconds: int = 3600
    dispatch_max_workers: int = 2


@dataclass
class WebUIConfig:
    monitor_refresh_seconds: int = 30
    analytics_refresh_seconds: int = 60
    exports_active_refresh_seconds: int = 10
    exports_idle_refresh_seconds: int = 30
    recent_runs_limit: int = 25
    detail_preview_page_size: int = 8
    analytics_export_jobs_limit: int = 8
    export_jobs_page_limit: int = 50
    error_message_max_length: int = 120
    default_dataset: str = "mes_ops"
    default_dashboard_id: str = "operations_overview"
    default_language: str = "en"


@dataclass
class MartConfig:
    enabled: bool = False
    root_path: str = "data/mart"
    database_filename: str = "analytics.duckdb"
    refresh_on_success: bool = True
    pipeline_datasets: dict[str, str] = field(default_factory=dict)

def _build_pipeline_configs(pipeline_items: list[dict]) -> list[PipelineConfig]:
    pipelines: list[PipelineConfig] = []
    for index, pipeline_data in enumerate(pipeline_items, start=1):
        pipeline_values = dict(pipeline_data)
        pipeline_values["schedule"] = validate_data_interval_schedule(
            pipeline_values.get("schedule", "0 2 * * *")
        )
        if pipeline_values.get("chunk_size") is not None:
            pipeline_values["chunk_size"] = _coerce_int(
                pipeline_values["chunk_size"], f"pipelines[{index}].chunk_size"
            )
        (
            pipeline_values["source_where_template"],
            pipeline_values["source_bind_params"],
        ) = coerce_source_query_from_mapping(
            pipeline_values,
            strategy=pipeline_values.get("strategy", "full"),
        )
        pipeline_values.pop("partition_column", None)
        pipeline_values.pop("partition_year_column", None)
        pipeline_values.pop("partition_month_column", None)
        pipeline_values["columns"] = _normalize_columns(pipeline_values.get("columns"))
        pipelines.append(PipelineConfig(**pipeline_values))
    return pipelines


def _normalize_columns(value) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return normalized or None
    if isinstance(value, str):
        normalized = [item.strip() for item in value.split(",") if item and item.strip()]
        return normalized or None
    return None


def _load_oracle_from_sqlite(sqlite_path: str, crypto: Crypto) -> OracleConfig | None:
    db_path = Path(sqlite_path)
    if not db_path.exists():
        return None

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        if not table_exists(connection, "connections"):
            return None
        row = connection.execute(
            """
            SELECT host, port, schema, login, password
            FROM connections
            WHERE conn_id = 'oracle'
            """
        ).fetchone()
        if row is None:
            return None
        if not row["host"] or not row["schema"] or not row["login"] or row["password"] is None:
            return None
        return OracleConfig(
            host=row["host"],
            port=_coerce_int(row["port"], "oracle.port"),
            service_name=row["schema"],
            user=row["login"],
            password=decode_password(row["password"], crypto) or "",
        )
    finally:
        connection.close()


class Settings:
    """YAML 설정 로더. 환경변수 ${VAR} 참조를 자동 치환한다."""

    def __init__(
        self,
        oracle,
        storage,
        defaults,
        pipelines,
        api=None,
        alerting=None,
        mart=None,
        export=None,
        scheduler=None,
        webui=None,
        crypto: Crypto | None = None,
    ):
        self.oracle = oracle
        self.storage = storage
        self.defaults = defaults
        self.pipelines = pipelines
        self.api = api or ApiConfig()
        self.alerting = alerting or AlertingConfig()
        self.mart = mart or MartConfig()
        self.export = export or ExportConfig()
        self.scheduler = scheduler or SchedulerConfig()
        self.webui = webui or WebUIConfig()
        self.crypto = crypto or Crypto.from_env()

    @classmethod
    def load(cls, config_path: str) -> "Settings":
        from .loader import SettingsLoader
        return SettingsLoader(config_path).load()
