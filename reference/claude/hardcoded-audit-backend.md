# Hardcoded Values Audit — Backend Layer

감사일: 2026-04-08
대상: src/airflow_lite/ 전체 (UI 제외)

---

## 1. CRITICAL HARDCODED VALUES

### src/airflow_lite/scheduler/scheduler.py

- **Line 55**: `misfire_grace_time: 3600` - Should be configurable (1 hour grace time for missed executions)
- **Line 53-54**: `coalesce: True`, `max_instances: 1` - These APScheduler job defaults are hardcoded

### src/airflow_lite/export/service.py

- **Line 115**: `max_workers: int = 2` - Thread pool executor size is hardcoded
- **Line 273**: `rows_per_batch=10_000` - Batch size for DuckDB exports is hardcoded
- **Line 282**: `compression="snappy"` - Compression type hardcoded for Parquet exports
- **Line 298**: `compression=zipfile.ZIP_DEFLATED` - ZIP compression hardcoded

### src/airflow_lite/extract/chunked_reader.py

- **Line 19**: `chunk_size: int = 10000` - Default chunk size, though can be overridden per pipeline

### src/airflow_lite/transform/parquet_writer.py

- **Line 20-22**: `compression: str = "snappy"` - Default compression in constructor (though configurable through settings)

### src/airflow_lite/engine/pipeline.py

- **Line 39**: `chunk_size: int = 10000` - Default chunk size in PipelineDefinition

### src/airflow_lite/alerting/email.py

- **Line 21**: `smtp_port: int = 25` - Hardcoded SMTP port default
- **Line 21**: `sender: str = "airflow-lite@company.com"` - Hardcoded email sender address (company-specific)

### src/airflow_lite/alerting/webhook.py

- **Line 16**: `timeout: float = 10.0` - Hardcoded HTTP timeout for webhook calls

### src/airflow_lite/storage/database.py

- **Line 11**: `PRAGMA journal_mode = WAL` - SQLite WAL mode is hardcoded
- **Line 12**: `PRAGMA foreign_keys = ON` - Foreign key enforcement is hardcoded

### src/airflow_lite/mart/execution.py

- **Line 45**: Raw table name prefix `"raw__"` is hardcoded in `_raw_table_name()` method
- **Line 169-174**: String slugification logic with hardcoded underscore separator and "dataset" default

### src/airflow_lite/mart/snapshot.py

- **Line 19**: `database_filename: str = "analytics.duckdb"` - Database filename hardcoded
- **Line 20**: `current_dirname: str = "current"` - Directory name hardcoded
- **Line 21**: `staging_dirname: str = "staging"` - Directory name hardcoded
- **Line 22**: `snapshots_dirname: str = "snapshots"` - Directory name hardcoded

### src/airflow_lite/query/service.py

- **Line 63-64**: `SUPPORTED_FILTERS`, `SUPPORTED_DETAILS` - Hardcoded as frozensets (cannot be extended)
- **Line 83-86**: `EXPORT_ACTIONS` - Export action mappings hardcoded
- **Line 273**: `rows_per_batch=10_000` - Batch size hardcoded in `_write_artifact()`

### src/airflow_lite/analytics/catalog.py

- **Line 29**: `COMMON_FILTER_KEYS = ["source", "partition_month"]` - Hardcoded filter keys
- **Line 126**: `limit=12` - Hardcoded chart limit for rows_by_month
- **Line 137**: `limit=20` - Hardcoded chart limit for files_by_source
- **Line 66**: `"Promoted mart coverage and refresh health view for MES datasets."` - Hardcoded dashboard description

### src/airflow_lite/api/app.py

- **Line 77**: `prefix="/api/v1"` - API prefix is hardcoded (appears in multiple routes)

### src/airflow_lite/__main__.py

- **Line 19**: `config_path = sys.argv[2] if len(sys.argv) > 2 else "config/pipelines.yaml"` - Hardcoded default config path
- **Line 58**: `Path(settings.mart.root_path).parent / "exports"` - Export root path calculated from mart path (no separate config)

---

## 2. WHAT IS ALREADY CONFIGURABLE (per settings.py)

### Well-Configured Areas

- Oracle connection (host, port, service_name, user, password, oracle_home) — **OracleConfig**
- Storage paths (parquet_base_path, sqlite_path, log_path) — **StorageConfig**
- Retry configuration (max_attempts, min_wait_seconds, max_wait_seconds) — **RetryDefaults**
- Parquet compression type — **ParquetDefaults.compression**
- Default chunk_size — **DefaultConfig.chunk_size**
- API host/port/CORS origins — **ApiConfig**
- Email channel (smtp_host, smtp_port, sender, recipients) — **EmailChannelConfig**
- Webhook channel (url, timeout) — **WebhookChannelConfig**
- Export retention and cleanup — **ExportConfig** (retention_hours=72, cleanup_cooldown_seconds=300)
- Mart root path and database filename — **MartConfig**

### settings.py Dataclass 전체 구조

```python
@dataclass
class OracleConfig:
    host: str
    port: int
    service_name: str
    user: str
    password: str
    oracle_home: str | None = None

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

@dataclass
class MartConfig:
    enabled: bool = False
    root_path: str = "data/mart"
    database_filename: str = "analytics.duckdb"
    refresh_on_success: bool = True
    pipeline_datasets: dict[str, str] = field(default_factory=dict)
```

### Settings 클래스

```python
class Settings:
    def __init__(self, oracle, storage, defaults, pipelines, api=None, alerting=None, mart=None, export=None):
        self.oracle = oracle
        self.storage = storage
        self.defaults = defaults
        self.pipelines = pipelines
        self.api = api or ApiConfig()
        self.alerting = alerting or AlertingConfig()
        self.mart = mart or MartConfig()
        self.export = export or ExportConfig()
```

---

## 3. RECOMMENDATIONS FOR CONFIGURATION

### High Priority (affects runtime behavior)

1. Move scheduler job defaults (coalesce, max_instances, misfire_grace_time) to config
2. Add export service configuration (max_workers, rows_per_batch, compression)
3. Make webhook timeout configurable
4. Move email defaults to config instead of code defaults
5. Move mart directory names (current, staging, snapshots) to config
6. Add SQLite PRAGMA settings to config
7. Make dashboard chart limits configurable

### Medium Priority (affects data handling)

1. Make supported filters and details extensible (move from frozensets)
2. Externalize dashboard descriptions and titles
3. Move API prefix to configuration
4. Make directory naming patterns configurable (year/month format, raw__ prefix)

### Low Priority (nice to have)

1. Make default config path environment-variable driven
2. Externalize email subject line format

### Files to Review for Configuration Changes

- `src/airflow_lite/config/settings.py` — Add new config dataclasses
- All files listed above with hardcoded values — Update to use Settings object
