# Airflow Lite 통합 테스트 검수 명세서

## 1. 목적

이 문서는 `airflow_lite`가 패키징 배포된 뒤, 다른 프로젝트나 운영팀이 저장소 내부 구현을 몰라도 **설치 완료 이후 런타임이 정상 동작하는지** 검수할 수 있도록 만든 통합 테스트 명세서다.

대상 범위는 다음과 같다.

- Windows 서비스 기동
- YAML 설정 로드 및 환경변수 치환
- Oracle 11g → Parquet 이관 실행
- 스케줄러 및 수동 트리거
- 백필 실행
- 실행 이력 저장(SQLite)
- REST API 조회
- 성능 및 운영성 검증

대상 범위에 포함하지 않는 항목:

- 패키지 빌드 파이프라인 자체 검증
- 단위 테스트
- React 모니터링 대시보드

## 2. 현재 구현 기준 주의사항

이 문서는 설계 문서가 아니라 **현재 코드 기준**으로 작성한다. 검수자가 혼동하기 쉬운 차이는 아래와 같다.

- 현재 런타임 진입점은 사실상 Windows 서비스다.
  - 명령: `python -m airflow_lite service install|start|stop|remove`
- 실행 이력의 step은 문서상 4단계 개념이 아니라 실제 저장 기준으로 아래 2개를 본다.
  - `extract_transform_load`
  - `verify`
- Full 전략은 첫 번째 청크 적재 시 기존 Parquet 파일을 `.bak`로 백업한다.
- Incremental 전략은 월별 Parquet 파일에 append한다.
- 알림 채널 클래스는 구현되어 있지만 현재 서비스 런타임에 자동 연결되어 있지 않다.
  - 따라서 알림 시나리오는 `선택 검증`으로 분리한다.
- Full 전략의 `.bak` 파일은 현재 코드 기준으로 성공 후 자동 삭제/실패 후 자동 복원까지 완결되어 있지 않다.
  - 따라서 검수는 `.bak` 생성 여부와 덮어쓰기 안전성 중심으로 본다.
- API health endpoint는 없다.
  - 기동 확인은 `GET /api/v1/pipelines` 200 응답으로 대체한다.

## 3. 대상 환경

| 항목 | 기준 |
|------|------|
| OS | Windows Server 2019 이상 |
| Python | 3.11+ |
| Oracle | Oracle 11g, `oracledb` thick mode 가능 환경 |
| 실행 형태 | 단일 서버, 단일 프로세스, Windows 서비스 |
| 저장소 | 로컬 파일시스템 + SQLite |
| 네트워크 | 사내망 |

권장 검수 환경:

- 실제 운영과 분리된 검수 서버 1대
- 운영과 동일한 Oracle Client 설치 경로
- 실제 운영과 유사한 디스크 경로
- 운영과 분리된 검수용 Oracle schema 또는 검수 전용 table

## 4. 검수 전 준비

### 4.1 필수 런타임 자산

패키지 설치는 이미 끝났다고 가정한다. 검수 시작 전 아래 항목이 준비되어 있어야 한다.

- `airflow_lite` 실행 파일 또는 Python 패키지
- `config/pipelines.yaml`
- Oracle Client 또는 Oracle Home
- 검수용 Oracle 계정
- Parquet 저장 디렉터리
- SQLite 저장 디렉터리
- 로그 디렉터리

### 4.2 환경변수

최소 아래 환경변수를 준비한다.

```powershell
$env:ORACLE_HOST = "oracle-host"
$env:ORACLE_PORT = "1521"
$env:ORACLE_SERVICE = "ORCL"
$env:ORACLE_USER = "airflow_lite_test"
$env:ORACLE_PASSWORD = "********"
```

### 4.3 권장 검수용 설정 예시

```yaml
oracle:
  host: ${ORACLE_HOST}
  port: ${ORACLE_PORT}
  service_name: ${ORACLE_SERVICE}
  user: ${ORACLE_USER}
  password: ${ORACLE_PASSWORD}
  oracle_home: "D:/Oracle/product/11.2.0/client_1"

storage:
  parquet_base_path: "D:/airflow-lite-test/parquet"
  sqlite_path: "D:/airflow-lite-test/meta/airflow_lite.db"
  log_path: "D:/airflow-lite-test/logs"

defaults:
  chunk_size: 10000
  retry:
    max_attempts: 3
    min_wait_seconds: 4
    max_wait_seconds: 60
  parquet:
    compression: "snappy"

api:
  host: "127.0.0.1"
  port: 8000
  allowed_origins:
    - "http://10.10.10.5"

pipelines:
  - name: "production_log_full"
    table: "PRODUCTION_LOG_IT"
    partition_column: "LOG_DATE"
    strategy: "full"
    schedule: "*/10 * * * *"
    chunk_size: 20000

  - name: "equipment_status_inc"
    table: "EQUIPMENT_STATUS_IT"
    partition_column: "STATUS_DATE"
    strategy: "incremental"
    schedule: "*/15 * * * *"
    incremental_key: "UPDATED_AT"
```

