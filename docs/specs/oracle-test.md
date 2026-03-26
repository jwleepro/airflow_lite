# Airflow Lite — Oracle 연동 통합 테스트 계획

## 1. 목적

이 문서는 airflow_lite의 **핵심 코어 기능**(Oracle → ChunkedReader → Parquet)이 실제 Oracle DB에서 정상 동작하는지 검증하기 위한 통합 테스트 계획이다.

현재 단위 테스트 134건은 모든 Oracle 연결을 Mock으로 대체하고 있어, 실제 Oracle과의 연동 동작은 검증되지 않은 상태다. 개발용 Oracle DB를 활용하여 이 공백을 채우는 것이 목적이다.

Apache Airflow의 3-tier 테스트 패턴을 참고한다:
- **Unit** (현재 완료): Mock 기반, Oracle 불필요
- **Integration** (이 문서): 실제 Oracle DB 사용, 파이프라인 데이터 흐름 검증
- **System** (기존 `integration-test.md`): 배포 후 Windows 서비스 전체 검수

---

## 2. 테스트 범위

### 포함

| 계층 | 검증 대상 |
|---|---|
| 연결 | OracleClient 실제 접속, thick mode, ping, 재연결 |
| 추출 | ChunkedReader.read_chunks() — 실제 cursor.fetchmany |
| 변환 | FullMigrationStrategy / IncrementalMigrationStrategy — 청크 → PyArrow |
| 적재 | ParquetWriter — 실제 파일 생성, Snappy 압축, append 모드 |
| 검증 | strategy.verify() — Oracle 행 수 vs Parquet 행 수 비교 |
| 오케스트레이션 | PipelineRunner.run() — ETL + SQLite 상태 기록 |
| 백필 | BackfillManager — 다월 처리, 멱등성 |

### 제외

- Windows 서비스 기동/종료 (→ `integration-test.md` 참고)
- APScheduler 크론 스케줄 실행 (→ `test_scheduler.py` 단위 테스트)
- FastAPI REST API (→ `test_api.py` 단위 테스트)
- 알림 채널 (→ `test_alerting.py` 단위 테스트)

---

## 3. 사전 요건

### 환경

| 항목 | 기준 |
|---|---|
| Oracle | ``, user: ``, password: `` |
| Oracle Client | Oracle Instant Client 설치 + `oci.dll` 접근 가능 |
| Python | 3.11+ |
| 설치 | `pip install -e ".[phase2]"` + `pip install oracledb pytest pytest-cov` |

### Oracle DB 테이블 전제조건

테스트는 **전용 테스트 테이블**(`AIRFLOW_TEST_*`)을 세션 시작 시 자동 생성하고 종료 시 자동 삭제한다. 운영 테이블(`PRODUCTION_LOG`, `EQUIPMENT_STATUS`)은 읽기도 접근하지 않는다.

필요 Oracle 권한:
```sql
GRANT CREATE TABLE, DROP ANY TABLE, INSERT ANY TABLE TO 계정명;
```

---

## 4. 디렉토리 구조

```
tests/
    conftest.py                          -- 수정: --run-integration 플래그 추가
    integration/                         -- 신규
        __init__.py
        conftest.py                      -- Oracle fixture, 테스트 데이터 관리
        test_oracle_connection.py        -- Oracle 실제 연결 검증 (5건)
        test_chunked_reader_oracle.py    -- 실제 cursor.fetchmany 스트리밍 (8건)
        test_full_migration.py           -- Full ETL 파이프라인 (9건)
        test_incremental_migration.py    -- Incremental 파이프라인 (5건)
        test_pipeline_runner_e2e.py      -- PipelineRunner E2E (7건)
        test_backfill_e2e.py             -- 다월 백필 (5건)
        test_idempotency.py             -- 멱등성 (4건)
        test_memory_streaming.py         -- 청크 스트리밍 검증 (3건)
```

**총 신규 통합 테스트: 46건**

---

## 5. 수정 파일

### 5.1 `pyproject.toml` — 마커 및 커버리지 설정

`[tool.pytest.ini_options]`에 추가:

```toml
markers = [
    "integration: tests requiring live Oracle DB (skip with '-m not integration')",
    "slow: tests taking more than 30 seconds",
]
addopts = "--strict-markers"
```

커버리지 설정 추가:

