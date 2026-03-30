# Airflow Lite

Oracle 11g 데이터를 월별 또는 일별 기준으로 Parquet 파일로 이관하고, 실행 이력을 SQLite에 남기는 경량 파이프라인 서비스입니다.

현재 소스 기준으로 이 프로젝트는 다음 구성요소를 포함합니다.

- YAML 기반 설정 로더와 환경변수 치환
- Oracle 11g thick mode 연결과 청크 단위 읽기
- `full` / `incremental` 마이그레이션 전략
- SQLite 실행 이력 저장소와 단계 상태 머신
- APScheduler 기반 스케줄링
- FastAPI 기반 수동 실행 / 백필 / 이력 조회 API
- Windows Service 래퍼
- 이메일 / 웹훅 알림 채널

문서는 설계 초안이 아니라 현재 구현된 코드 기준으로 정리되어 있습니다.

## 현재 구현 한눈에 보기

### 실행 모델

- 서비스 시작 시 `config/pipelines.yaml`을 읽습니다.
- Windows 서비스 내부에서 스케줄러와 FastAPI 서버를 함께 올립니다.
- 각 파이프라인 실행은 `PipelineRunner`가 담당합니다.
- 현재 파이프라인 단계는 `extract_transform_load` 와 `verify` 두 단계입니다.

### 지원 전략

- `full`: 실행 월 전체를 조회해 월 단위 Parquet를 새로 씁니다.
- `incremental`: `incremental_key` 기준으로 `execution_date` 당일 데이터만 조회해 월 디렉터리에 append 합니다.

### 실행 이력

- `pipeline_runs`, `step_runs` 테이블을 SQLite에 저장합니다.
- 동일 `pipeline_name + execution_date + trigger_type` 조합에 대해 성공 실행만 유니크합니다.
- 같은 날짜의 성공 실행이 이미 있으면 재실행 대신 기존 성공 실행을 반환합니다.

## 운영 환경

| 항목 | 내용 |
|------|------|
| Python | 3.11+ |
| 기본 의존성 | `oracledb`, `pyarrow`, `pandas`, `tenacity`, `pyyaml` |
| Phase 2 의존성 | `apscheduler`, `fastapi`, `uvicorn`, `sqlalchemy`, `httpx`, `pywin32` |
| 대상 환경 | Windows Server 단일 서버 운영 기준 |

`oracledb` 사용 시 Oracle 11g 연결은 thick mode가 사실상 전제입니다. `oracle_home` 설정이 있으면 `oci.dll` 위치를 찾아 `oracledb.init_oracle_client()`를 시도합니다.

## 설치

기본 엔진만 설치:

```bash
pip install -e .
```

스케줄러, API, Windows 서비스까지 포함:

```bash
pip install -e ".[phase2]"
```

개발/테스트 의존성:

```bash
pip install -e ".[dev]"
```

전체 개발 환경:

```bash
pip install -e ".[phase2,dev]"
```

## 설정

설정 파일 기본 경로는 `config/pipelines.yaml` 입니다.

### 설정 스키마

```yaml
oracle:
  host: ${ORACLE_HOST}
  port: ${ORACLE_PORT}
  service_name: ${ORACLE_SERVICE}
  user: ${ORACLE_USER}
  password: ${ORACLE_PASSWORD}
  oracle_home: "C:/oracle/instantclient_19_23"   # 선택

storage:
  parquet_base_path: "D:/data/parquet"
  sqlite_path: "D:/data/airflow_lite.db"
  log_path: "D:/data/logs"

defaults:
  chunk_size: 10000
  retry:
    max_attempts: 3
    min_wait_seconds: 4
    max_wait_seconds: 60
  parquet:
    compression: "snappy"

api:
  allowed_origins:
    - "http://10.0.0.*"
    - "http://192.168.1.*"
  host: "0.0.0.0"
  port: 8000

alerting:
  channels:
    - type: "email"
      smtp_host: "mail.internal"
      smtp_port: 25
      sender: "airflow-lite@company.com"
      recipients:
        - "ops@company.com"
    - type: "webhook"
      url: "https://messenger.internal/webhook/xxx"
      timeout: 10.0
  triggers:
    on_failure: true
    on_success: false

pipelines:
  - name: "production_log"
    table: "PRODUCTION_LOG"
    partition_column: "LOG_DATE"
    strategy: "full"
    schedule: "0 2 * * *"
    chunk_size: 20000
    columns:
      - "LOG_ID"
      - "PRODUCT_CODE"
      - "LOG_DATE"
      - "QUANTITY"
      - "STATUS"

  - name: "equipment_status"
    table: "EQUIPMENT_STATUS"
    partition_column: "STATUS_DATE"
    strategy: "incremental"
    schedule: "0 */6 * * *"
    incremental_key: "UPDATED_AT"
```

### 설정 동작 메모

