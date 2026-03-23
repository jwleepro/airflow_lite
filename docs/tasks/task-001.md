# Task-001: 프로젝트 초기 설정

## 목적

Airflow Lite 프로젝트의 기반 구조를 생성한다. 패키지 빌드 설정, 디렉터리 구조, 설정 로더, 로깅을 구축하여 이후 모든 task의 실행 기반을 마련한다.

## 입력

- Python 3.11+ 환경
- 프로젝트 루트 디렉터리: `D:\00_TestProject\airflow_lite`

## 출력

- `pyproject.toml` (패키지 메타데이터 + 의존성 정의)
- `src/airflow_lite/` 패키지 디렉터리 구조 (architecture.md 섹션 2 참조)
- `src/airflow_lite/__main__.py` (CLI 진입점)
- `src/airflow_lite/config/settings.py` (YAML 설정 로더)
- `src/airflow_lite/logging_config/setup.py` (로깅 설정)
- `tests/` 디렉터리 + `conftest.py`

## 구현 제약

- 기술 스택: Python 3.11+, PyYAML 6.0+, pytest
- 단일 프로세스 설계 (P1)
- 환경변수로 민감 정보 관리 (NFR-10)

## 구현 상세

### pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "airflow-lite"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "oracledb>=1.3",
    "pyarrow>=14.0",
    "pandas>=2.1",
    "tenacity>=8.2",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
phase2 = [
    "apscheduler>=3.10",
    "fastapi>=0.110",
    "uvicorn>=0.27",
    "pydantic>=2.6",
    "httpx>=0.27",
    "pywin32>=306",
]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 디렉터리 구조

```
src/airflow_lite/
├── __init__.py
├── __main__.py
├── engine/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── stage.py
│   ├── strategy.py
│   ├── state_machine.py
│   └── backfill.py
├── storage/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── database.py
├── extract/
│   ├── __init__.py
│   ├── oracle_client.py
│   └── chunked_reader.py
├── transform/
│   ├── __init__.py
│   └── parquet_writer.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── logging_config/
│   ├── __init__.py
│   └── setup.py
├── scheduler/
│   └── __init__.py
├── api/
│   ├── __init__.py
│   └── routes/
│       └── __init__.py
├── alerting/
│   └── __init__.py
└── service/
    └── __init__.py
tests/
├── __init__.py
└── conftest.py
```

### config/settings.py — YAML 로더 + 환경변수 치환

```python
import os
import re
import yaml
from dataclasses import dataclass
from pathlib import Path

# 환경변수 치환 패턴: ${VAR_NAME}
ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")

def _substitute_env_vars(value: str) -> str:
    """YAML 문자열 내 ${VAR_NAME} 패턴을 os.environ에서 조회하여 치환.
    미설정 시 KeyError를 발생시켜 시작 단계에서 명확하게 실패."""
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
    retry: RetryDefaults = None
    parquet: ParquetDefaults = None

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

class Settings:
    """YAML 설정 로더. 환경변수 ${VAR} 참조를 자동 치환한다."""

    def __init__(self, oracle, storage, defaults, pipelines):
        self.oracle = oracle
        self.storage = storage
        self.defaults = defaults
        self.pipelines = pipelines

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
        return cls(oracle=oracle, storage=storage, defaults=defaults, pipelines=pipelines)
```

### logging_config/setup.py — 로깅 설정

```python
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: str, level: int = logging.INFO) -> None:
    """로깅 설정.

    - TimedRotatingFileHandler: 일별 로테이션, 30일 보관
    - 로거 네이밍: airflow_lite.{module}.{pipeline}.{stage}
    - 포맷: %(asctime)s [%(levelname)s] %(name)s - %(message)s
    - 로그 경로: {log_dir}/airflow_lite_{date}.log
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / "airflow_lite.log"

    handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger("airflow_lite")
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    root_logger.addHandler(console_handler)
```

## 완료 조건

- [ ] `pyproject.toml` 작성, `pip install -e ".[dev]"` 성공
- [ ] 디렉터리 구조 생성 (모든 `__init__.py` 포함)
- [ ] `Settings.load("config/pipelines.yaml")` 동작 확인 (환경변수 치환 포함)
- [ ] `setup_logging()` 호출 후 로그 파일 생성 확인
- [ ] `pytest` 실행 가능 (테스트 0개라도 수집/실행 성공)
- [ ] 테스트: 환경변수 치환 로직 단위 테스트
- [ ] 테스트: 미설정 환경변수 시 명확한 에러 메시지 확인

## 참고 (선택)

- 전체 프로젝트 구조: `docs/system_design/architecture.md` 섹션 2
- 설정 YAML 예시: `docs/system_design/architecture.md` 섹션 5
- 요구사항 원문: `docs/system_design/requirements.md`
