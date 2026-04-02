import os
import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path

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


class Settings:
    """YAML 설정 로더. 환경변수 ${VAR} 참조를 자동 치환한다."""

    def __init__(self, oracle, storage, defaults, pipelines, api=None, alerting=None, mart=None):
        self.oracle = oracle
        self.storage = storage
        self.defaults = defaults
        self.pipelines = pipelines
        self.api = api or ApiConfig()
        self.alerting = alerting or AlertingConfig()
        self.mart = mart or MartConfig()

    @classmethod
    def load(cls, config_path: str) -> "Settings":
        path = Path(config_path)
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        data = _walk_and_substitute(raw)

        oracle_data = dict(data["oracle"])
        oracle_data["port"] = _coerce_int(oracle_data["port"], "oracle.port")
        oracle = OracleConfig(**oracle_data)
        storage = StorageConfig(**data["storage"])

        defaults_data = data.get("defaults", {})
        retry_data = dict(defaults_data.get("retry", {}))
        if "max_attempts" in retry_data:
            retry_data["max_attempts"] = _coerce_int(retry_data["max_attempts"], "defaults.retry.max_attempts")
        if "min_wait_seconds" in retry_data:
            retry_data["min_wait_seconds"] = _coerce_int(
                retry_data["min_wait_seconds"], "defaults.retry.min_wait_seconds"
            )
        if "max_wait_seconds" in retry_data:
            retry_data["max_wait_seconds"] = _coerce_int(
                retry_data["max_wait_seconds"], "defaults.retry.max_wait_seconds"
            )
        retry = RetryDefaults(**retry_data)
        parquet = ParquetDefaults(**defaults_data.get("parquet", {}))
        defaults = DefaultConfig(
            chunk_size=_coerce_int(defaults_data.get("chunk_size", 10000), "defaults.chunk_size"),
            retry=retry,
            parquet=parquet,
        )

        pipelines = []
        for index, pipeline_data in enumerate(data.get("pipelines", []), start=1):
            pipeline_values = dict(pipeline_data)
            if pipeline_values.get("chunk_size") is not None:
                pipeline_values["chunk_size"] = _coerce_int(
                    pipeline_values["chunk_size"], f"pipelines[{index}].chunk_size"
                )
            pipelines.append(PipelineConfig(**pipeline_values))

        api_data = data.get("api", {})
        if api_data:
            api_values = dict(api_data)
            if "port" in api_values:
                api_values["port"] = _coerce_int(api_values["port"], "api.port")
            api = ApiConfig(**api_values)
        else:
            api = ApiConfig()

        alerting_data = data.get("alerting", {})
        if alerting_data:
            channels = []
            for ch_data in alerting_data.get("channels", []):
                ch = dict(ch_data)
                ch_type = ch.get("type")
                if ch_type == "email":
                    if "smtp_port" in ch:
                        ch["smtp_port"] = _coerce_int(ch["smtp_port"], "alerting.channels[].smtp_port")
                    channels.append(EmailChannelConfig(**ch))
                elif ch_type == "webhook":
                    channels.append(WebhookChannelConfig(**ch))
                else:
                    raise ValueError(f"알 수 없는 알림 채널 타입: {ch_type!r}")
            triggers_data = alerting_data.get("triggers", {})
            triggers = AlertingTriggersConfig(**triggers_data)
            alerting = AlertingConfig(channels=channels, triggers=triggers)
        else:
            alerting = AlertingConfig()

        mart_data = data.get("mart", {})
        mart = MartConfig(**mart_data) if mart_data else MartConfig()

        return cls(
            oracle=oracle,
            storage=storage,
            defaults=defaults,
            pipelines=pipelines,
            api=api,
            alerting=alerting,
            mart=mart,
        )