- 문자열 값의 `${VAR_NAME}` 패턴은 환경변수로 치환됩니다.
- `oracle.port`, `defaults.chunk_size`, `api.port`, `smtp_port`, 파이프라인 `chunk_size` 는 문자열이어도 정수로 변환됩니다.
- `api`, `alerting` 섹션이 없으면 기본값이 적용됩니다.

## 실행

현재 패키지 엔트리포인트는 Windows 서비스 명령만 제공합니다.

```bash
python -m airflow_lite service install
python -m airflow_lite service start
python -m airflow_lite service stop
python -m airflow_lite service remove
```

서비스 시작 후 내부적으로 다음이 함께 올라갑니다.

1. 로깅 초기화
2. SQLite 스키마 초기화
3. APScheduler 잡 등록 및 시작
4. FastAPI 앱 생성
5. `uvicorn.Server` 를 별도 스레드에서 실행

## API

서비스가 실행 중이면 아래 엔드포인트를 사용할 수 있습니다.

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/pipelines` | 설정된 파이프라인 목록 조회 |
| `POST` | `/api/v1/pipelines/{name}/trigger` | 수동 실행 |
| `POST` | `/api/v1/pipelines/{name}/backfill` | 월 단위 백필 실행 |
| `GET` | `/api/v1/pipelines/{name}/runs` | 페이지네이션 실행 이력 조회 |
| `GET` | `/api/v1/pipelines/{name}/runs/{run_id}` | 실행 상세 조회 |

백필 요청 예시:

```bash
curl -X POST http://localhost:8000/api/v1/pipelines/production_log/backfill ^
  -H "Content-Type: application/json" ^
  -d "{\"start_date\":\"2026-01-01\",\"end_date\":\"2026-03-31\"}"
```

백필 응답은 단일 실행이 아니라 월별 실행 결과 리스트입니다.

## 저장 구조

### Parquet 경로

`full` 과 `incremental` 모두 월 단위 디렉터리를 사용합니다.

```text
{parquet_base_path}/{TABLE_NAME}/year={YYYY}/month={MM}/
```

대표 파일명:

```text
PRODUCTION_LOG_2026_03.parquet
```

증분 적재로 append 가 발생하면 추가 파일이 생성될 수 있습니다.

```text
PRODUCTION_LOG_2026_03.part00001.parquet
PRODUCTION_LOG_2026_03.part00002.parquet
```

### SQLite 메타데이터

- `pipeline_runs`: 파이프라인 실행 단위 메타데이터
- `step_runs`: 단계별 상태, 처리 건수, 에러 메시지, retry 횟수

## 프로젝트 구조

```text
src/airflow_lite/
├── __main__.py
├── alerting/
├── api/
├── config/
├── engine/
├── extract/
├── logging_config/
├── scheduler/
├── service/
├── storage/
└── transform/
```

주요 모듈 역할:

- `engine/pipeline.py`: 파이프라인 순차 실행과 재시도 처리
- `engine/strategy.py`: `FullMigrationStrategy`, `IncrementalMigrationStrategy`
- `engine/state_machine.py`: 단계 상태 전이 검증
- `extract/oracle_client.py`: Oracle 연결과 에러 분류
- `extract/chunked_reader.py`: `fetchmany()` 기반 스트리밍
- `transform/parquet_writer.py`: Parquet 쓰기, append, row count 조회
- `storage/database.py`: SQLite 초기화와 마이그레이션
- `service/win_service.py`: 실제 런타임 조립

## 테스트

단위 테스트:

```bash
pytest -q --basetemp .tmp_pytest -p no:cacheprovider
```

커버리지:

```bash
pytest --cov=src/airflow_lite --cov-report=term-missing
```

통합 테스트는 Oracle 접근이 필요하므로 별도 환경에서 `-m integration` 기준으로 실행합니다.

## 현재 구현상의 참고 사항

- 현재 서비스 경로에서 알림은 ETL 단계 재시도 소진 실패 시에만 연결되어 있습니다.
- `AlertManager` 자체는 성공 알림을 지원하지만, 서비스 실행 흐름에서는 성공 완료 알림을 발생시키지 않습니다.
- `verify` 실패 시 `.bak` 자동 복원까지 연결되어 있지는 않습니다. 관련 백업 유틸리티는 `BackfillManager`에 별도로 존재합니다.
- 패키지 CLI는 `service` 명령만 제공하며, 독립 실행용 `api` 또는 `scheduler` 서브커맨드는 없습니다.

## 추가 문서

- [`docs/specs/architecture.md`](docs/specs/architecture.md): 현재 코드 기준 상세 아키텍처
- [`docs/specs/requirements.md`](docs/specs/requirements.md): 요구사항 원문
- [`docs/specs/integration-test.md`](docs/specs/integration-test.md): 통합 테스트 체크리스트
