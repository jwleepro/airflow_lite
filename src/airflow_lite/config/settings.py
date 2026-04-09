import os
import re
import sqlite3
import yaml
from dataclasses import dataclass, field
from pathlib import Path

from airflow_lite.i18n import require_supported_language
from airflow_lite.storage.crypto import Crypto

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
    partition_column: str
    strategy: str  # "full" | "incremental"
    schedule: str
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


def _coerce_int(value: int | str, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"정수 필드 '{field_name}'의 값이 올바르지 않습니다: {value!r}") from exc


def _coerce_int_fields(values: dict, field_names: tuple[str, ...], prefix: str) -> dict:
    coerced = dict(values)
    for field_name in field_names:
        if field_name in coerced:
            coerced[field_name] = _coerce_int(coerced[field_name], f"{prefix}.{field_name}")
    return coerced


def _build_optional_config(section_data, config_cls, *, prefix: str, int_fields: tuple[str, ...] = ()):
    if not section_data:
        return config_cls()
    values = _coerce_int_fields(dict(section_data), int_fields, prefix)
    return config_cls(**values)


def _build_pipeline_configs(pipeline_items: list[dict]) -> list[PipelineConfig]:
    pipelines: list[PipelineConfig] = []
    for index, pipeline_data in enumerate(pipeline_items, start=1):
        pipeline_values = dict(pipeline_data)
        if pipeline_values.get("chunk_size") is not None:
            pipeline_values["chunk_size"] = _coerce_int(
                pipeline_values["chunk_size"], f"pipelines[{index}].chunk_size"
            )
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


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _decode_connection_password(raw_password: str | None) -> str | None:
    if raw_password is None:
        return None
    decrypted = Crypto.decrypt(raw_password)
    if decrypted == "---DECRYPTION_FAILED---":
        return raw_password
    return decrypted


def _load_oracle_from_sqlite(sqlite_path: str) -> OracleConfig | None:
    db_path = Path(sqlite_path)
    if not db_path.exists():
        return None

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        if not _table_exists(connection, "connections"):
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
            password=_decode_connection_password(row["password"]) or "",
        )
    finally:
        connection.close()


def _load_pipelines_from_sqlite(sqlite_path: str) -> list[PipelineConfig] | None:
    db_path = Path(sqlite_path)
    if not db_path.exists():
        return None

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        if not _table_exists(connection, "pipeline_configs"):
            return None
        rows = connection.execute(
            """
            SELECT
                name,
                source_table,
                partition_column,
                strategy,
                schedule,
                chunk_size,
                columns,
                incremental_key
            FROM pipeline_configs
            ORDER BY name
            """
        ).fetchall()
        if not rows:
            return None
        return [
            PipelineConfig(
                name=row["name"],
                table=row["source_table"],
                partition_column=row["partition_column"],
                strategy=row["strategy"],
                schedule=row["schedule"],
                chunk_size=row["chunk_size"],
                columns=_normalize_columns(row["columns"]),
                incremental_key=row["incremental_key"],
            )
            for row in rows
        ]
    finally:
        connection.close()


def _build_alerting_config(alerting_data) -> AlertingConfig:
    if not alerting_data:
        return AlertingConfig()

    channels = []
    for channel_data in alerting_data.get("channels", []):
        channel_values = dict(channel_data)
        channel_type = channel_values.get("type")
        if channel_type == "email":
            channel_values = _coerce_int_fields(
                channel_values,
                ("smtp_port",),
                "alerting.channels[]",
            )
            channels.append(EmailChannelConfig(**channel_values))
            continue
        if channel_type == "webhook":
            channels.append(WebhookChannelConfig(**channel_values))
            continue
        raise ValueError(f"알 수 없는 알림 채널 타입: {channel_type!r}")

    triggers = AlertingTriggersConfig(**alerting_data.get("triggers", {}))
    return AlertingConfig(channels=channels, triggers=triggers)


def _build_webui_config(webui_data) -> WebUIConfig:
    if not webui_data:
        return WebUIConfig()

    webui_values = _coerce_int_fields(
        dict(webui_data),
        (
            "monitor_refresh_seconds",
            "analytics_refresh_seconds",
            "exports_active_refresh_seconds",
            "exports_idle_refresh_seconds",
            "recent_runs_limit",
            "detail_preview_page_size",
            "analytics_export_jobs_limit",
            "export_jobs_page_limit",
            "error_message_max_length",
        ),
        "webui",
    )
    if "default_language" in webui_values:
        webui_values["default_language"] = require_supported_language(
            str(webui_values["default_language"]),
            field_name="webui.default_language",
        )
    return WebUIConfig(**webui_values)


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

    @classmethod
    def load(cls, config_path: str) -> "Settings":
        path = Path(config_path)
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        data = _walk_and_substitute(raw)
        storage = StorageConfig(**data["storage"])

        oracle = _load_oracle_from_sqlite(storage.sqlite_path)
        if oracle is None:
            if "oracle" not in data:
                raise ValueError(
                    "Oracle 설정을 찾을 수 없습니다. "
                    "YAML oracle 섹션 또는 SQLite connections(conn_id='oracle')를 확인하세요."
                )
            oracle_data = _coerce_int_fields(dict(data["oracle"]), ("port",), "oracle")
            oracle = OracleConfig(**oracle_data)

        defaults_data = data.get("defaults", {})
        retry_data = _coerce_int_fields(
            dict(defaults_data.get("retry", {})),
            ("max_attempts", "min_wait_seconds", "max_wait_seconds"),
            "defaults.retry",
        )
        retry = RetryDefaults(**retry_data)
        parquet = ParquetDefaults(**defaults_data.get("parquet", {}))
        defaults = DefaultConfig(
            chunk_size=_coerce_int(defaults_data.get("chunk_size", 10000), "defaults.chunk_size"),
            retry=retry,
            parquet=parquet,
        )

        pipelines = _load_pipelines_from_sqlite(storage.sqlite_path)
        if pipelines is None:
            pipelines = _build_pipeline_configs(data.get("pipelines", []))
        api = _build_optional_config(data.get("api", {}), ApiConfig, prefix="api", int_fields=("port",))
        alerting = _build_alerting_config(data.get("alerting", {}))
        mart = _build_optional_config(data.get("mart", {}), MartConfig, prefix="mart")
        export = _build_optional_config(
            data.get("export", {}),
            ExportConfig,
            prefix="export",
            int_fields=("retention_hours", "cleanup_cooldown_seconds", "max_workers", "rows_per_batch"),
        )
        scheduler = _build_optional_config(
            data.get("scheduler", {}),
            SchedulerConfig,
            prefix="scheduler",
            int_fields=("max_instances", "misfire_grace_time_seconds"),
        )
        webui = _build_webui_config(data.get("webui", {}))

        return cls(
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
        )
