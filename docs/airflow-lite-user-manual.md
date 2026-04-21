# airflow_lite 사용자 매뉴얼

## 1. 문서 목적

이 문서는 `airflow_lite`를 실제 운영자가 설치 후 사용하는 기준 절차를 설명한다.
대상 범위는 다음과 같다.

- Windows Server 2019 환경에서 서비스 기동
- 파이프라인 상태 확인
- 수동 실행과 백필 실행
- 분석 대시보드와 export 사용
- 기본 장애 확인과 운영 점검

개발 구조나 내부 설계가 필요하면 [README.md](../README.md)와 `spec/` 문서를 함께 본다.

## 2. 시스템 개요

`airflow_lite`는 Oracle 11g 데이터를 배치로 추출해 Parquet에 적재하고, 필요 시 DuckDB mart를 갱신한 뒤 FastAPI와 Web UI로 결과를 제공하는 운영 시스템이다.

전체 흐름은 다음과 같다.

```text
Oracle 11g -> Parquet raw -> DuckDB mart -> FastAPI -> Web UI
```

운영자가 주로 사용하는 대상은 아래 네 가지다.

- Windows 서비스
- Web UI 운영 화면
- API 엔드포인트
- 로그 및 산출물 디렉터리

## 3. 사전 준비

운영 전에 아래 항목을 확인한다.

- OS: Windows Server 2019
- Python: 3.11 이상
- Oracle Client 또는 Instant Client 설치
- Oracle 접속 정보 확보
- 서비스 계정의 파일 경로 접근 권한 확인
- 방화벽에서 API 포트 접근 가능 여부 확인

주요 입력 파일은 `config/pipelines.yaml`과 `dags/*.py`이다.

## 4. 주요 경로와 구성요소

### 4.1 설정 파일

- `config/pipelines.yaml`: Oracle 연결, 저장 경로, defaults, API, alerting, mart 설정
- `dags/*.py`: 파이프라인 정의 source of truth

### 4.2 주요 데이터 경로

- Parquet raw: `{parquet_base_path}/{TABLE_NAME}/year={YYYY}/month={MM}/`
- SQLite 실행 이력: `{sqlite_path}`
- 로그: `{log_path}`
- Mart: `{mart.root_path}/staging`, `{mart.root_path}/current`, `{mart.root_path}/snapshots`
- Export: mart 상위 경로 기준 `exports/jobs`, `exports/artifacts`

### 4.3 주요 화면

- `/monitor`: 홈 화면
- `/monitor/pipelines`: 파이프라인 목록
- `/monitor/pipelines/{name}`: 파이프라인 상세
- `/monitor/pipelines/{name}/runs/{run_id}`: 실행 상세
- `/monitor/analytics?dataset=...`: 분석 대시보드
- `/monitor/exports`: export 작업 화면
- `/monitor/admin`: 운영 관리 화면

## 5. 설치와 최초 실행

### 5.1 패키지 설치

운영 서버에서 프로젝트 루트 기준으로 실행한다.

```powershell
pip install -e ".[phase2]"
```

개발/테스트 도구까지 필요하면 다음 명령을 사용한다.

```powershell
pip install -e ".[phase2,dev]"
```

### 5.2 설정 파일 준비

`config/pipelines.yaml`에 최소 아래 항목이 있어야 한다.

- `oracle`
- `storage`
- `defaults`
- 필요 시 `mart`, `api`, `alerting`, `webui`

예시:

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

주의:

- `${...}` 값은 환경변수로 치환된다.
- 경로는 서비스 계정이 읽기/쓰기 가능해야 한다.

### 5.3 DAG 파일 준비

파이프라인 등록은 Admin UI가 아니라 `dags/*.py` 코드로 수행한다.

예시: `dags/default.py`

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

운영 규칙:

- `pipelines` 리스트를 모듈 전역으로 노출해야 한다.
- 각 항목은 `Pipeline` 또는 `PipelineConfig` 타입이어야 한다.
- `_`로 시작하는 파일은 기본적으로 로드되지 않는다(`_migrated.py` 제외).
- `AIRFLOW_LITE_DAGS_DIR` 환경변수로 DAG 디렉터리를 오버라이드할 수 있다.

### 5.4 포그라운드 실행

개발 또는 최초 점검 시에는 포그라운드 실행이 가장 단순하다.

```powershell
python -m airflow_lite run
```

특정 설정 파일을 직접 지정하려면:

```powershell
python -m airflow_lite run D:\path\to\pipelines.yaml
```

