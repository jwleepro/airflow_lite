# Airflow Lite

Airflow Lite는 Oracle 11g 데이터를 Parquet로 적재하고 실행 이력을 SQLite에 기록하는 경량 파이프라인 서비스입니다.

이 프로젝트는 복잡한 분산 오케스트레이터 없이도 정기 배치 추출, 간단한 백필, 운영 가시성이 필요한 팀을 대상으로 합니다. 이 README는 현재 저장소에 구현된 동작을 기준으로 작성되어 있습니다.

**Table of contents**

- [Project Focus](#project-focus)
- [Core Features](#core-features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation Options](#installation-options)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [API](#api)
- [Storage Layout](#storage-layout)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [Documentation](#documentation)

## Project Focus

Airflow Lite는 다음과 같은 상황에서 가장 잘 맞습니다:

- 소스 시스템이 Oracle 11g이고 배치 추출이 핵심 요구사항일 때
- 파이프라인 구조가 비교적 고정적이고 자주 바뀌지 않을 때
- 단일 Windows Server 운영 모델이 허용될 때
- 월별 또는 일별 Parquet 산출물만으로 downstream 분석이나 아카이빙이 가능할 때

Airflow Lite는 Apache Airflow를 대체하려는 프로젝트가 아닙니다. 분산 실행, DAG 저작, 범용 워크플로 오케스트레이션을 목표로 하지 않습니다. 대신 Oracle-to-Parquet 이관, 경량 스케줄링, 실행 이력 추적이라는 좁고 명확한 운영 시나리오에 집중합니다.

## Core Features

- `${ENV_VAR}` 치환을 지원하는 YAML 기반 설정
- `oracledb` thick mode 기반 Oracle 11g 연결
- 대용량 테이블 메모리 사용량을 낮추기 위한 청크 단위 추출
- `full`, `incremental` 두 가지 마이그레이션 전략
- SQLite 기반 파이프라인 및 단계 실행 이력 저장
- 재시도와 상태 전이를 포함한 stage 기반 실행 모델
- APScheduler 기반 스케줄링
- 수동 실행, 백필, 실행 이력 조회를 위한 FastAPI 엔드포인트
- 장기 실행을 위한 Windows Service 래퍼
- 이메일 및 웹훅 알림 채널

## Requirements

| 항목 | 내용 |
| --- | --- |
| Python | 3.11+ |
| OS | Windows Server 또는 Windows 서비스 실행이 가능한 환경 |
| Oracle client | Oracle 11g thick mode 연결을 위한 Oracle Client 또는 Instant Client |
| 기본 의존성 | `oracledb`, `pyarrow`, `pandas`, `tenacity`, `pyyaml` |
| 서비스/API 추가 의존성 | `apscheduler`, `fastapi`, `uvicorn`, `sqlalchemy`, `httpx`, `pywin32` |

Oracle 11g 환경에서는 사실상 `oracledb` thick mode 사용을 전제로 봐야 합니다. `oracle_home`이 설정되어 있으면 서비스가 Oracle Client 초기화를 자동으로 시도합니다.

## Quick Start

1. 서비스 런타임 의존성을 설치합니다.

```bash
pip install -e ".[phase2]"
```

2. `config/pipelines.yaml`을 준비합니다.

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
```

3. 필요한 환경변수를 설정합니다.

```powershell
$env:ORACLE_HOST = "db.example.local"
$env:ORACLE_PORT = "1521"
$env:ORACLE_SERVICE = "MESDB"
$env:ORACLE_USER = "mesmgr"
$env:ORACLE_PASSWORD = "secret"
```

4. Windows 서비스를 설치하고 시작합니다.

```powershell
python -m airflow_lite service install
python -m airflow_lite service start
```

중지 또는 제거가 필요하면 다음 명령을 사용합니다.

```powershell
python -m airflow_lite service stop
python -m airflow_lite service remove
```

5. 서비스 기동 여부를 확인합니다.

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI 스키마: `http://localhost:8000/openapi.json`
- 파이프라인 목록: `http://localhost:8000/api/v1/pipelines`

선택적으로 DuckDB mart 계획 훅을 켜려면 아래와 같이 `mart` 섹션을 추가합니다.

```yaml
mart:
  enabled: true
  root_path: "D:/data/mart"
  refresh_on_success: true
  pipeline_datasets:
    production_log: "mes_ops"
    equipment_status: "mes_ops"
```

## Installation Options

핵심 엔진 의존성만 설치:

```bash
pip install -e .
```

스케줄러, API, Windows 서비스 런타임 포함:

```bash
pip install -e ".[phase2]"
```

개발 및 테스트 도구 포함:

```bash
pip install -e ".[dev]"
```

전체 개발 환경 설치:

```bash
pip install -e ".[phase2,dev]"
```

## Configuration

기본 설정 파일 경로는 `config/pipelines.yaml`입니다.

### Configuration Notes

- `${VAR_NAME}` 패턴과 일치하는 문자열 값은 프로세스 환경변수로 치환됩니다.
- `api`, `alerting` 섹션은 선택 사항이며, 없으면 기본값이 적용됩니다.
- `strategy`는 `full` 또는 `incremental`이어야 합니다.
- `incremental` 파이프라인은 정상 동작을 위해 `incremental_key`를 정의해야 합니다.
- `oracle.port`, `defaults.chunk_size`, `api.port`, 파이프라인별 `chunk_size` 같은 정수 필드는 로딩 시 자동으로 정수 변환됩니다.

### Optional Sections

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

## How It Works

서비스 런타임은 다음 흐름으로 동작합니다:

1. `config/pipelines.yaml`에서 설정을 로드합니다.
2. 로깅과 SQLite 메타데이터 데이터베이스를 초기화합니다.
3. APScheduler에 스케줄 작업을 등록합니다.
4. FastAPI 애플리케이션을 백그라운드 스레드에서 시작합니다.
5. `PipelineRunner`를 통해 각 파이프라인을 실행합니다.

현재 각 파이프라인은 두 개의 stage로 구성됩니다:

- `extract_transform_load`
- `verify`

전략별 실행 방식:

- `full`: 대상 월 전체를 읽고 월 단위 Parquet 산출물을 새로 씁니다.
- `incremental`: `incremental_key` 기준으로 요청한 실행일 데이터만 읽고 월 디렉터리에 append 합니다.

멱등성 동작:

- `force_rerun`이 아니면 동일 파이프라인과 실행일의 성공 실행은 재사용됩니다.
- 실행 메타데이터는 `pipeline_runs`, `step_runs`에 저장됩니다.

## API

서비스가 실행 중이면 다음 엔드포인트를 사용할 수 있습니다:

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/api/v1/pipelines` | 설정된 파이프라인 목록 조회 |
| `POST` | `/api/v1/pipelines/{name}/trigger` | 수동 실행 |
| `POST` | `/api/v1/pipelines/{name}/backfill` | 월 단위 분할 백필 실행 |
| `GET` | `/api/v1/pipelines/{name}/runs` | 페이지네이션 실행 이력 조회 |
| `GET` | `/api/v1/pipelines/{name}/runs/{run_id}` | 단계 상태를 포함한 실행 상세 조회 |

수동 실행 예시:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/trigger" `
  -ContentType "application/json" `
  -Body '{"execution_date":"2026-03-01","force":false}'
```

백필 예시:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/backfill" `
  -ContentType "application/json" `
  -Body '{"start_date":"2026-01-01","end_date":"2026-03-31","force":true}'
```

백필 요청은 내부적으로 월 단위로 분할되어 실행되며, 응답도 월별 실행 결과 리스트를 반환합니다.

## Storage Layout

Parquet 출력은 테이블과 월 기준으로 정리됩니다:

```text
{parquet_base_path}/{TABLE_NAME}/year={YYYY}/month={MM}/
```

대표 파일명 예시:

```text
PRODUCTION_LOG_2026_03.parquet
PRODUCTION_LOG_2026_03.part00001.parquet
PRODUCTION_LOG_2026_03.part00002.parquet
```

SQLite 메타데이터 테이블:

- `pipeline_runs`: 파이프라인 실행 단위 메타데이터
- `step_runs`: 단계별 상태, 재시도 횟수, 처리 건수, 오류 메시지

## Project Structure

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

주요 모듈:

- `engine/pipeline.py`: 파이프라인 순차 실행과 재시도 오케스트레이션
- `engine/strategy.py`: `FullMigrationStrategy`, `IncrementalMigrationStrategy`
- `engine/state_machine.py`: 단계 상태 전이 검증
- `extract/oracle_client.py`: Oracle 연결과 예외 분류
- `extract/chunked_reader.py`: `fetchmany()` 기반 스트리밍 읽기
- `transform/parquet_writer.py`: Parquet 쓰기, append, 백업/복원 헬퍼
- `storage/database.py`: SQLite 초기화와 스키마 부트스트랩
- `service/win_service.py`: 서비스 런타임 조립

## Testing

단위 테스트 실행:

```bash
pytest -q --basetemp .tmp_pytest -p no:cacheprovider
```

커버리지 실행:

```bash
pytest --cov=src/airflow_lite --cov-report=term-missing
```

통합 테스트는 실제 Oracle 환경이 필요합니다:

```bash
pytest -m integration
```

## Contributing

동작 방식이나 설정 계약을 변경했다면 코드와 함께 문서도 같이 갱신하는 편이 좋습니다. 최소한 다음 항목은 맞춰두는 것을 권장합니다:

- 구현된 런타임 동작과 `README.md`를 일치시킬 것
- 운영 동작이 바뀌면 아키텍처 또는 요구사항 문서도 함께 갱신할 것
- 변경 전후 관련 `pytest` 명령을 실행할 것
- GitHub 라벨 정책을 바꾸면 `.github/labels.json`을 수정하고 `label-sync` 경로로 실제 저장소 라벨도 맞출 것

## Documentation

- [`spec/architecture.md`](spec/architecture.md): 현재 구현 기준 아키텍처 상세
- [`spec/requirements.md`](spec/requirements.md): 요구사항 원문
- [`spec/integration-test.md`](spec/integration-test.md): 통합 테스트 체크리스트
- [`spec/mart-refresh-design.md`](spec/mart-refresh-design.md): Parquet -> DuckDB mart refresh handoff 설계
- [`spec/query-api-contract.md`](spec/query-api-contract.md): summary/chart/filter API 계약 초안
- [`.github/labels.json`](.github/labels.json): GitHub label catalog source of truth