### 4.4 권장 검수 데이터셋

동일한 시나리오를 반복 실행할 수 있도록 아래 3종 데이터를 준비한다.

| 데이터셋 | 용도 | 권장 규모 |
|------|------|------|
| Smoke | 기능 확인 | 월별 1,000행 |
| Standard | 회귀 검수 | 월별 100,000행, 3개월치 |
| Performance | 성능 검수 | 월별 1,000,000행 |

권장 컬럼 조건:

- 날짜 파티션 컬럼 1개
- 증분 기준 컬럼 1개
- 숫자/문자열 컬럼 혼합
- NULL 허용 컬럼 포함

### 4.5 서비스 기동 절차

관리자 권한 PowerShell에서 아래 순서로 진행한다.

```powershell
python -m airflow_lite service install
python -m airflow_lite service start
```

중지/정리:

```powershell
python -m airflow_lite service stop
python -m airflow_lite service remove
```

## 5. 공통 확인 방법

### 5.1 API 호출

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/pipelines"
```

수동 실행:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/pipelines/production_log_full/trigger" `
  -ContentType "application/json" `
  -Body '{"execution_date":"2026-03-01"}'
```

백필 실행:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/pipelines/production_log_full/backfill" `
  -ContentType "application/json" `
  -Body '{"start_date":"2026-01-01","end_date":"2026-03-31"}'
```

### 5.2 SQLite 확인

최근 실행:

```sql
SELECT id, pipeline_name, execution_date, status, trigger_type, started_at, finished_at
FROM pipeline_runs
ORDER BY created_at DESC;
```

특정 실행의 step:

```sql
SELECT pipeline_run_id, step_name, status, records_processed, retry_count, error_message
FROM step_runs
WHERE pipeline_run_id = '<run_id>'
ORDER BY created_at;
```

### 5.3 파일 결과 확인

Parquet 출력 경로:

```text
{parquet_base_path}/{TABLE_NAME}/year={YYYY}/month={MM}/{TABLE_NAME}_{YYYY}_{MM}.parquet
```

Full 전략 실행 전에 기존 파일이 있으면 아래 백업 파일이 생성된다.

```text
{TABLE_NAME}_{YYYY}_{MM}.bak
```

### 5.4 로그 확인

기본 로그 파일:

```text
{log_path}/airflow_lite.log
{log_path}/airflow_lite.log.YYYY-MM-DD
```

검수 시 반드시 아래 키워드를 확인한다.

- `oracledb thick mode`
- `파이프라인 등록`
- `스케줄러 시작됨`
- `백업 생성`
- `Retrying`
- `서비스 시작 실패`

### 5.5 성능 측정

아래 중 하나로 서비스 프로세스 메모리를 측정한다.

- 작업 관리자
- 리소스 모니터
- PerfMon
- PowerShell `Get-Process`

예시:

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*python*" } |
  Select-Object Id, ProcessName, WS, PM, StartTime
