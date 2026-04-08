# Airflow Lite

Oracle 11g 데이터를 Parquet로 적재하고, DuckDB 기반 분석 mart를 서빙하는 경량 배치 파이프라인 서비스입니다.

<!-- Badges -->
| | |
| --- | --- |
| **Package** | `pip install -e ".[phase2]"` · Python 3.11+ |
| **Runtime** | Windows Server 2019 · Oracle 11g thick mode · DuckDB |
| **License** | Internal |

## Table of Contents

- [Project Focus](#project-focus)
- [Core Features](#core-features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [API Reference](#api-reference)
- [Operational Monitoring](#operational-monitoring)
- [Storage Layout](#storage-layout)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [Documentation](#documentation)

## Project Focus

Airflow Lite는 다음과 같은 상황에서 가장 잘 맞습니다:

- 소스 시스템이 Oracle 11g이고 배치 추출이 핵심 요구사항일 때
- 운영 Oracle 부하를 줄이고 DuckDB 기반 분석/조회를 제공해야 할 때
- 단일 Windows Server 운영 모델이 허용될 때
- 월별 또는 일별 Parquet 산출물과 집계 중심 대시보드가 필요할 때

> **Apache Airflow를 대체하려는 프로젝트가 아닙니다.**
> 분산 실행, DAG 저작, 범용 워크플로 오케스트레이션을 목표로 하지 않습니다.
> Oracle → Parquet 이관, DuckDB mart 서빙, 경량 스케줄링, 실행 이력 추적이라는
> 좁고 명확한 운영 시나리오에 집중합니다.

## Core Features

| 영역 | 기능 |
| --- | --- |
| **Ingest** | `oracledb` thick mode 기반 Oracle 11g 연결, 청크 단위 추출, `full`/`incremental` 전략 |
| **Storage** | 월 단위 Parquet 산출물, SQLite 실행 이력, 재시도·상태 전이 포함 stage 기반 실행 모델 |
| **Mart** | Parquet → DuckDB staging build → validation → snapshot promotion |
| **Analytics** | KPI summary, chart 시리즈, detail 페이징, dashboard 정의, 필터 메타데이터 |
| **Export** | 비동기 export job 생성 (xlsx, csv.zip, parquet), artifact 다운로드 |
| **Web UI** | `/monitor` 파이프라인 모니터, `/monitor/analytics` 대시보드 뷰, `/monitor/exports` export job 운영 화면 |
| **Scheduling** | APScheduler cron 스케줄링, 수동 실행, 월 단위 백필 |
| **API** | FastAPI 엔드포인트 (파이프라인 관리 + analytics 조회 + export) |
| **Alerting** | 이메일 및 웹훅 알림 채널 |
| **Service** | Windows Service 래퍼를 통한 장기 실행 |

## Requirements

| 항목 | 내용 |
| --- | --- |
| Python | 3.11+ |
| OS | Windows Server 2019 이상 |
| Oracle client | Oracle 11g thick mode 연결을 위한 Oracle Client 또는 Instant Client |
| 기본 의존성 | `oracledb`, `duckdb`, `pyarrow`, `pandas`, `tenacity`, `pyyaml` |
| 서비스/API 추가 | `apscheduler`, `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `httpx`, `pywin32` |

## Quick Start

**1. 서비스 런타임 의존성 설치**

```bash
pip install -e ".[phase2]"
```

**2. `config/pipelines.yaml` 준비**

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
  retry:
    max_attempts: 3
    min_wait_seconds: 4
    max_wait_seconds: 60
  parquet:
    compression: "snappy"

pipelines:
  - name: "production_log"
    table: "PRODUCTION_LOG"
    partition_column: "LOG_DATE"
    strategy: "full"
    schedule: "0 2 * * *"

mart:
  enabled: true
  root_path: "D:/data/mart"
  refresh_on_success: true
  pipeline_datasets:
    production_log: "mes_ops"
```

**3. Windows 서비스 설치 및 시작**

```powershell
python -m airflow_lite service install
python -m airflow_lite service start
```

중지 또는 제거:

```powershell
python -m airflow_lite service stop
python -m airflow_lite service remove
```

**4. 기동 확인**

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI 스키마: `http://localhost:8000/openapi.json`
- 파이프라인 목록: `http://localhost:8000/api/v1/pipelines`
- 운영 모니터: `http://localhost:8000/monitor`
- 분석 대시보드 뷰: `http://localhost:8000/monitor/analytics?dataset=mes_ops`
- export job 모니터: `http://localhost:8000/monitor/exports`
- 언어 전환 예시: `http://localhost:8000/monitor?lang=ko` (`en`, `ko` 지원)

## Installation

| 대상 | 명령 |
| --- | --- |
| 핵심 엔진만 | `pip install -e .` |
| 스케줄러 + API + Windows 서비스 | `pip install -e ".[phase2]"` |
| 개발·테스트 도구 포함 | `pip install -e ".[dev]"` |
| 전체 개발 환경 | `pip install -e ".[phase2,dev]"` |

## Configuration

기본 설정 파일 경로: `config/pipelines.yaml`

### 설정 규칙

- `${VAR_NAME}` 패턴은 프로세스 환경변수로 치환됩니다.
- `strategy`는 `full` 또는 `incremental`이어야 합니다.
- `incremental` 파이프라인은 `incremental_key`를 정의해야 합니다.
- 정수 필드(`oracle.port`, `defaults.chunk_size`, `api.port` 등)는 로딩 시 자동 변환됩니다.
- `api`, `alerting`, `mart` 섹션은 선택 사항이며, 없으면 기본값이 적용됩니다.
- `webui.default_language`는 `en` 또는 `ko`만 허용되며 기본값은 `en`입니다.

### 선택 섹션

<details>
<summary>API / Alerting 설정 예시</summary>

```yaml
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
```

</details>

## How It Works

### 아키텍처

```
Oracle 11g → [ingest] → Parquet raw → [mart] → DuckDB → [serve] → FastAPI → Web UI
```

### 서비스 런타임 흐름

1. `config/pipelines.yaml`에서 설정 로드
2. 로깅과 SQLite 메타데이터 데이터베이스 초기화
3. APScheduler에 스케줄 작업 등록
4. FastAPI 애플리케이션을 백그라운드 스레드에서 시작
5. `PipelineRunner`를 통해 각 파이프라인 실행

### 파이프라인 stage

각 파이프라인은 두 개의 stage로 구성됩니다:

1. `extract_transform_load` — Oracle에서 데이터 추출 후 Parquet 적재
2. `verify` — 산출물 검증

`mart.enabled: true`와 `mart.refresh_on_success: true`가 함께 설정되면, raw Parquet 실행 성공 후 DuckDB mart staging build → validation → snapshot promotion이 이어서 실행됩니다.

### 전략별 동작

| 전략 | 동작 |
| --- | --- |
| `full` | 대상 월 전체를 읽고 월 단위 Parquet를 새로 작성 |
| `incremental` | `incremental_key` 기준으로 실행일 데이터만 읽고 월 디렉터리에 append |

### 멱등성

- `force_rerun`이 아니면 동일 파이프라인+실행일의 성공 실행은 재사용
- 실행 메타데이터는 `pipeline_runs`, `step_runs` 테이블에 저장

## API Reference

### 파이프라인 관리

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/api/v1/pipelines` | 설정된 파이프라인 목록 조회 |
| `POST` | `/api/v1/pipelines/{name}/trigger` | 수동 실행 |
| `POST` | `/api/v1/pipelines/{name}/backfill` | 월 단위 분할 백필 실행 |
| `GET` | `/api/v1/pipelines/{name}/runs` | 페이지네이션 실행 이력 조회 |
| `GET` | `/api/v1/pipelines/{name}/runs/{run_id}` | 단계 상태를 포함한 실행 상세 조회 |

### Analytics 조회

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/v1/analytics/summary` | KPI 요약 조회 |
| `POST` | `/api/v1/analytics/charts/{chart_id}/query` | 차트 시리즈 조회 |
| `POST` | `/api/v1/analytics/details/{detail_key}/query` | 상세 그리드 조회 (페이징) |
| `GET` | `/api/v1/analytics/filters` | dataset별 필터 메타데이터 조회 |
| `GET` | `/api/v1/analytics/dashboards/{dashboard_id}` | dashboard widget/action 메타데이터 조회 |

### Export

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/v1/analytics/exports` | 비동기 export job 생성 |
| `GET` | `/api/v1/analytics/exports/{job_id}` | export job 상태 조회 |
| `GET` | `/api/v1/analytics/exports/{job_id}/download` | 완료된 export artifact 다운로드 |

### 사용 예시

<details>
<summary>수동 실행</summary>

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/trigger" `
  -ContentType "application/json" `
  -Body '{"execution_date":"2026-03-01","force":false}'
```

</details>

<details>
<summary>백필</summary>

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/backfill" `
  -ContentType "application/json" `
  -Body '{"start_date":"2026-01-01","end_date":"2026-03-31","force":true}'
```

백필 요청은 내부적으로 월 단위로 분할되어 실행되며, 응답도 월별 실행 결과 리스트를 반환합니다.

</details>

## Operational Monitoring

운영자는 기본 Swagger/API 호출 없이 다음 read-only 화면으로 현재 상태를 바로 확인할 수 있습니다.
현재 `/monitor` 계열 화면은 Airflow 운영 콘솔의 밀도 높은 listing/table 감각을 참고하되, 이 저장소의 pipeline, analytics, export 모델에 맞춰 재구성되어 있습니다.

| Path | 용도 |
| --- | --- |
| `/monitor` | 파이프라인별 최신 실행 상태와 최근 실행 이력 확인 |
| `/monitor/analytics?dataset=mes_ops` | `operations_overview` dashboard contract를 소비해 KPI, 차트, drilldown preview를 브라우저에서 확인 |
| `/monitor/exports` | async export job 상태, 만료 시각, 다운로드 가능 여부를 운영자 관점에서 확인 |

`/monitor/analytics` 화면에서는 현재 필터 상태로 export job을 바로 생성할 수 있고, 생성 후 `/monitor/exports`에서 상태와 artifact 다운로드 경로를 이어서 볼 수 있습니다.

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

## Project Structure

```
src/airflow_lite/
├── __main__.py              # CLI 진입점
├── alerting/                # 이메일·웹훅 알림
├── analytics/               # KPI 계산, 차트/대시보드 카탈로그
├── api/                     # FastAPI 앱 팩토리, 라우트
│   └── routes/              #   pipelines, backfill, analytics
├── config/                  # YAML 설정 로더
├── engine/                  # 파이프라인 실행, 전략, 상태 전이, 백필
├── export/                  # 비동기 analytics export (xlsx/csv/parquet)
├── extract/                 # Oracle 연결, 청크 리더
├── logging_config/          # 로깅 설정
├── mart/                    # DuckDB build, refresh, snapshot, validation
├── query/                   # 조회 SQL 생성, 필터, 페이징
├── scheduler/               # APScheduler 래퍼
├── service/                 # Windows Service 래퍼
├── storage/                 # SQLite 초기화, 모델, 리포지토리
└── transform/               # Parquet 쓰기, append, 백업/복원
```

## Testing

```bash
# 단위 테스트
pytest tests/ -q

# 커버리지
pytest --cov=src/airflow_lite --cov-report=term-missing

# 통합 테스트 (실제 Oracle 환경 필요)
pytest -m integration
```

## Contributing

- 구현된 런타임 동작과 `README.md`를 일치시킬 것
- 운영 동작이 바뀌면 아키텍처·요구사항 문서도 함께 갱신
- 변경 전후 `pytest` 실행
- GitHub 라벨 정책을 바꾸면 `.github/labels.json` 수정 후 `label-sync`로 동기화

## Documentation

| 문서 | 설명 |
| --- | --- |
| [`spec/architecture.md`](spec/architecture.md) | 현재 구현 기준 아키텍처 상세 |
| [`spec/requirements.md`](spec/requirements.md) | 요구사항 원문 |
| [`spec/mart-refresh-design.md`](spec/mart-refresh-design.md) | Parquet → DuckDB mart refresh handoff 설계 |
| [`spec/query-api-contract.md`](spec/query-api-contract.md) | summary/chart/filter API 계약 |
| [`.github/labels.json`](.github/labels.json) | GitHub label catalog source of truth |
