from datetime import datetime
import shutil
import time
from pathlib import Path
from uuid import uuid4

import pytest

from airflow_lite.storage.database import Database
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository


def _resolve_test_tmp_root() -> Path:
    candidates = [
        Path.home() / ".codex" / "memories" / "airflow_lite_pytest",
        Path.home() / ".airflow_lite_pytest",
        Path(__file__).resolve().parents[1] / "var" / ".pytest-work",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return candidate
        except OSError:
            continue
    raise RuntimeError("No writable tmp root available for tests.")


_TEST_TMP_ROOT = _resolve_test_tmp_root()


@pytest.fixture
def tmp_path():
    """pytest 기본 temp fixture를 대체하는 수동 임시 디렉터리.

    Windows 권한 제약으로 기본 pytest temp plugin cleanup이 불안정한 환경을 우회한다.
    """
    path = _TEST_TMP_ROOT / f"airflow-lite-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    yield path

    for _ in range(5):
        try:
            shutil.rmtree(path)
            break
        except PermissionError:
            time.sleep(0.1)
    else:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_yaml(tmp_path):
    """환경변수 치환이 포함된 샘플 YAML 파일."""
    content = """\
oracle:
  host: ${ORACLE_HOST}
  port: 1521
  service_name: ${ORACLE_SERVICE}
  user: ${ORACLE_USER}
  password: ${ORACLE_PASSWORD}

storage:
  parquet_base_path: "/tmp/parquet"
  sqlite_path: "/tmp/airflow_lite.db"
  log_path: "/tmp/logs"

defaults:
  chunk_size: 10000
  retry:
    max_attempts: 3
    min_wait_seconds: 4
    max_wait_seconds: 60
  parquet:
    compression: "snappy"

pipelines:
  - name: "test_pipeline"
    table: "TEST_TABLE"
    source_where_template: "DATE_COL >= :data_interval_start AND DATE_COL < :data_interval_end"
    strategy: "full"
    schedule: "0 2 * * *"
"""
    yaml_file = tmp_path / "pipelines.yaml"
    yaml_file.write_text(content, encoding="utf-8")
    return yaml_file


@pytest.fixture
def oracle_env_vars(monkeypatch):
    """Oracle 접속 환경변수 설정."""
    monkeypatch.setenv("ORACLE_HOST", "localhost")
    monkeypatch.setenv("ORACLE_PORT", "1521")
    monkeypatch.setenv("ORACLE_SERVICE", "ORCL")
    monkeypatch.setenv("ORACLE_USER", "scott")
    monkeypatch.setenv("ORACLE_PASSWORD", "tiger")


@pytest.fixture(autouse=True)
def fernet_env_var(monkeypatch):
    monkeypatch.setenv(
        "AIRFLOW_LITE_FERNET_KEY",
        "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
    )


@pytest.fixture
def db(tmp_path):
    """임시 SQLite DB 인스턴스. 테스트마다 새 파일 사용."""
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    return database


@pytest.fixture
def pipeline_repo(db):
    return PipelineRunRepository(db)


@pytest.fixture
def step_repo(db):
    return StepRunRepository(db)


def _build_analytics_mart(database_path):
    import duckdb

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
            """
            CREATE TABLE mart_datasets (
                dataset_name VARCHAR,
                source_count BIGINT,
                total_rows BIGINT,
                total_files BIGINT,
                min_partition_start DATE,
                max_partition_start DATE,
                last_refreshed_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE mart_dataset_sources (
                dataset_name VARCHAR,
                source_name VARCHAR,
                raw_table_name VARCHAR,
                source_root VARCHAR,
                row_count BIGINT,
                file_count BIGINT,
                min_partition_start DATE,
                max_partition_start DATE,
                last_build_id VARCHAR,
                refresh_mode VARCHAR,
                last_refreshed_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE mart_dataset_files (
                dataset_name VARCHAR,
                source_name VARCHAR,
                partition_start DATE,
                file_path VARCHAR,
                row_count BIGINT,
                last_build_id VARCHAR
            )
            """
        )
        connection.execute(
            "INSERT INTO mart_datasets VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "mes_ops",
                2,
                20,
                3,
                "2026-03-01",
                "2026-04-01",
                datetime(2026, 4, 6, 10, 0, 0),
            ],
        )
        connection.executemany(
            "INSERT INTO mart_dataset_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                [
                    "mes_ops",
                    "OPS_TABLE",
                    "raw__mes_ops__ops_table",
                    "D:/data/parquet/OPS_TABLE",
                    15,
                    2,
                    "2026-03-01",
                    "2026-04-01",
                    "build-001",
                    "full",
                    datetime(2026, 4, 6, 9, 0, 0),
                ],
                [
                    "mes_ops",
                    "EQUIPMENT_STATUS",
                    "raw__mes_ops__equipment_status",
                    "D:/data/parquet/EQUIPMENT_STATUS",
                    5,
                    1,
                    "2026-04-01",
                    "2026-04-01",
                    "build-002",
                    "incremental",
                    datetime(2026, 4, 6, 10, 0, 0),
                ],
            ],
        )
        connection.executemany(
            "INSERT INTO mart_dataset_files VALUES (?, ?, ?, ?, ?, ?)",
            [
                ["mes_ops", "OPS_TABLE", "2026-03-01", "march.parquet", 10, "build-001"],
                ["mes_ops", "OPS_TABLE", "2026-04-01", "april.parquet", 5, "build-001"],
                ["mes_ops", "EQUIPMENT_STATUS", "2026-04-01", "equipment.parquet", 5, "build-002"],
            ],
        )
    finally:
        connection.close()


@pytest.fixture
def analytics_mart_builder():
    return _build_analytics_mart




def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Oracle DB가 필요한 통합 테스트를 실행한다",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration", default=False):
        skip = pytest.mark.skip(reason="--run-integration 옵션 필요 (Oracle DB 필요)")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