```

## 6. 시나리오 요약

| ID | 구분 | 시나리오 | 우선순위 |
|------|------|------|------|
| FIT-01 | 기능 | 유효한 설정으로 서비스 기동 | 상 |
| FIT-02 | 기능 | 파이프라인 목록 API 조회 | 상 |
| FIT-03 | 기능 | Full 전략 수동 실행 성공 | 상 |
| FIT-04 | 기능 | Incremental 전략 수동 실행 성공 | 상 |
| FIT-05 | 기능 | 스케줄러 자동 실행 | 상 |
| FIT-06 | 기능 | 백필 월 분할 실행 | 상 |
| FIT-07 | 기능 | 동일 execution_date 재실행 멱등성 | 상 |
| FIT-08 | 기능 | 재시도 가능한 Oracle 오류 후 복구 | 중 |
| FIT-09 | 기능 | 비재시도 오류 시 실패 및 step skip | 상 |
| FIT-10 | 기능 | 서비스 재시작 후 실행 이력 유지 | 상 |
| PIT-01 | 성능 | 월 100만 건 Full 이관 시간 | 상 |
| PIT-02 | 성능 | 메모리 500MB 제한 준수 | 상 |
| PIT-03 | 성능 | chunk_size 변경에 따른 처리 효율 비교 | 중 |
| PIT-04 | 성능 | 장시간 실행 중 중복 스케줄 차단 | 중 |
| NFT-01 | 비기능 | 환경변수 누락 시 명확 실패 | 상 |
| NFT-02 | 비기능 | Oracle Client/접속 오류 시 명확 실패 | 상 |
| NFT-03 | 비기능 | CORS 및 내부망 접근 제한 확인 | 중 |
| NFT-04 | 비기능 | 로그, DB, Parquet 증적 추적성 | 상 |
| NFT-05 | 비기능 | 서비스 재시작 후 misfire 처리 | 중 |
| NFT-06 | 비기능 | Full 전략 백업 파일 생성 및 운영 잔존물 점검 | 중 |
| OPT-01 | 선택 | 알림 채널 연동 확인 | 선택 |

## 7. 상세 시나리오

### FIT-01. 유효한 설정으로 서비스 기동

- 목적: 서비스, 스케줄러, API가 정상 기동되는지 확인한다.
- 사전조건:
  - `config/pipelines.yaml`이 존재한다.
  - 환경변수가 모두 설정되어 있다.
  - SQLite/로그/Parquet 경로에 쓰기 권한이 있다.
- 절차:
  1. `python -m airflow_lite service install`
  2. `python -m airflow_lite service start`
  3. `Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/pipelines"`
- 기대 결과:
  - 서비스가 시작된다.
  - API가 200을 반환한다.
  - 로그에 `스케줄러 시작됨`이 남는다.
- 합격 기준:
  - 서비스 시작 후 60초 이내 API 응답 가능
  - `pipeline_runs`, `step_runs` 손상 없음

### FIT-02. 파이프라인 목록 API 조회

- 목적: 설정 파일의 파이프라인 정의가 API에 반영되는지 확인한다.
- 사전조건: FIT-01 통과
- 절차:
  1. `GET /api/v1/pipelines` 호출
- 기대 결과:
  - 설정된 파이프라인 수와 동일한 항목 반환
  - 각 항목에 `name`, `table`, `strategy`, `schedule` 포함
- 합격 기준:
  - 누락/중복 없이 반환
  - YAML과 API 응답이 일치

### FIT-03. Full 전략 수동 실행 성공

- 목적: Full 전략 파이프라인이 수동 트리거로 한 달 데이터를 이관하는지 확인한다.
- 사전조건:
  - `PRODUCTION_LOG_IT`에 검수 월 데이터 존재
  - 대상 월 Parquet가 없거나 사전 삭제됨
- 절차:
  1. `POST /api/v1/pipelines/production_log_full/trigger`
  2. `execution_date`를 검수 대상 월 1일로 지정
  3. 응답의 `run_id` 확인
  4. SQLite에서 해당 run의 step 조회
  5. Parquet 파일 존재 여부 확인
- 기대 결과:
  - `pipeline_runs.status = success`
  - `step_runs`에 `extract_transform_load`, `verify`가 순서대로 생성
  - 두 step 모두 `success`
  - Parquet 파일이 월 경로에 생성
- 합격 기준:
  - API 200
  - Oracle 원본 월 건수 = Parquet 행 수
  - `records_processed > 0`

### FIT-04. Incremental 전략 수동 실행 성공

- 목적: Incremental 전략이 지정 날짜 변경분을 append하는지 확인한다.
- 사전조건:
  - `EQUIPMENT_STATUS_IT`에 `UPDATED_AT` 기준 데이터 존재
  - 같은 월에 기존 Parquet 파일이 존재한다.
- 절차:
  1. `POST /api/v1/pipelines/equipment_status_inc/trigger`
  2. `execution_date`를 변경 데이터가 있는 날짜로 지정
  3. 실행 전/후 Parquet 행 수 비교
- 기대 결과:
  - 실행 후 Parquet 행 수가 증가하거나 동일하다.
  - `verify` step 성공
- 합격 기준:
  - 증가한 행 수가 기대 범위와 일치
  - 기존 월 Parquet가 손상되지 않음

### FIT-05. 스케줄러 자동 실행