```toml
[tool.coverage.run]
source = ["src/airflow_lite"]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
]
```

### 5.2 `tests/conftest.py` — 통합 테스트 opt-in 플래그

기존 fixture는 건드리지 않고, 파일 끝에 아래 두 함수 추가:

```python
def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Oracle DB가 필요한 통합 테스트를 실행한다",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration", default=False):
        skip = pytest.mark.skip(reason="--run-integration 옵션 필요")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
```

---

## 6. 신규 파일: `tests/integration/conftest.py`

통합 테스트의 핵심 fixture 파일. 아래를 담당한다.

### Oracle 연결 (session 범위)

```python
ORACLE_HOST = os.environ.get("TEST_ORACLE_HOST", "")
ORACLE_PORT = int(os.environ.get("TEST_ORACLE_PORT", "1521"))
ORACLE_SERVICE = os.environ.get("TEST_ORACLE_SERVICE", "")
ORACLE_USER = os.environ.get("TEST_ORACLE_USER", "")
ORACLE_PASSWORD = os.environ.get("TEST_ORACLE_PASSWORD", "")
```

- `oracle_config` (session): `OracleConfig` 인스턴스
- `oracle_raw_connection` (session): raw `oracledb.connect()` — 테스트 데이터 setup 전용
- `oracle_client` (session): `OracleClient` 인스턴스 — 실제 파이프라인 테스트용

### 테스트 테이블 관리 (autouse, session)

세션 시작 시 자동 실행:

```
setup_test_tables (autouse, scope="session")
  ├── DROP TABLE AIRFLOW_TEST_PRODUCTION_LOG  (있으면)
  ├── CREATE TABLE AIRFLOW_TEST_PRODUCTION_LOG
  │     (LOG_ID, PRODUCT_CODE, LOG_DATE, QUANTITY, STATUS)
  ├── INSERT 100행 (1월 50건, 2월 30건, 3월 20건)
  ├── DROP TABLE AIRFLOW_TEST_EQUIPMENT_STATUS (있으면)
  ├── CREATE TABLE AIRFLOW_TEST_EQUIPMENT_STATUS
  │     (STATUS_ID, EQUIPMENT_ID, STATUS_DATE, STATUS_CODE, UPDATED_AT)
  ├── INSERT 23행 (3/15 10건, 3/16 5건, 3/17 8건)
  └── COMMIT

세션 종료 시:
  ├── DROP TABLE AIRFLOW_TEST_PRODUCTION_LOG PURGE
  └── DROP TABLE AIRFLOW_TEST_EQUIPMENT_STATUS PURGE
```

**시드 데이터 설계 원칙**: 행 수와 값이 결정적(deterministic)이어야 정확한 assertion이 가능하다. LOG_ID는 1부터 100까지 순서대로, PRODUCT_CODE는 `PROD_0001` 형식.

### 재사용 fixture

| Fixture | 범위 | 설명 |
|---|---|---|
| `chunked_reader(oracle_client)` | function | 실제 Oracle 연결 ChunkedReader (chunk_size=10) |
| `parquet_writer(tmp_path)` | function | tmp_path 대상 ParquetWriter |
| `sqlite_db(tmp_path)` | function | 테스트별 신규 SQLite DB |
| `pipeline_repos(sqlite_db)` | function | (PipelineRunRepository, StepRunRepository) |
| `full_pipeline_config()` | function | AIRFLOW_TEST_PRODUCTION_LOG 대상 PipelineConfig |
| `incr_pipeline_config()` | function | AIRFLOW_TEST_EQUIPMENT_STATUS 대상 PipelineConfig |
| `full_strategy(oracle_client, parquet_writer)` | function | 실제 Oracle 연결 FullMigrationStrategy |
| `incr_strategy(oracle_client, parquet_writer)` | function | 실제 Oracle 연결 IncrementalMigrationStrategy |
| `make_e2e_runner(oracle_client, parquet_writer, pipeline_repos)` | function | PipelineRunner 팩토리 |

`make_e2e_runner` 구현 참조: `win_service.py:_create_runner_factory()` (lines 124-199) — 동일한 컴포넌트 조립 패턴.

---

## 7. 테스트 케이스 상세

