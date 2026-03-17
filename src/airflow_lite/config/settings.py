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


class Settings:
    """YAML 설정 로더. 환경변수 ${VAR} 참조를 자동 치환한다."""

    def __init__(self, oracle, storage, defaults, pipelines, api=None):
        self.oracle = oracle
        self.storage = storage
        self.defaults = defaults
        self.pipelines = pipelines
        self.api = api or ApiConfig()

    @classmethod
    def load(cls, config_path: str) -> "Settings":
        path = Path(config_path)
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        data = _walk_and_substitute(raw)

        oracle = OracleConfig(**data["oracle"])
        storage = StorageConfig(**data["storage"])

        defaults_data = data.get("defaults", {})
        retry = RetryDefaults(**defaults_data.get("retry", {}))
        parquet = ParquetDefaults(**defaults_data.get("parquet", {}))
        defaults = DefaultConfig(
            chunk_size=defaults_data.get("chunk_size", 10000),
            retry=retry,
            parquet=parquet,
        )

        pipelines = [PipelineConfig(**p) for p in data.get("pipelines", [])]

        api_data = data.get("api", {})
        api = ApiConfig(**api_data) if api_data else ApiConfig()

        return cls(oracle=oracle, storage=storage, defaults=defaults, pipelines=pipelines, api=api)
