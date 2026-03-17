# Airflow Lite

Oracle 11g → Parquet 데이터 이관을 위한 경량 파이프라인 엔진.

Windows Server 단일 서버 환경에서 Apache Airflow의 핵심 개념(파이프라인 단계 정의, 재시도/에러 핸들링, 백필)을 차용하되, 설치/운영 복잡도를 최소화한 구현체입니다.

---

## 특징

- **선언적 파이프라인 정의** — YAML 설정으로 Extract → Transform → Load → Verify 단계 정의
- **자동 장애 복구** — Oracle 연결 끊김 등 MES 환경 특화 에러에 대한 지수 백오프 재시도
- **안전한 재처리(백필)** — 멱등성을 보장하는 과거 데이터 재이관 (`.bak` 백업 후 검증)
- **Cron 스케줄링** — APScheduler 기반 주기 실행, Windows 서비스 자동 시작
- **REST API** — 수동 트리거, 백필 요청, 실행 이력 조회
- **알림** — 파이프라인 실패 시 이메일 / 사내 웹훅 발송
- **500MB 메모리 제약** — 청크 기반 스트리밍으로 대용량 테이블 처리

---

## 운영 환경

| 항목 | 사양 |
|------|------|
| OS | Windows Server 2019 |
| Python | 3.11+ |
| 소스 DB | Oracle 11g (oracledb thick mode) |
| 실행 형태 | 단일 서버, 단일 프로세스 |

> **주의**: cx_Oracle은 Python 3.14에서 설치 불가(개발 공식 종료). 본 프로젝트는 Oracle 공식 후속 패키지인 `oracledb`를 사용하며, Oracle 11g 연결에 thick mode가 필요합니다.

---

## 설치

### 1단계 (파이프라인 엔진 코어)

```bash
pip install -e .
```

### 2단계 (스케줄러 + API + Windows 서비스)

```bash
pip install -e ".[phase2]"
```

### 개발 의존성

```bash
pip install -e ".[dev]"
```

---

## 빠른 시작

### 1. 환경변수 설정

```bash
set ORACLE_HOST=your-oracle-host
set ORACLE_PORT=1521
set ORACLE_SERVICE=your-service-name
set ORACLE_USER=your-user
set ORACLE_PASSWORD=your-password
```

### 2. 파이프라인 설정

`config/pipelines.yaml`을 수정하여 파이프라인을 정의합니다:

```yaml
oracle:
  host: ${ORACLE_HOST}
  port: ${ORACLE_PORT}
  service_name: ${ORACLE_SERVICE}
  user: ${ORACLE_USER}
  password: ${ORACLE_PASSWORD}

storage:
  parquet_base_path: "D:/data/parquet"
  sqlite_path: "D:/data/airflow_lite.db"
  log_path: "D:/data/logs"

pipelines:
  - name: "production_log"
    table: "PRODUCTION_LOG"
    partition_column: "LOG_DATE"
    strategy: "full"           # full | incremental
    schedule: "0 2 * * *"     # 매일 02:00
    chunk_size: 20000
    columns:
      - "LOG_ID"
      - "PRODUCT_CODE"
      - "LOG_DATE"
      - "QUANTITY"
      - "STATUS"
```

### 3. Windows 서비스 등록

```bash
python -m airflow_lite service install   # 서비스 등록 (자동 시작)
python -m airflow_lite service start     # 서비스 시작
python -m airflow_lite service stop      # 서비스 중지
python -m airflow_lite service remove    # 서비스 제거
```

---

## API

서비스 실행 후 아래 엔드포인트를 사용할 수 있습니다.

| Method | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/pipelines/{name}/trigger` | 수동 즉시 실행 |
| `POST` | `/api/v1/pipelines/{name}/backfill` | 백필 요청 |
| `GET`  | `/api/v1/pipelines` | 파이프라인 목록 조회 |
| `GET`  | `/api/v1/pipelines/{name}/runs` | 실행 이력 조회 |
| `GET`  | `/api/v1/pipelines/{name}/runs/{run_id}` | 실행 상세 |

**백필 예시:**

```bash
curl -X POST http://localhost:8000/api/v1/pipelines/production_log/backfill \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2026-01-01", "end_date": "2026-03-31"}'
```

---

## 프로젝트 구조

```
src/airflow_lite/
├── engine/          # Phase 1: 파이프라인 엔진 코어
│   ├── pipeline.py      # PipelineDefinition, PipelineRunner
│   ├── stage.py         # StageDefinition, StageState
│   ├── strategy.py      # MigrationStrategy (Full / Incremental)
│   ├── state_machine.py # 상태 전이 관리
│   └── backfill.py      # BackfillManager
├── storage/         # SQLite 실행 이력 저장소
│   ├── models.py        # 데이터 모델
│   ├── repository.py    # PipelineRunRepository, StepRunRepository
│   └── database.py      # SQLite 연결 (WAL 모드)
├── extract/         # Oracle 데이터 추출
│   ├── oracle_client.py   # Oracle 연결 (재시도 포함)
│   └── chunked_reader.py  # 청크 기반 커서 스트리밍
├── transform/       # 데이터 변환
│   └── parquet_writer.py  # Parquet 직렬화 (Snappy 압축)
├── config/          # 설정 관리
│   └── settings.py        # YAML 설정 로더 (환경변수 치환)
├── logging_config/  # 로깅
│   └── setup.py           # TimedRotatingFileHandler (일별, 30일 보관)
├── scheduler/       # Phase 2: APScheduler 스케줄러
├── api/             # Phase 2: FastAPI REST API
├── alerting/        # Phase 2: 이메일 / 웹훅 알림
└── service/         # Phase 2: Windows 서비스 래퍼
```

---

## 아키텍처

### 데이터 흐름

```
Oracle 11g → ChunkedReader (fetchmany) → MigrationStrategy.transform
          → ParquetWriter (Snappy) → /data/parquet/{TABLE}/YYYY={MM}/
```

### 단계 상태 전이

```
PENDING → RUNNING → SUCCESS
                 → FAILED → PENDING (재시도)
PENDING → SKIPPED (선행 단계 실패 시)
```

### 파티션 구조

```
/data/parquet/{TABLE_NAME}/YYYY={MM}/{TABLE_NAME}_{YYYY}_{MM}.parquet
```

자세한 설계는 [`docs/architecture.md`](docs/architecture.md)를 참조하세요.

---

## 테스트

```bash
pytest
pytest --cov=src/airflow_lite --cov-report=term-missing
```

---

## 구현 단계

| 단계 | 범위 | 상태 |
|------|------|------|
| Phase 1 | 파이프라인 엔진 코어 (engine, storage, extract, transform, config, logging) | 완료 |
| Phase 2 | 스케줄러, API, 알림, Windows 서비스 | 완료 |
| Phase 3 | React 모니터링 대시보드 | 예정 |

---

## 요구사항 문서

- [`docs/requirements.md`](docs/requirements.md) — 기능/비기능 요구사항 정의
- [`docs/architecture.md`](docs/architecture.md) — 상세 설계 결정 및 아키텍처