### 7.1 Oracle 연결 (`test_oracle_connection.py`)

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| OC-01 | `test_connect_to_oracle` | `get_connection()` 성공 | connection is not None |
| OC-02 | `test_thick_mode_initialized` | oracledb thick mode 초기화 | 예외 없이 통과 |
| OC-03 | `test_ping_succeeds` | `connection.ping()` 정상 | 예외 없이 통과 |
| OC-04 | `test_reconnect_after_close` | close 후 재연결 | 새 connection 정상 동작 |
| OC-05 | `test_error_on_invalid_host` | 잘못된 호스트 접속 시도 | `RetryableOracleError` 발생 |

### 7.2 청크 스트리밍 (`test_chunked_reader_oracle.py`)

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| CR-01 | `test_read_chunks_returns_dataframes` | `read_chunks()` 반환 타입 | `pd.DataFrame` 리스트 |
| CR-02 | `test_chunk_sizes_respected` | chunk_size=10, 1월 50행 | 5개 청크 |
| CR-03 | `test_column_names_match_schema` | DataFrame 컬럼명 | Oracle 컬럼명 대문자 일치 |
| CR-04 | `test_data_types_preserved` | 컬럼 타입 보존 | NUMBER→int, VARCHAR2→str, DATE→datetime |
| CR-05 | `test_empty_result_yields_nothing` | `WHERE 1=0` 쿼리 | 청크 없음 |
| CR-06 | `test_cursor_closed_after_iteration` | 이터레이션 완료 후 | 커서 close 호출 확인 |
| CR-07 | `test_large_chunk_single_fetch` | chunk_size=1000, 50행 | 1개 청크 |
| CR-08 | `test_total_row_count_matches` | 청크 합산 | `SELECT COUNT(*)` 결과와 일치 |

### 7.3 Full Migration (`test_full_migration.py`)

대상 테이블: `AIRFLOW_TEST_PRODUCTION_LOG`, partition_column: `LOG_DATE`

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| FM-01 | `test_extract_january` | 1월 파티션 추출 | 50행 |
| FM-02 | `test_transform_produces_arrow` | 청크 변환 | `pa.Table` 반환 |
| FM-03 | `test_load_creates_parquet` | Parquet 파일 생성 | `{tmp_path}/AIRFLOW_TEST_PRODUCTION_LOG/year=2026/month=01/` 존재 |
| FM-04 | `test_etl_row_count_matches` | ETL 후 행 수 | `count_rows()` = 50 |
| FM-05 | `test_verify_returns_true` | verify 통과 | `verify()` is True |
| FM-06 | `test_february_partition` | 2월 파티션 ETL | 30행, 별도 Parquet |
| FM-07 | `test_parquet_snappy_compression` | 압축 포맷 | 메타데이터 SNAPPY 확인 |
| FM-08 | `test_parquet_data_matches_oracle` | 데이터 정합성 | Parquet ↔ Oracle SELECT 결과 일치 |
| FM-09 | `test_backup_on_rerun` | 재실행 시 백업 | 두 번째 실행 후 `.bak` 파일 존재 |

### 7.4 Incremental Migration (`test_incremental_migration.py`)

대상 테이블: `AIRFLOW_TEST_EQUIPMENT_STATUS`, incremental_key: `UPDATED_AT`

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| IM-01 | `test_extract_single_day` | 3/15 데이터 추출 | 10행 |
| IM-02 | `test_load_appends` | 3/15 + 3/16 적재 | Parquet 15행 |
| IM-03 | `test_verify_succeeds` | verify 통과 | `verify()` is True |
| IM-04 | `test_query_date_range` | 생성된 쿼리 확인 | `WHERE UPDATED_AT >= DATE '2026-03-15' AND UPDATED_AT < DATE '2026-03-16'` 포함 |
| IM-05 | `test_multiple_days_accumulate` | 3일 누적 | 10+5+8 = 23행 |

### 7.5 PipelineRunner E2E (`test_pipeline_runner_e2e.py`)

`make_e2e_runner` fixture로 실제 Oracle + 실제 Parquet + 실제 SQLite 조합.

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| PE-01 | `test_run_success_full` | `runner.run()` 완료 | `status = "success"` |
| PE-02 | `test_creates_sqlite_records` | SQLite 레코드 생성 | PipelineRun + 2개 StepRun 존재 |
| PE-03 | `test_steps_all_success` | 단계별 상태 | `extract_transform_load`, `verify` 모두 success |
| PE-04 | `test_records_processed_count` | 처리 건수 기록 | `records_processed` = Oracle 행 수 (50) |
| PE-05 | `test_parquet_exists_after_run` | Parquet 생성 | 파일 존재 + `count_rows()` = 50 |
| PE-06 | `test_failure_marks_correctly` | 실패 전파 | 존재하지 않는 테이블 → `failed` + verify `skipped` |
| PE-07 | `test_error_message_persisted` | 에러 메시지 저장 | `StepRun.error_message` not None |

