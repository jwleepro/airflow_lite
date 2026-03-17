import pytest
import os
import tempfile
from pathlib import Path

from airflow_lite.storage.database import Database
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository


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
    partition_column: "DATE_COL"
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