- 목적: Cron 스케줄에 따라 자동 실행되는지 확인한다.
- 사전조건:
  - 검수 파이프라인의 `schedule`을 `*/10 * * * *` 같은 짧은 주기로 설정
  - 서비스가 실행 중
- 절차:
  1. 다음 스케줄 시점까지 대기
  2. `pipeline_runs` 최신 레코드 확인
  3. 로그에서 자동 실행 기록 확인
- 기대 결과:
  - `trigger_type = scheduled`
  - 예약 시각 이후 자동 실행 레코드가 생성
- 합격 기준:
  - 수동 개입 없이 1회 이상 자동 실행 성공

### FIT-06. 백필 월 분할 실행

- 목적: 백필 요청이 월 단위로 분할되어 여러 실행으로 저장되는지 확인한다.
- 사전조건: 3개월 이상 데이터 준비
- 절차:
  1. `POST /api/v1/pipelines/production_log_full/backfill`
  2. `start_date = 2026-01-01`, `end_date = 2026-03-31`로 호출
  3. 응답 배열 길이와 execution_date 확인
- 기대 결과:
  - 2026-01-01, 2026-02-01, 2026-03-01 3건 생성
  - 모든 run의 `trigger_type = backfill`
- 합격 기준:
  - 월 수와 동일한 run 개수 생성
  - 각 월 Parquet가 생성 또는 갱신

### FIT-07. 동일 execution_date 재실행 멱등성

- 목적: 동일 파이프라인과 동일 `execution_date`를 재실행했을 때 중복 적재를 막는지 확인한다.
- 사전조건: FIT-03 성공 이력 존재
- 절차:
  1. 동일 파이프라인에 동일 `execution_date`로 다시 trigger
  2. 이전 run ID와 반환 run ID 비교
  3. Parquet 행 수 비교
- 기대 결과:
  - 기존 성공 run이 재사용되거나 결과가 동일
  - Parquet 데이터가 추가 중복되지 않음
- 합격 기준:
  - 중복 row 증가 없음
  - 추가 실패 레코드 생성 없음

### FIT-08. 재시도 가능한 Oracle 오류 후 복구

- 목적: 일시적 Oracle 접속 장애가 재시도 후 복구되는지 확인한다.
- 사전조건:
  - 재시도 가능한 장애를 유발할 수 있는 검수 환경
  - 로그 접근 가능
- 절차:
  1. 실행 직전 Oracle listener 또는 네트워크를 짧게 차단
  2. 파이프라인 trigger 실행
  3. 재시도 이후 연결 복구
  4. `step_runs.retry_count`와 최종 상태 확인
- 기대 결과:
  - 중간에 warning 로그 발생
  - `retry_count >= 1`
  - 최종 status는 `success`
- 합격 기준:
  - 재시도 소진 전에 정상 복구
  - 서비스 프로세스가 비정상 종료하지 않음

### FIT-09. 비재시도 오류 시 실패 및 후속 step skip

- 목적: 데이터 오류나 비재시도 Oracle 오류가 즉시 실패 처리되는지 확인한다.
- 사전조건:
  - 잘못된 SQL 조건 또는 비재시도 오류를 일으키는 검수 데이터 준비
- 절차:
  1. 오류를 유도할 설정 또는 데이터로 실행
  2. `pipeline_runs`, `step_runs`, 로그 확인
- 기대 결과:
  - 첫 step이 `failed`
  - 후속 `verify` step은 `skipped`
  - `error_message`가 저장됨
- 합격 기준:
  - `retry_count`가 과도하게 증가하지 않음
  - 실패 원인을 로그와 DB에서 추적 가능

### FIT-10. 서비스 재시작 후 실행 이력 유지

- 목적: 서비스 재시작 후 SQLite 실행 이력과 API 조회가 유지되는지 확인한다.
- 사전조건: 최소 1건 이상의 성공 run 존재
- 절차:
  1. `python -m airflow_lite service stop`
  2. `python -m airflow_lite service start`
  3. `GET /api/v1/pipelines/{name}/runs`
  4. `GET /api/v1/pipelines/{name}/runs/{run_id}`
- 기대 결과:
  - 과거 run 이력이 그대로 조회된다.
  - 최신 run 상세의 step 목록도 동일하다.
- 합격 기준:
  - 서비스 재시작 후 이력 손실 없음
  - SQLite 파일 손상 없음

### PIT-01. 월 100만 건 Full 이관 시간