정상 기동 시 API와 스케줄러가 함께 올라온다.

### 5.5 Windows 서비스 설치

운영 환경에서는 Windows 서비스로 실행하는 것을 기본으로 한다.

```powershell
python -m airflow_lite service install
python -m airflow_lite service start
```

중지와 제거:

```powershell
python -m airflow_lite service stop
python -m airflow_lite service remove
```

## 6. 기동 후 확인

서비스 또는 포그라운드 실행 후 다음 URL을 확인한다.

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- 파이프라인 API: `http://localhost:8000/api/v1/pipelines`
- 홈 화면: `http://localhost:8000/monitor`
- 분석 화면: `http://localhost:8000/monitor/analytics?dataset=mes_ops`
- export 화면: `http://localhost:8000/monitor/exports`

언어 전환은 `lang` 쿼리 파라미터로 가능하다.

- 한국어: `?lang=ko`
- 영어: `?lang=en`

## 7. Web UI 사용 방법

### 7.1 Home 화면

`/monitor`는 전체 운영 상태를 한 번에 보는 시작 화면이다.

여기서 확인할 수 있는 내용:

- 파이프라인별 최신 상태
- 최근 실행 이력
- 기본 health check 상태

먼저 이 화면에서 장애 징후가 있는지 본 뒤, 문제가 있는 파이프라인 상세로 이동한다.

### 7.2 DAGs 화면

`/monitor/pipelines`에서는 파이프라인 목록을 조회한다.

주요 기능:

- 파이프라인 검색
- 최신 실행 상태 필터
- 상세 화면 이동

상태가 `warn` 또는 `bad`인 파이프라인부터 확인하는 것을 권장한다.

### 7.3 DAG Details 화면

`/monitor/pipelines/{name}`에서는 특정 파이프라인의 최근 실행과 구성 정보를 확인한다.

주요 작업:

- 수동 실행
- force rerun 실행
- 백필 실행
- 최근 실행 이력 확인

백필 입력 시 유의사항:

- `start_date`, `end_date`는 `YYYY-MM-DD` 형식이어야 한다.
- 내부적으로 월 단위로 분할 실행된다.
- 범위가 길수록 실행 건수가 많아진다.

### 7.4 Dag Run 화면

`/monitor/pipelines/{name}/runs/{run_id}`에서는 특정 실행 건의 세부 내용을 확인한다.

주요 확인 항목:

- 전체 실행 상태
- 단계별 상태
- 실행 시간
- 파이프라인 메타데이터
- 최근 실행과의 비교

실패가 있으면 이 화면과 로그를 함께 본다.

### 7.5 Analytics 화면

`/monitor/analytics`는 DuckDB mart 기반 분석 화면이다.

사용 방법:

1. dataset을 선택한다.
2. 필터를 적용한다.
3. KPI와 차트를 확인한다.
4. 필요한 경우 detail preview를 본다.
5. 동일 조건으로 export를 생성한다.

주의:

- 이 화면은 Oracle 직접 조회가 아니라 DuckDB mart를 사용한다.
- mart가 최신이 아니면 화면 데이터도 최신이 아닐 수 있다.

### 7.6 Exports 화면

`/monitor/exports`는 export 작업 상태를 보는 화면이다.

여기서 할 수 있는 작업:

- 작업 상태 확인
- 완료 파일 다운로드
- 개별 작업 삭제
- 완료된 작업 일괄 정리

대용량 데이터는 `csv.zip` 또는 `parquet` 사용을 권장한다.
소규모 결과만 `xlsx`를 사용하는 것이 안전하다.

### 7.7 Admin 화면

`/monitor/admin`에서는 운영용 메타데이터를 관리한다.

현재 화면에서 다루는 주요 대상:

- connections
- variables
- pools

파이프라인 정의 변경은 Admin 화면이 아니라 DAG 파일 배포로 수행한다.

## 8. 수동 실행 방법

### 8.1 Web UI에서 수동 실행

1. `/monitor/pipelines` 또는 상세 화면으로 이동한다.
2. 대상 파이프라인을 선택한다.
3. `trigger` 또는 `force rerun`을 실행한다.
4. 실행 후 Dag Run 화면으로 이동해 결과를 확인한다.

`force rerun`은 기존 성공 실행이 있어도 다시 수행한다.
중복 실행 비용이 있으므로 일반 실행과 구분해서 사용한다.

### 8.2 API로 수동 실행

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/trigger" `
  -ContentType "application/json" `
  -Body '{"execution_date":"2026-03-01","force":false}'
```