### 7.6 Backfill E2E (`test_backfill_e2e.py`)

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| BF-01 | `test_backfill_three_months` | 1~3월 백필 | 3개 Parquet (50+30+20행) |
| BF-02 | `test_results_all_success` | 실행 결과 | 3건 모두 status=success |
| BF-03 | `test_trigger_type_backfill` | trigger_type 확인 | `trigger_type = "backfill"` |
| BF-04 | `test_parquet_files_independent` | 파일 경로 독립 | 월별 별도 경로에 파일 존재 |
| BF-05 | `test_backfill_idempotent` | 재실행 | 두 번째 실행 시 기존 결과 반환 |

### 7.7 멱등성 (`test_idempotency.py`)

단위 테스트 `test_run_idempotent_returns_existing_success` (test_engine.py)는 Mock으로 검증. 통합 테스트에서 실제 Oracle + SQLite 조합으로 재검증.

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| ID-01 | `test_rerun_returns_existing` | 동일 execution_date 재실행 | 같은 `PipelineRun.id` 반환 |
| ID-02 | `test_parquet_not_overwritten` | Parquet 불변 | 파일 mtime 변동 없음 |
| ID-03 | `test_oracle_not_requeried` | Oracle 쿼리 재실행 없음 | `cursor()` spy — 두 번째 실행에서 호출 없음 |
| ID-04 | `test_failed_run_allows_retry` | 실패 후 재실행 허용 | 실패 기록 있어도 두 번째 실행 진행 |

### 7.8 메모리 스트리밍 (`test_memory_streaming.py`)

| ID | 테스트명 | 검증 내용 | 합격 기준 |
|---|---|---|---|
| MS-01 | `test_small_chunk_completes` | chunk_size=5, 50행 | 정상 완료, 총 50행 |
| MS-02 | `test_total_matches_with_small_chunks` | 청크 합산 | 총 행 수 일치 |
| MS-03 | `test_peak_memory_bounded` | `tracemalloc`으로 피크 측정 | 전체 데이터 크기의 2배 이내 |

---

## 8. 테스트 데이터 전략

### 원칙

- **Oracle 데이터는 읽기 전용**: 통합 테스트 중 Oracle INSERT/UPDATE 없음
- **Parquet/SQLite는 `tmp_path`**: 테스트마다 pytest가 격리된 임시 디렉토리 제공
- **결정적 시드 데이터**: 행 수와 값이 예측 가능 → 정확한 assertion 가능

### 시드 데이터 설계

**AIRFLOW_TEST_PRODUCTION_LOG**

| 월 | 행 수 | LOG_DATE 범위 | LOG_ID 범위 |
|---|---|---|---|
| 2026년 1월 | 50 | 2026-01-01 ~ 2026-01-28 (순환) | 1 ~ 50 |
| 2026년 2월 | 30 | 2026-02-01 ~ 2026-02-28 (순환) | 51 ~ 80 |
| 2026년 3월 | 20 | 2026-03-01 ~ 2026-03-20 (순환) | 81 ~ 100 |

**AIRFLOW_TEST_EQUIPMENT_STATUS**

| 날짜 | 행 수 | UPDATED_AT | STATUS_ID 범위 |
|---|---|---|---|
| 2026-03-15 | 10 | 2026-03-15 | 1 ~ 10 |
| 2026-03-16 | 5 | 2026-03-16 | 11 ~ 15 |
| 2026-03-17 | 8 | 2026-03-17 | 16 ~ 23 |

### 생명주기

```
pytest 세션 시작
    → setup_test_tables (autouse, scope="session")
        → CREATE TABLE AIRFLOW_TEST_PRODUCTION_LOG
        → CREATE TABLE AIRFLOW_TEST_EQUIPMENT_STATUS
        → INSERT 시드 데이터
        → COMMIT

테스트 실행 (Oracle은 읽기만)
    → 각 테스트: 독립적 tmp_path (Parquet, SQLite)

pytest 세션 종료
    → DROP TABLE AIRFLOW_TEST_PRODUCTION_LOG PURGE
    → DROP TABLE AIRFLOW_TEST_EQUIPMENT_STATUS PURGE
```

