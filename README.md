<div align="center">
  <h1>Airflow Lite</h1>
  <p><strong>Oracle 11g 데이터를 Parquet로 적재하고, DuckDB 기반 분석 mart를 서빙하는 경량 배치 파이프라인</strong></p>
</div>

<!-- Badges -->
<div align="center">

| | |
|---|---|
| **Package** | `pip install -e ".[phase2]"` · Python 3.11+ |
| **Runtime** | Windows Server 2019 · Oracle 11g thick mode · DuckDB |
| **License** | Internal |

</div>

---

## Table of Contents

- [Project Focus](#project-focus)
- [Architecture](#architecture)
- [Principles](#principles)
- [Core Features](#core-features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [API Reference](#api-reference)
- [Web UI](#web-ui)
- [Storage Layout](#storage-layout)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [Documentation](#documentation)

---

## Project Focus

Airflow Lite는 다음과 같은 환경에 최적화되어 있습니다:

**적합한 경우**
- 소스 시스템이 **Oracle 11g**이고 배치 추출이 핵심 요구사항일 때
- 운영 Oracle 부하를 줄이고 **DuckDB 기반 분석/조회**를 제공해야 할 때
- **단일 Windows Server** 운영 모델이 허용될 때
- 월별 또는 일별 Parquet 산출물과 집계 중심 대시보드가 필요할 때

**적합하지 않은 경우**
- 실시간 CDC, Kafka, 스트리밍 워크로드
- 분산 실행, 범용 워크플로 오케스트레이션
- 멀티 서버, Kubernetes, Celery 기반 스케일아웃

> **Apache Airflow를 대체하려는 프로젝트가 아닙니다.**
> Oracle → Parquet 이관, DuckDB mart 서빙, 경량 스케줄링, 실행 이력 추적이라는
> 좁고 명확한 운영 시나리오에 집중합니다.

---

## Architecture

```
Oracle 11g → [ingest] → Parquet raw → [mart] → DuckDB → [serve] → FastAPI → Web UI
```

| 레이어 | 역할 |
|--------|------|
| **ingest** | Oracle에서 청크 단위 추출 |
| **raw** | 원본 보존용 Parquet (재현 가능한 원천) |
| **mart** | DuckDB fact/dimension/summary (재생성 가능한 파생) |
| **serve** | API, export, query service |
| **ops** | 스케줄, 실행 이력, 로그, 알림 |

---

## Principles

| 원칙 | 설명 |
|------|------|
| **Batch-first** | 배치 ETL 전용. 실시간 CDC, 스트리밍은 범위 밖 |
| **Reproducible** | Raw Parquet 보존. Mart는 언제든 raw로부터 재빌드 가능 |
| **Observable** | 실행 이력, 단계별 상태, 재시도 횟수, 알림 채널 |
| **Lightweight** | 단일 서버, 비분산. WSL, K8s, Celery, Redis 없음 |
| **Offline-ready** | 폐쇄망(사내망) 운영 가능 |

---

## Core Features

| 영역 | 기능 |
|------|------|
| **Ingest** | `oracledb` thick mode 기반 Oracle 11g 연결, 청크 단위 추출, `full`/`incremental` 전략 |
| **Storage** | 월 단위 Parquet 산출물, SQLite 실행 이력, 재시도·상태 전이 포함 stage 기반 실행 모델 |
| **Mart** | Parquet → DuckDB staging build → validation → snapshot promotion |
| **Analytics** | KPI summary, chart 시리즈, detail 페이징, dashboard 정의, 필터 메타데이터 |
| **Export** | 비동기 export job 생성 (xlsx, csv.zip, parquet), artifact 다운로드 |
| **Web UI** | `/monitor` 파이프라인 모니터, `/monitor/analytics` 대시보드, `/monitor/exports` export job 화면 |
| **Scheduling** | APScheduler cron 스케줄링, 수동 실행, 월 단위 백필 |
| **API** | FastAPI 엔드포인트 (파이프라인 관리 + analytics 조회 + export) |
| **Alerting** | 이메일 및 웹훅 알림 채널 |
| **Service** | Windows Service 래퍼를 통한 장기 실행 |

---

## Requirements

| 항목 | 내용 |
|------|------|
| **Python** | 3.11+ |
| **OS** | Windows Server 2019 이상 |
| **Oracle Client** | Oracle 11g thick mode 연결을 위한 Oracle Client 또는 Instant Client |
| **핵심 의존성** | `oracledb`, `duckdb`, `pyarrow`, `pandas`, `tenacity`, `pyyaml` |
| **서비스 추가** | `apscheduler`, `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `httpx`, `pywin32` |

---

## Quick Start

### 1. 설치

```bash
pip install -e ".[phase2]"
```

### 2. 기본 설정 파일 준비

`config/pipelines.yaml` 준비:

```yaml
oracle:
  host: ${ORACLE_HOST}
  port: ${ORACLE_PORT}
  service_name: ${ORACLE_SERVICE}
  user: ${ORACLE_USER}
  password: ${ORACLE_PASSWORD}
  oracle_home: "C:/oracle/instantclient_19_23"

storage:
  parquet_base_path: "D:/data/parquet"
  sqlite_path: "D:/data/airflow_lite.db"
  log_path: "D:/data/logs"

defaults:
  chunk_size: 10000

mart:
  enabled: true
  root_path: "D:/data/mart"
  refresh_on_success: true
```

### 3. DAG 파일 준비

`dags/default.py` 파일을 생성해 파이프라인을 코드로 정의한다.

```python
from airflow_lite.dag_api import Pipeline

pipelines = [
    Pipeline(
        id="production_log",
        table="PRODUCTION_LOG",
        source_where_template="LOG_DATE >= :data_interval_start AND LOG_DATE < :data_interval_end",
        strategy="full",
        schedule="0 2 * * *",
        chunk_size=5000,
    ),
]
```

### 4. 실행

**Windows 서비스**

```powershell
python -m airflow_lite service install
python -m airflow_lite service start
```

**포그라운드 (개발/디버깅)**

```bash
python -m airflow_lite run
```

서비스 중지 및 제거:

```powershell
python -m airflow_lite service stop
python -m airflow_lite service remove
```

### 5. 확인

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI 스키마: `http://localhost:8000/openapi.json`
- 파이프라인 목록: `http://localhost:8000/api/v1/pipelines`
- 운영 모니터: `http://localhost:8000/monitor`
- 분석 대시보드: `http://localhost:8000/monitor/analytics?dataset=mes_ops`
- Export 모니터: `http://localhost:8000/monitor/exports`

---

## Installation

| 대상 | 명령 |
|------|------|
| 핵심 엔진만 | `pip install -e .` |
| 스케줄러 + API + Windows 서비스 | `pip install -e ".[phase2]"` |
| 개발·테스트 도구 포함 | `pip install -e ".[dev]"` |
| 전체 개발 환경 | `pip install -e ".[phase2,dev]"` |

---

## Configuration

기본 설정 파일 경로: `config/pipelines.yaml`

파이프라인 정의 파일 경로: `dags/*.py` (기본값). 필요 시 `AIRFLOW_LITE_DAGS_DIR` 환경변수로 DAG 디렉터리를 지정할 수 있다.

### 설정 규칙

- `${VAR_NAME}` 패턴은 프로세스 환경변수로 치환
- 정수 필드(`oracle.port`, `defaults.chunk_size` 등)는 자동 변환
- `api`, `alerting`, `mart`, `webui` 섹션은 선택 사항
- `webui.default_language`는 `en` 또는 `ko` (기본값: `en`)
- `pipelines` 섹션은 legacy fallback 용도이며, DAG 파일에서 파이프라인이 로드되면 사용되지 않음

### DAG 정의 규칙

- DAG 파일은 `dags/` 아래 `.py` 파일로 관리
- 각 파일은 `pipelines` 리스트를 노출해야 함
- `pipelines` 항목은 `airflow_lite.dag_api.Pipeline` 또는 `PipelineConfig` 인스턴스여야 함
- `_`로 시작하는 파일은 로드 대상에서 제외됨(`_migrated.py`는 예외)

<details>
<summary><strong>전체 설정 예시</strong></summary>

```yaml
security:
  fernet_key: REPLACE_WITH_GENERATED_FERNET_KEY

oracle:
  host: ${ORACLE_HOST}
  port: ${ORACLE_PORT}
  service_name: ${ORACLE_SERVICE}
  user: ${ORACLE_USER}
  password: ${ORACLE_PASSWORD}
  oracle_home: "C:/oracle/instantclient_19_23"

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

mart:
  enabled: true
  root_path: "D:/data/mart"
  refresh_on_success: true
  pipeline_datasets:
    production_log: "mes_ops"

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

webui:
  monitor_refresh_seconds: 30
  default_language: ko
```

</details>

---

## How It Works

### 서비스 런타임 흐름

1. `config/pipelines.yaml`에서 공통 설정(oracle/storage/defaults 등)을 로드
2. `dags/*.py`에서 파이프라인 정의를 로드
3. DAG가 비어 있으면 YAML `pipelines`를 legacy fallback으로 로드
4. 로깅과 SQLite 메타데이터 데이터베이스 초기화
5. APScheduler에 스케줄 작업 등록
6. FastAPI 애플리케이션을 백그라운드 스레드에서 시작
7. `PipelineRunner`를 통해 각 파이프라인 실행

### 파이프라인 Stage

각 파이프라인은 두 개의 stage로 구성:

1. **extract_transform_load** — Oracle에서 데이터 추출 후 Parquet 적재
2. **verify** — 산출물 검증

`mart.enabled: true`와 `mart.refresh_on_success: true`가 함께 설정되면, raw Parquet 실행 성공 후 DuckDB mart staging build → validation → snapshot promotion이 이어서 실행됩니다.

### 전략별 동작

| 전략 | 동작 |
|------|------|
| `full` | 대상 월 전체를 읽고 월 단위 Parquet를 새로 작성 |
| `incremental` | `incremental_key` 기준으로 실행일 데이터만 읽고 월 디렉터리에 append |

### 멱등성

- `force_rerun`이 아니면 동일 파이프라인+실행일의 성공 실행은 재사용
- 실행 메타데이터는 `pipeline_runs`, `step_runs` 테이블에 저장

---

## API Reference

### 파이프라인 관리

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/pipelines` | 설정된 파이프라인 목록 |
| `POST` | `/api/v1/pipelines/{name}/trigger` | 수동 실행 |
| `POST` | `/api/v1/pipelines/{name}/backfill` | 월 단위 백필 |
| `GET` | `/api/v1/pipelines/{name}/runs` | 실행 이력 (페이지네이션) |
| `GET` | `/api/v1/pipelines/{name}/runs/{run_id}` | 단계 상태 포함 실행 상세 |

### Analytics 조회

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/analytics/summary` | KPI 요약 |
| `POST` | `/api/v1/analytics/charts/{chart_id}/query` | 차트 시리즈 |
| `POST` | `/api/v1/analytics/details/{detail_key}/query` | 상세 그리드 (페이징) |
| `GET` | `/api/v1/analytics/filters` | dataset별 필터 메타데이터 |
| `GET` | `/api/v1/analytics/dashboards/{dashboard_id}` | dashboard widget/action 메타데이터 |

### Export

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/analytics/exports` | 비동기 export job 생성 |
| `GET` | `/api/v1/analytics/exports/{job_id}` | export job 상태 조회 |
| `GET` | `/api/v1/analytics/exports/{job_id}/download` | 완료된 artifact 다운로드 |

<details>
<summary><strong>사용 예시</strong></summary>

**수동 실행**

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/trigger" `
  -ContentType "application/json" `
  -Body '{"execution_date":"2026-03-01","force":false}'
```

**백필**

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/backfill" `
  -ContentType "application/json" `
  -Body '{"start_date":"2026-01-01","end_date":"2026-03-31","force":true}'
```

백필 요청은 내부적으로 월 단위로 분할되어 실행되며, 응답도 월별 실행 결과 리스트를 반환합니다.

</details>

---

## Web UI

운영자는 기본 Swagger/API 호출 없이 다음 read-only 화면으로 현재 상태를 바로 확인할 수 있습니다.

| Path | 용도 |
|------|------|
| `/monitor` | 파이프라인별 최신 실행 상태와 최근 실행 이력 |
| `/monitor/analytics?dataset=mes_ops` | KPI, 차트, drilldown preview |
| `/monitor/exports` | export job 상태, 만료 시각, 다운로드 |

- 언어 전환: `?lang=ko` 또는 `?lang=en`
- `/monitor/analytics`에서 현재 필터 상태로 export job을 바로 생성 가능

---

## Storage Layout

### Parquet 출력

```
{parquet_base_path}/{TABLE_NAME}/year={YYYY}/month={MM}/
├── PRODUCTION_LOG_2026_03.parquet
├── PRODUCTION_LOG_2026_03.part00001.parquet
└── PRODUCTION_LOG_2026_03.part00002.parquet
```

### DuckDB Mart

```
{mart_root}/
├── staging/       # 빌드 중 임시 DB
├── current/       # 검증 통과한 최신 mart
└── snapshots/     # 롤백용 이전 버전 보관
```

### Analytics Export

```
{mart_root_parent}/exports/
├── jobs/{job_id}.json
└── artifacts/{generated_file}
```

### SQLite 메타데이터

- `pipeline_runs` — 파이프라인 실행 단위 메타데이터
- `step_runs` — 단계별 상태, 재시도 횟수, 처리 건수, 오류 메시지

---

## Project Structure

```
src/airflow_lite/
├── __main__.py              # CLI 진입점
├── bootstrap.py             # 런타임 서비스 팩토리
├── dag_api.py               # DAG 파일용 Pipeline 정의 API
├── alerting/                # 이메일·웹훅 알림
├── analytics/               # KPI 계산, 차트/대시보드 카탈로그
├── api/                     # FastAPI 앱 팩토리, 라우트
│   └── routes/              #   pipelines, backfill, analytics
├── config/                  # YAML + DAG 설정 로더
├── engine/                  # 파이프라인 실행, 전략, 상태 전이, 백필
├── executor/                # 로컬 워커 풀
├── export/                  # 비동기 analytics export (xlsx/csv/parquet)
├── extract/                 # Oracle 연결, 청크 리더
├── i18n/                    # 다국어 지원 (en, ko)
├── logging_config/          # 구조화된 로깅 설정
├── mart/                    # DuckDB build, refresh, snapshot, validation
├── query/                   # 조회 SQL 생성, 필터, 페이징
├── scheduler/               # APScheduler 래퍼
├── service/                 # Windows Service 래퍼
├── storage/                 # SQLite 초기화, 모델, 리포지토리
└── transform/               # Parquet 쓰기, append, 백업/복원
```

---

## Testing

```bash
# 단위 테스트
pytest tests/ -q

# 통합 테스트 제외
pytest tests/ -m "not integration" -q

# 커버리지
pytest --cov=src/airflow_lite --cov-report=term-missing

# 통합 테스트 (실제 Oracle 환경 필요)
pytest -m integration
```

---

## Contributing

- 구현된 런타임 동작과 `README.md`를 일치시킬 것
- 운영 동작이 바뀌면 아키텍처·요구사항 문서도 함께 갱신
- 변경 전후 `pytest` 실행
- 새 기능에는 최소 1개 이상 테스트 추가
- GitHub 라벨 정책을 바꾸면 `.github/labels.json` 수정 후 `label-sync`로 동기화

---

## Documentation

| 문서 | 설명 |
|------|------|
| [`docs/airflow-lite-user-manual.md`](docs/airflow-lite-user-manual.md) | 운영자/사용자용 설치 후 사용 절차 매뉴얼 |
| [`spec/architecture.md`](spec/architecture.md) | 현재 구현 기준 아키텍처 상세 |
| [`spec/requirements.md`](spec/requirements.md) | 요구사항 원문 |
| [`spec/mart-refresh-design.md`](spec/mart-refresh-design.md) | Parquet → DuckDB mart refresh handoff 설계 |
| [`spec/query-api-contract.md`](spec/query-api-contract.md) | summary/chart/filter API 계약 |
| [`.github/labels.json`](.github/labels.json) | GitHub label catalog source of truth |