- 목적: 요구사항의 처리시간 기준을 충족하는지 확인한다.
- 사전조건:
  - 월 100만 건 데이터 준비
  - 다른 대형 배치 작업 중지
- 절차:
  1. Full 전략 파이프라인 수동 실행
  2. 시작/종료 시각 기록
  3. Oracle 건수와 Parquet 행 수 비교
- 기대 결과:
  - 100만 건 월 데이터가 단일 run으로 이관 완료
- 합격 기준:
  - 총 소요시간 30분 이내
  - 결과 파일 손상 없음

### PIT-02. 메모리 500MB 제한 준수

- 목적: 대용량 이관 시 프로세스 메모리 사용이 제한 내인지 확인한다.
- 사전조건: PIT-01과 동일
- 절차:
  1. 대용량 run 중 1분 간격으로 Working Set 또는 Private Memory 기록
  2. 피크 메모리값 산출
- 기대 결과:
  - 청크 처리 중 메모리 급증 없이 안정적 유지
- 합격 기준:
  - 피크 메모리 500MB 이하

### PIT-03. chunk_size 변경에 따른 처리 효율 비교

- 목적: 배포 환경에 맞는 현실적 chunk_size를 찾는다.
- 사전조건: 동일 데이터셋, 동일 서버 조건
- 절차:
  1. `chunk_size`를 5000, 10000, 20000으로 바꿔 3회 실행
  2. 각 실행의 시간, 피크 메모리, 실패 여부 기록
- 기대 결과:
  - 너무 작은 청크는 느리고, 너무 큰 청크는 메모리를 증가시킨다.
- 합격 기준:
  - 성능/메모리 균형이 가장 좋은 값을 운영 기본값으로 선정 가능

### PIT-04. 장시간 실행 중 중복 스케줄 차단

- 목적: 한 번 실행이 길어져도 같은 파이프라인이 중복 실행되지 않는지 확인한다.
- 사전조건:
  - 실행 시간이 스케줄 간격보다 긴 데이터셋 준비
  - 스케줄 주기를 짧게 설정
- 절차:
  1. 장시간 Full run 시작
  2. 다음 스케줄 시점이 지나도록 대기
  3. `pipeline_runs` 생성 건수 확인
- 기대 결과:
  - 같은 파이프라인의 동시 실행이 발생하지 않음
- 합격 기준:
  - 중첩된 `running` run이 생기지 않음

### NFT-01. 환경변수 누락 시 명확 실패

- 목적: 필수 환경변수가 없을 때 조용히 잘못 실행되지 않는지 확인한다.
- 사전조건:
  - 서비스 중지
  - `ORACLE_PASSWORD` 등 필수 환경변수 하나 제거
- 절차:
  1. 서비스 시작 시도
  2. 콘솔/이벤트 로그/애플리케이션 로그 확인
- 기대 결과:
  - 서비스가 정상 기동하지 않음
  - 누락된 환경변수명이 오류 메시지에 표시됨
- 합격 기준:
  - 원인 식별 가능한 메시지 제공

### NFT-02. Oracle Client 또는 접속 오류 시 명확 실패

- 목적: Oracle thick mode 설정 문제나 접속 정보 오류를 빠르게 식별할 수 있는지 확인한다.
- 사전조건:
  - `oracle_home` 또는 접속 정보를 의도적으로 잘못 설정
- 절차:
  1. 서비스 시작 또는 trigger 실행
  2. 로그와 API/DB 상태 확인
- 기대 결과:
  - thick mode 초기화 실패 또는 DB 접속 실패가 로그에 기록됨
  - 데이터 손상 없이 실패 처리
- 합격 기준:
  - 장애 원인이 로그에서 구분 가능

### NFT-03. CORS 및 내부망 접근 제한 확인

- 목적: 허용된 origin만 CORS 헤더를 받는지 확인한다.
- 사전조건:
  - `api.allowed_origins` 설정 존재
- 절차:
  1. 허용 origin으로 preflight 요청
  2. 비허용 origin으로 preflight 요청
- 기대 결과:
  - 허용 origin에는 CORS 허용 헤더가 반환됨
  - 비허용 origin에는 동일 헤더가 반환되지 않음
- 합격 기준:
  - 브라우저 기반 내부 UI 연동 시 허용 origin만 사용 가능

### NFT-04. 로그, DB, Parquet 증적 추적성

