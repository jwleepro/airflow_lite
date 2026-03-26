"""통합 테스트 공통 fixture.

실제 Oracle DB에 연결하여 테스트 전용 테이블을 생성/관리한다.
환경변수로 접속 정보를 오버라이드할 수 있다:
    TEST_ORACLE_HOST, TEST_ORACLE_PORT, TEST_ORACLE_SERVICE,
    TEST_ORACLE_USER, TEST_ORACLE_PASSWORD
"""
import os
from pathlib import Path

import oracledb
import pytest

from airflow_lite.config.settings import OracleConfig, PipelineConfig, Settings
from airflow_lite.engine.pipeline import PipelineDefinition, PipelineRunner
from airflow_lite.engine.stage import RetryConfig, StageDefinition, StageResult
from airflow_lite.engine.state_machine import StageStateMachine
from airflow_lite.engine.strategy import FullMigrationStrategy, IncrementalMigrationStrategy
from airflow_lite.extract.chunked_reader import ChunkedReader
from airflow_lite.extract.oracle_client import OracleClient
from airflow_lite.storage.database import Database
from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository
from airflow_lite.transform.parquet_writer import ParquetWriter

pytestmark = pytest.mark.integration

# ── Oracle 접속 정보 ───────────────────────────────────────────────────────────
# config/pipelines.yaml을 기본으로 사용. TEST_CONFIG_YAML 환경변수로 경로 오버라이드 가능.

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "pipelines.yaml"
CONFIG_YAML = Path(os.environ.get("TEST_CONFIG_YAML", str(_DEFAULT_CONFIG)))

# ── 테스트 전용 테이블명 ────────────────────────────────────────────────────────

TEST_FULL_TABLE = "AIRFLOW_TEST_PRODUCTION_LOG"
TEST_INCR_TABLE = "AIRFLOW_TEST_EQUIPMENT_STATUS"

# 시드 데이터 행 수 (결정적)
JANUARY_ROWS = 50
FEBRUARY_ROWS = 30
MARCH_ROWS = 20
INCR_ROWS_BY_DAY = {15: 10, 16: 5, 17: 8}


# ── Oracle 연결 fixture (session 범위) ────────────────────────────────────────

@pytest.fixture(scope="session")
def oracle_config():
    """config/pipelines.yaml에서 Oracle 접속 정보를 로드.
    개별 환경변수(TEST_ORACLE_HOST 등)로 항목 오버라이드 가능."""
    base = Settings.load(str(CONFIG_YAML)).oracle
    return OracleConfig(
        host=os.environ.get("TEST_ORACLE_HOST", base.host),
        port=int(os.environ.get("TEST_ORACLE_PORT", str(base.port))),
        service_name=os.environ.get("TEST_ORACLE_SERVICE", base.service_name),
        user=os.environ.get("TEST_ORACLE_USER", base.user),
        password=os.environ.get("TEST_ORACLE_PASSWORD", base.password),
    )


@pytest.fixture(scope="session")
def oracle_client(oracle_config):
    """세션 공유 OracleClient. __init__에서 thick mode를 초기화한다."""
    client = OracleClient(oracle_config)
    yield client
    client.close()


@pytest.fixture(scope="session")
def oracle_raw_connection(oracle_client, oracle_config):
    """테스트 데이터 setup/teardown 전용 raw 연결.
    oracle_client에 의존하여 thick mode가 먼저 초기화됨을 보장한다."""
    dsn = oracledb.makedsn(
        oracle_config.host, oracle_config.port, service_name=oracle_config.service_name
    )
    conn = oracledb.connect(
        user=oracle_config.user, password=oracle_config.password, dsn=dsn
    )
    yield conn
    conn.close()