응답에는 실행 ID와 단계 정보가 포함된다.

## 9. 백필 실행 방법

### 9.1 Web UI에서 백필 실행

1. `/monitor/pipelines/{name}`로 이동한다.
2. 시작일과 종료일을 입력한다.
3. 필요 시 `force` 옵션을 선택한다.
4. 실행 후 최근 run 목록에서 월별 생성 run을 확인한다.

### 9.2 API로 백필 실행

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/pipelines/production_log/backfill" `
  -ContentType "application/json" `
  -Body '{"start_date":"2026-01-01","end_date":"2026-03-31","force":true}'
```

이 요청은 월 단위로 분할되어 여러 실행을 생성한다.

## 10. Export 사용 방법

Export는 분석 화면의 현재 필터 기준으로 생성하는 흐름이 가장 일반적이다.

기본 절차:

1. `/monitor/analytics`에서 dataset과 필터를 선택한다.
2. export를 생성한다.
3. `/monitor/exports`로 이동한다.
4. 상태가 완료되면 artifact를 다운로드한다.

운영 기준 권장 포맷:

- 소량 데이터: `xlsx`
- 대량 데이터: `csv.zip`
- 후속 분석 연계: `parquet`

## 11. 운영 점검 체크리스트

매일 또는 배치 확인 시 아래 순서로 점검한다.

1. `/monitor`에서 전체 상태와 health check를 본다.
2. 실패 또는 경고 상태 파이프라인을 확인한다.
3. 필요 시 파이프라인 상세에서 최근 run 흐름을 본다.
4. Dag Run 화면에서 단계별 상태를 확인한다.
5. 로그 파일과 SQLite 실행 이력을 대조한다.
6. analytics 화면 데이터가 최신 배치 기준인지 확인한다.
7. export 누적 파일이 과도하면 정리한다.

## 12. 장애 대응 가이드

### 12.1 서비스가 올라오지 않을 때

확인 항목:

- Python 패키지 설치 누락 여부
- Oracle Client 경로와 환경변수 설정
- `config/pipelines.yaml` 문법 오류
- `dags/*.py` 문법/임포트 오류
- 서비스 계정 권한
- 포트 충돌 여부

먼저 포그라운드 모드로 실행해 오류 메시지를 직접 보는 것이 빠르다.

```powershell
python -m airflow_lite run
```

### 12.2 파이프라인 실행이 실패할 때

우선 확인 순서:

1. Dag Run 화면에서 실패 단계 확인
2. 로그 파일 확인
3. Oracle 접속 가능 여부 확인
4. 대상 경로 쓰기 권한 확인
5. 동일 일자 성공 이력과 비교

### 12.3 Analytics 화면이 비어 있을 때

가능한 원인:

- mart refresh가 실행되지 않음
- dataset 이름이 잘못됨
- 필터 조건이 과도함
- 현재 mart가 최신 스냅샷이 아님

이 경우 raw 적재 성공 여부와 mart 현재 디렉터리 갱신 여부를 같이 확인한다.

### 12.4 Export가 완료되지 않을 때

확인 항목:

- export job 상태
- artifact 경로 쓰기 권한
- 필터 조건으로 인한 과도한 데이터량
- 임시 파일 잠금 여부

## 13. 로그와 산출물 확인 위치

운영 중 자주 보는 대상은 아래와 같다.

- 실행 로그: `storage.log_path`
- Parquet 산출물: `storage.parquet_base_path`
- 실행 메타데이터: `storage.sqlite_path`
- mart 현재본: `mart.root_path/current`
- mart 스냅샷: `mart.root_path/snapshots`
- export 결과물: `exports/artifacts`

문제 재현 시에는 실행 시간, pipeline 이름, run ID를 같이 기록한다.

## 14. 권장 운영 절차

변경 작업은 아래 순서로 하는 것이 안전하다.

1. `config/pipelines.yaml` 또는 `dags/*.py` 수정
2. 포그라운드 모드 또는 테스트 환경에서 점검
3. 서비스 재시작
4. `/monitor`에서 상태 확인
5. 필요 시 수동 trigger로 단건 검증
6. analytics와 export까지 최종 확인

## 15. 참고 문서

- [README.md](../README.md)
- [spec/architecture.md](../spec/architecture.md)
- [spec/requirements.md](../spec/requirements.md)
- [spec/mart-refresh-design.md](../spec/mart-refresh-design.md)
- [spec/query-api-contract.md](../spec/query-api-contract.md)