---

## 9. 실행 방법

```bash
# 단위 테스트만 (Oracle 불필요, 기본)
pytest tests/ -m "not integration" -v

# 통합 테스트 포함 전체
pytest tests/ --run-integration -v

# 통합 테스트만
pytest tests/integration/ --run-integration -v

# 커버리지 포함 (단위 테스트)
pytest tests/ -m "not integration" --cov=src/airflow_lite --cov-report=term-missing

# 커버리지 포함 (통합 포함)
pytest tests/ --run-integration --cov=src/airflow_lite --cov-report=html

# 특정 통합 테스트 파일만
pytest tests/integration/test_oracle_connection.py --run-integration -v

# Oracle 접속 정보 변경 시 (환경변수)
set TEST_ORACLE_HOST=192.168.1.100
set TEST_ORACLE_PORT=1521
set TEST_ORACLE_SERVICE=TESTDB
set TEST_ORACLE_USER=test_user
set TEST_ORACLE_PASSWORD=test_pass
pytest tests/integration/ --run-integration -v
```

---

## 10. 구현 순서

단계별로 Oracle 연결을 확인한 뒤 다음 단계로 진행한다. Phase 2 실패 시 Phase 3 진행 불필요.

### Phase 1 — 인프라 (기반 작업)

1. `pyproject.toml` — markers, addopts, coverage 설정 추가
2. `tests/conftest.py` — `--run-integration` 플래그 + auto-skip 로직 추가
3. `tests/integration/__init__.py` — 빈 파일 생성
4. `tests/integration/conftest.py` — Oracle fixture + 테스트 데이터 관리 전체

### Phase 2 — 기반 검증 (Oracle 연결 확인)

5. `test_oracle_connection.py` — Oracle 접속 가능 여부 확인
6. `test_chunked_reader_oracle.py` — 실제 스트리밍 동작 확인

**이 단계 실패 시**: Oracle Client 설치 상태, `oci.dll` 경로, 네트워크 연결 점검 필요.

### Phase 3 — 전략 검증 (데이터 흐름)

7. `test_full_migration.py`
8. `test_incremental_migration.py`

### Phase 4 — 오케스트레이션 (전체 통합)

9. `test_pipeline_runner_e2e.py`
10. `test_backfill_e2e.py`
11. `test_idempotency.py`
12. `test_memory_streaming.py`

---

## 11. 주요 설계 결정

### 테스트 전용 테이블 사용 이유

운영 테이블(`PRODUCTION_LOG`)을 직접 사용하지 않는 이유:
- 운영 데이터는 예측 불가 → assertion 불안정
- 운영 테이블 스키마 변경 시 테스트 영향 없어야 함
- Oracle의 다른 사용자/프로세스와 충돌 방지

### Oracle fixture를 session 범위로 설정한 이유 (Apache Airflow 패턴 참고)

- oracledb thick mode 초기화는 프로세스당 1회 (전역 상태)
- TCP 핸드쉐이크 비용 절감
- 시드 데이터는 읽기 전용이므로 session 공유 안전

### `--run-integration` 플래그 방식 채택 이유

- 환경변수 감지 방식(`ORACLE_HOST` 존재 여부)은 설정 실수로 silent skip 가능
- 명시적 opt-in으로 의도치 않은 skip 방지
- Apache Airflow의 `--backend` 옵션 패턴과 동일 철학

### Oracle 데이터 읽기 전용 유지 이유

- Oracle 트랜잭션 롤백 기반 격리(PostgreSQL 방식)는 Oracle 11g에서 복잡
- Parquet/SQLite를 `tmp_path`로 격리하면 테스트 간 독립성 충분히 확보 가능
- 구현 단순성 우선

---

## 참고 (선택)

- `docs/specs/integration-test.md` — Windows 서비스 배포 후 전체 검수 명세
- `docs/specs/architecture.md` — 전체 아키텍처 설계
- `src/airflow_lite/service/win_service.py:_create_runner_factory()` (lines 124-199) — 통합 테스트 fixture 조립 참조 구현