# ── 테스트 테이블 생명주기 (session 범위, autouse) ────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_test_tables(oracle_raw_connection):
    """세션 시작 시 테스트 테이블 생성 및 시드 데이터 삽입.
    세션 종료 시 DROP TABLE PURGE로 완전 삭제한다."""
    cursor = oracle_raw_connection.cursor()

    # 기존 테이블 삭제 (멱등)
    for table in [TEST_FULL_TABLE, TEST_INCR_TABLE]:
        try:
            cursor.execute(f"DROP TABLE {table} PURGE")
        except Exception:
            pass

    # AIRFLOW_TEST_PRODUCTION_LOG 생성
    cursor.execute(f"""
        CREATE TABLE {TEST_FULL_TABLE} (
            LOG_ID       NUMBER PRIMARY KEY,
            PRODUCT_CODE VARCHAR2(50),
            LOG_DATE     DATE,
            QUANTITY     NUMBER,
            STATUS       VARCHAR2(20)
        )
    """)

    # AIRFLOW_TEST_EQUIPMENT_STATUS 생성
    cursor.execute(f"""
        CREATE TABLE {TEST_INCR_TABLE} (
            STATUS_ID    NUMBER PRIMARY KEY,
            EQUIPMENT_ID VARCHAR2(50),
            STATUS_DATE  DATE,
            STATUS_CODE  VARCHAR2(20),
            UPDATED_AT   DATE
        )
    """)

    # 시드 데이터: 1월 50건, 2월 30건, 3월 20건
    row_id = 1
    for month, count in [(1, JANUARY_ROWS), (2, FEBRUARY_ROWS), (3, MARCH_ROWS)]:
        for i in range(count):
            day = (i % 28) + 1
            cursor.execute(
                f"INSERT INTO {TEST_FULL_TABLE} VALUES "
                f"(:1, :2, TO_DATE(:3, 'YYYY-MM-DD'), :4, :5)",
                [
                    row_id,
                    f"PROD_{row_id:04d}",
                    f"2026-{month:02d}-{day:02d}",
                    row_id * 10,
                    "OK",
                ],
            )
            row_id += 1

    # 시드 데이터: 3/15 10건, 3/16 5건, 3/17 8건
    status_id = 1
    for day, count in sorted(INCR_ROWS_BY_DAY.items()):
        for i in range(count):
            cursor.execute(
                f"INSERT INTO {TEST_INCR_TABLE} VALUES "
                f"(:1, :2, TO_DATE(:3, 'YYYY-MM-DD'), :4, TO_DATE(:5, 'YYYY-MM-DD'))",
                [
                    status_id,
                    f"EQ_{status_id:03d}",
                    f"2026-03-{day:02d}",
                    "RUNNING",
                    f"2026-03-{day:02d}",
                ],
            )
            status_id += 1

    oracle_raw_connection.commit()
    cursor.close()

    yield

    # 세션 종료: 테이블 삭제
    cursor = oracle_raw_connection.cursor()
    for table in [TEST_FULL_TABLE, TEST_INCR_TABLE]:
        try:
            cursor.execute(f"DROP TABLE {table} PURGE")
        except Exception:
            pass
    oracle_raw_connection.commit()
    cursor.close()


# ── 재사용 컴포넌트 fixture ───────────────────────────────────────────────────

@pytest.fixture
def parquet_writer(tmp_path):
    return ParquetWriter(str(tmp_path), compression="snappy")


@pytest.fixture
def sqlite_db(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    return db


@pytest.fixture
def pipeline_repos(sqlite_db):
    """(PipelineRunRepository, StepRunRepository) 튜플."""
    return PipelineRunRepository(sqlite_db), StepRunRepository(sqlite_db)


@pytest.fixture
def full_pipeline_config():
    return PipelineConfig(
        name="test_full_migration",
        table=TEST_FULL_TABLE,
        partition_column="LOG_DATE",
        strategy="full",
        schedule="0 2 * * *",
    )


@pytest.fixture
def incr_pipeline_config():
    return PipelineConfig(
        name="test_incr_migration",
        table=TEST_INCR_TABLE,
        partition_column="STATUS_DATE",
        strategy="incremental",
        schedule="0 */6 * * *",
        incremental_key="UPDATED_AT",
    )


@pytest.fixture
def full_strategy(oracle_client, parquet_writer):
    """실제 Oracle에 연결된 FullMigrationStrategy."""
    reader = ChunkedReader(connection=None, chunk_size=10)
    return FullMigrationStrategy(oracle_client, reader, parquet_writer)


@pytest.fixture
def incr_strategy(oracle_client, parquet_writer):
    """실제 Oracle에 연결된 IncrementalMigrationStrategy."""
    reader = ChunkedReader(connection=None, chunk_size=10)
    return IncrementalMigrationStrategy(oracle_client, reader, parquet_writer)


@pytest.fixture
def make_e2e_runner(oracle_client, parquet_writer, pipeline_repos):
    """PipelineRunner 팩토리 fixture.
    win_service.py:_create_runner_factory()와 동일한 컴포넌트 조립 패턴."""
    run_repo, step_repo = pipeline_repos
    state_machine = StageStateMachine(step_repo)

    def _factory(pipeline_config, chunk_size=10):
        reader = ChunkedReader(connection=None, chunk_size=chunk_size)

        if pipeline_config.strategy == "full":
            strategy = FullMigrationStrategy(oracle_client, reader, parquet_writer)
        else:
            strategy = IncrementalMigrationStrategy(oracle_client, reader, parquet_writer)

        retry_config = RetryConfig(max_attempts=1, min_wait_seconds=0, max_wait_seconds=0)

        def etl_stage(context) -> StageResult:
            total = 0
            for chunk in strategy.extract(context):
                arrow_table = strategy.transform(chunk, context)
                total += strategy.load(arrow_table, context)
            return StageResult(records_processed=total)

        def verify_stage(context) -> StageResult:
            if not strategy.verify(context):
                raise RuntimeError("verification failed")
            return StageResult()

        stages = [
            StageDefinition(
                name="extract_transform_load",
                callable=etl_stage,
                retry_config=retry_config,
            ),
            StageDefinition(
                name="verify",
                callable=verify_stage,
                retry_config=RetryConfig(max_attempts=1),
            ),
        ]

        return PipelineRunner(
            pipeline=PipelineDefinition(
                name=pipeline_config.name,
                stages=stages,
                strategy=strategy,
                table_config=pipeline_config,
                chunk_size=chunk_size,
            ),
            run_repo=run_repo,
            step_repo=step_repo,
            state_machine=state_machine,
        )

    return _factory