- 목적: 한 번의 실행을 로그, DB, 파일 결과물로 모두 역추적할 수 있는지 확인한다.
- 사전조건: 성공 run 1건 존재
- 절차:
  1. API 응답에서 `run_id`, `execution_date` 확보
  2. SQLite에서 동일 run 조회
  3. 로그에서 같은 시간대 메시지 조회
  4. Parquet 파일 경로 확인
- 기대 결과:
  - 한 실행의 증적이 세 저장소에서 일관되게 확인됨
- 합격 기준:
  - 장애 분석에 필요한 최소 증적이 모두 확보됨

### NFT-05. 서비스 재시작 후 misfire 처리

- 목적: 서비스 다운타임이 짧을 때 놓친 스케줄이 재기동 후 처리되는지 확인한다.
- 사전조건:
  - 짧은 cron 주기 설정
  - 서비스가 실행 중
- 절차:
  1. 다음 스케줄 직전에 서비스 중지
  2. 1시간 이내에 서비스 재시작
  3. 자동 실행 여부 확인
- 기대 결과:
  - 재시작 후 놓친 실행이 1회 보정되거나 다음 실행으로 정상 복구
- 합격 기준:
  - 장시간 정지 후 재기동해도 스케줄러가 비정상 상태에 빠지지 않음

### NFT-06. Full 전략 백업 파일 생성 및 운영 잔존물 점검

- 목적: 기존 월 Parquet를 덮어쓸 때 최소한의 백업 안전장치가 동작하는지 확인한다.
- 사전조건:
  - 검수 월의 기존 Parquet 파일이 존재
- 절차:
  1. 같은 월에 대해 Full 전략 run 실행
  2. 실행 직후 `.bak` 파일 존재 여부 확인
  3. 새 Parquet와 `.bak` 파일을 모두 확인
- 기대 결과:
  - 기존 Parquet가 `.bak`로 이동된 뒤 새 Parquet가 생성됨
- 합격 기준:
  - 덮어쓰기 전에 백업 흔적이 남음
  - 검수 보고서에 `.bak` 정리/복원 자동화 미연결 상태를 별도 기록

### OPT-01. 알림 채널 연동 확인

- 목적: 배포 래퍼 또는 추가 통합 코드에서 알림을 실제 연결한 경우 이메일/웹훅이 발송되는지 확인한다.
- 사전조건:
  - AlertManager가 실제 런타임에 연결되어 있어야 함
- 절차:
  1. 실패 run 유도
  2. 이메일 또는 웹훅 수신 여부 확인
- 기대 결과:
  - 설정된 채널에 실패 알림 전달
- 합격 기준:
  - 이 시나리오는 현재 저장소 기본 구현만으로는 필수 합격 항목이 아님

## 8. 합격 판정 기준

### 필수 합격

아래 시나리오는 실제 배포 승인 기준으로 통과해야 한다.

- FIT-01 ~ FIT-07
- FIT-09
- FIT-10
- PIT-01
- PIT-02
- NFT-01
- NFT-02
- NFT-04

### 조건부 합격

환경 특성상 일부 시나리오는 조건부로 본다.

- FIT-08: 장애 유도 환경 필요
- PIT-03: 튜닝 목적
- PIT-04: 긴 실행시간을 재현할 데이터셋 필요
- NFT-03: 브라우저 기반 호출 환경 필요
- NFT-05: 시간 기반 재현 필요
- NFT-06: 현재 구현 편차를 고려한 운영 점검 항목
- OPT-01: 알림 연동 코드가 실제 배포본에 포함될 때만 적용

## 9. 검수 결과 기록 양식

각 시나리오마다 아래 항목을 남긴다.

- 시나리오 ID
- 실행 일시
- 검수자
- 대상 서버
- 사용한 파이프라인 이름
- execution_date 또는 기간
- 결과: Pass / Fail / Blocked
- 증적 위치
  - API 응답 캡처
  - 로그 파일 경로
  - SQLite 조회 결과
  - Parquet 파일 경로
- 비고

## 10. 검수 후 정리

검수 종료 후 아래 항목을 수행한다.

1. 테스트용 스케줄을 운영값으로 복원한다.
2. 검수용 Parquet, SQLite, 로그를 백업 또는 정리한다.
3. 서비스 중지가 필요하면 `service stop`, 제거가 필요하면 `service remove`를 수행한다.
4. `.bak` 파일이 남아 있으면 운영 정책에 따라 보관 또는 수동 정리한다.
5. 실패 시나리오의 재현 조건과 로그를 별도 장애 보고서로 분리한다.
