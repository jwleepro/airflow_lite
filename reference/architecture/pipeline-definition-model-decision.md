# Pipeline Definition Model Decision

업데이트: `2026-04-21`

## 문서 목적

이 문서는 `airflow_lite`의 파이프라인 정의 모델을 어떻게 가져갈지에 대해 이번 대화에서 확인한 사실, 정정된 판단, 현재 코드 분석, 그리고 최종 결정을 상세히 기록한다.

이 문서는 축약본이 아니다. 다른 agent가 이 문서만 읽고도 아래 항목을 이해할 수 있게 작성한다.

- Apache Airflow가 워크플로와 데이터 처리를 어떤 방식으로 다루는지
- 현재 `airflow_lite`가 파이프라인을 어떤 저장소와 경로로 관리하는지
- 기존 오해나 부정확했던 표현이 무엇이었는지
- 왜 Admin UI 기반 등록보다 Python DAG 파일 정의가 더 적합하다고 판단했는지
- 이후 구현에서 무엇을 바꿔야 하는지

## 배경 문제

초기 문제의식은 다음과 같았다.

- 대상 Oracle 인스턴스에서 가져와야 할 테이블이 소수라면 파이프라인을 하나씩 등록해도 된다.
- 그러나 대상 테이블이 200개 이상이라면 수동 등록은 운영 비용이 크다.
- 실운영에서는 다음과 같은 요구가 자연스럽다.
  - 인스턴스의 모든 테이블 가져오기
  - 특정 단어를 포함하는 테이블만 가져오기
  - 특정 접두어로 시작하는 테이블만 가져오기
  - 특정 접미어로 끝나는 테이블만 가져오기

이 요구를 처리하려면 두 가지 질문이 필요했다.

1. 현재 `airflow_lite`에 그런 기능이 이미 있는가
2. Apache Airflow는 보통 이 문제를 어떤 식으로 푸는가

이 두 질문의 답을 바탕으로 `airflow_lite`가 어떤 모델로 가야 하는지 결정했다.

## 현재 airflow_lite 코드 기준 사실

### 1. 현재 모델은 파이프라인 1개 = source table 1개

현재 설정 모델에서 파이프라인은 단일 `table` 필드를 가진다.

- `src/airflow_lite/config/settings.py`
- `PipelineConfig.name`
- `PipelineConfig.table`

현재 저장 스키마도 `pipeline_configs.source_table` 한 컬럼만 가진다.

- `src/airflow_lite/storage/schema.sql`

즉 현재 데이터 모델은 규칙 기반 집합 선택이 아니라, 명시적 단건 등록 모델이다.

### 2. 현재 파이프라인 등록은 하드코딩 정적이 아니라 SQLite 기반 동적 CRUD다

처음에는 `airflow_lite`를 "정적 목록을 읽는 구조"로 단순화해 표현했지만, 이 표현은 정확하지 않다.

정확한 상태는 다음과 같다.

- 파이프라인은 SQLite의 `pipeline_configs` 테이블에 저장될 수 있다.
- Admin API에서 pipeline CRUD를 제공한다.
- Web Admin UI에서도 pipeline CRUD를 제공한다.
- YAML은 legacy/폴백 성격이며, SQLite가 비어 있을 때만 보조 입력원으로 쓰인다.
- 서버 시작 시 YAML 관리 데이터는 SQLite로 1회 import/migration 될 수 있다.

관련 코드 경로:

- `src/airflow_lite/api/routes/admin.py`
- `src/airflow_lite/api/routes/web_admin.py`
- `src/airflow_lite/api/presenters/admin_forms.py`
- `src/airflow_lite/storage/pipeline_repository.py`
- `src/airflow_lite/storage/admin_repository.py`
- `src/airflow_lite/storage/yaml_admin_migration.py`
- `src/airflow_lite/config/loader.py`

따라서 현재 `airflow_lite`를 "정적 하드코딩 제품"이라고 부르는 것은 틀리다.

### 3. 다만 실행 관점에서는 live-dynamic이 아니라 runtime snapshot에 가깝다

위의 정정과 별개로, 런타임 동작에는 중요한 제약이 있다.

- 서버가 시작되면 `Settings.load()`로 파이프라인 목록을 읽는다.
- 그 시점의 `settings.pipelines`로 `runner_map`과 `backfill_map`이 만들어진다.
- FastAPI app은 이 `settings`와 `runner_map`을 `app.state`에 보관한다.
- 파이프라인 목록 API와 수동 실행 API도 이 스냅샷을 참조한다.

관련 코드 경로:

- `src/airflow_lite/bootstrap.py`
- `src/airflow_lite/api/app.py`
- `src/airflow_lite/api/routes/pipelines.py`

즉 현재 모델은 다음 두 문장을 동시에 만족한다.

- 저장/관리 측면에서는 SQLite 기반 동적 등록이 가능하다.
- 실행 측면에서는 프로세스 시작 시점에 읽힌 파이프라인 스냅샷에 의존한다.

이 점은 이후 DAG 파일 모델 설계에서 reload 정책을 따로 정의해야 한다는 뜻이다.

### 4. 현재 코드에는 테이블 자동 발견 기능이 없다

로컬 코드 조사 기준으로 다음은 현재 존재하지 않는다.

- Oracle `USER_TABLES`, `ALL_TABLES`, `DBA_TABLES`를 조회해 테이블 목록을 자동 발견하는 로직
- 이름 패턴 기반 일괄 등록 규칙
- `all_tables`, `contains`, `prefix`, `suffix` 같은 pipeline discovery rule 모델
- 실행 직전에 Oracle 메타데이터를 조회해 synthetic pipeline을 확장하는 로직

즉 현재 `airflow_lite`는 많은 테이블을 효율적으로 다루기 위한 discovery-driven 모델이 아니다.

## Apache Airflow 조사 결과

### 1. Airflow는 데이터 수집 제품이 아니라 워크플로 오케스트레이터다

이번 대화에서 가장 중요한 정리는 이것이다.

- Airflow의 본질은 "데이터를 가져오는 전용 제품"이 아니다.
- Airflow의 본질은 "작업 순서와 실행 방식을 코드로 정의하는 오케스트레이터"다.
- 데이터 수집, 가공, 적재, 검증은 DAG 파일과 task 코드가 정한다.

즉 Airflow를 본떠야 한다는 말은 "UI 등록 방식"을 본뜨는 것이 아니라, "코드로 워크플로를 정의하고 필요하면 동적으로 확장하는 방식"을 본뜨는 것이다.

### 2. Airflow의 DAG 정의는 Python 코드 기반이다

공식 문서 기준으로 Airflow는 DAG를 Python 파일로 정의한다.

핵심 의미:

- source of truth는 UI가 아니라 `DAGS_FOLDER`의 코드 파일이다.
- UI는 관찰과 운영에 가깝고, DAG 자체를 창작하는 주요 정의 수단이 아니다.
- 이 점이 현재 `airflow_lite`의 Admin UI/SQLite 등록 모델과 가장 큰 철학적 차이다.

### 3. Dynamic DAG Generation은 parse-time 코드 생성이다

이번 대화에서 정정된 핵심 항목 중 하나다.

부정확했던 설명:

- `Dynamic DAG Generation`을 메타데이터 테이블이나 `SerializedDagModel`, `dag_run`, `dag_dependencies` 같은 내부 메타데이터 중심으로 설명하는 것은 맞지 않다.

정확한 설명:

- 문서가 설명하는 것은 DAG 파일이 파싱될 때 Python 코드로 DAG 구조를 생성하는 패턴이다.
- 대표적으로 설정값, 상수, 외부 선언을 읽어 여러 DAG나 task를 코드에서 만들어 낸다.
- 이 패턴은 보통 "구조는 parse-time에 확정"되는 성격에 가깝다.

### 4. Dynamic Task Mapping은 runtime 확장이다

Airflow의 또 다른 표준 패턴은 Dynamic Task Mapping이다.

핵심 의미:

- upstream task가 리스트나 iterable 성격의 값을 만든다.
- downstream task는 그 결과 길이만큼 runtime에 확장된다.
- 실행 시점에 실제 task fan-out이 정해진다.

이 패턴은 예를 들어 아래와 같은 문제에 적합하다.

- 특정 날짜에 실제로 처리할 파티션 목록이 달라질 수 있다.
- 메타데이터 조회 결과로 대상 테이블 목록이 달라질 수 있다.
- 외부 시스템 상태에 따라 실제 처리 대상을 결정해야 한다.

### 5. Oracle 테이블 자동 discover는 Airflow 내장 기능이 아니다

이 점도 명확하게 정리됐다.

- Airflow 자체가 Oracle 인스턴스를 자동 스캔해 파이프라인을 등록해 주는 범용 내장 기능을 제공하는 것은 아니다.
- 대신 Airflow 사용자는 코드로 discovery를 구현한다.

예시 패턴:

1. upstream task에서 Oracle 메타데이터를 조회한다.
2. 결과로 테이블 목록을 반환한다.
3. downstream task를 `expand()` 같은 메커니즘으로 펼친다.

즉 Airflow의 강점은 auto-discovery 자체의 내장보다, "그 discovery 과정을 코드로 쉽게 모델링할 수 있는 구조"에 있다.

## 대화 중 정정된 판단

이번 논의에서 명확히 바로잡힌 내용은 아래와 같다.

### 정정 1. airflow_lite는 단순 정적 제품이 아니다

잘못된 표현:

- `airflow_lite는 등록된 파이프라인 목록을 정적으로 읽는 구조`

정정:

- `airflow_lite`는 SQLite를 주요 저장소로 쓰고 Admin API/UI로 CRUD가 가능한 동적 관리 모델이다.
- 다만 runtime에서 로딩된 스냅샷을 사용하므로 live-reload 중심 제품은 아니다.

### 정정 2. Dynamic DAG Generation의 성격

잘못된 표현:

- 내부 메타데이터 모델이나 `dag_run` 계층 중심 설명

정정:

- parse-time Python 코드 생성 패턴으로 이해해야 한다.

### 정정 3. Airflow를 따라한다는 말의 의미

잘못된 이해 가능성:

- Airflow에도 관리자 화면에서 파이프라인을 대량 등록하는 내장 관리 기능이 있을 것이다

정정:

- Airflow를 따른다는 것은 "코드를 source of truth로 삼는 모델"을 따른다는 뜻에 가깝다.

## 최종 해석

이번 논의를 거친 뒤 다음 문장이 가장 정확한 요약으로 채택된다.

- Apache Airflow는 DAG 파일의 Python 코드로 워크플로를 정의하는 오케스트레이터다.
- 대상 데이터 선정은 하드코딩일 수도 있고 메타데이터 조회 기반 동적 생성일 수도 있다.
- 따라서 "Airflow가 동적으로 데이터를 가져온다"는 문장은 완전히 틀리지는 않지만, 더 정확히는 "필요하면 코드로 동적으로 가져오게 만들 수 있다"가 맞다.

이 해석을 `airflow_lite`에 적용하면 다음 결론이 나온다.

- `airflow_lite`도 장기적으로는 파이프라인 정의 source of truth를 UI/SQLite가 아니라 코드로 두는 편이 확장성 측면에서 더 낫다.
- 특히 테이블 수가 많고 규칙 기반 discovery가 필요한 경우, 선언형 또는 코드 기반의 DAG 정의 모델이 운영상 유리하다.

## 최종 결정

이번 대화의 최종 결정은 다음과 같다.

### 결정 1. Admin UI 기반 파이프라인 등록 모델은 장기 source of truth에서 제외한다

현재 `airflow_lite`는 Admin UI와 Admin API를 통해 pipeline CRUD를 제공한다.

그러나 다음 이유로 이 모델을 중심 정의 방식으로 유지하지 않기로 했다.

- 테이블 수가 적을 때만 관리가 쉽다.
- 수백 개 테이블 규모에서 수작업 등록은 비효율적이다.
- 패턴 기반 discovery 요구와 맞지 않는다.
- 정의의 재현성, 코드 리뷰, 버전 관리, 변경 추적 측면에서 불리하다.
- Airflow식 확장 모델과 맞지 않는다.

### 결정 2. 파이프라인 정의의 source of truth는 Python DAG 파일로 전환한다

목표 모델:

- 파이프라인은 코드 파일로 정의한다.
- 코드 파일은 버전 관리 대상이다.
- 운영 UI는 관찰/실행/상태 확인 위주로 남기고, 파이프라인 정의 자체는 코드에 둔다.

이 결정은 Airflow의 핵심 철학과 가장 잘 맞는다.

### 결정 3. 이후 확장 기능도 코드 중심으로 설계한다

향후 아래 기능이 필요하면 UI 등록 기능을 늘리는 방향보다 DAG 코드와 로더 설계로 푸는 것을 기본 원칙으로 삼는다.

- 전체 테이블 수집
- prefix/contains/suffix 기반 대상 선택
- schema 별 대상 선택
- 특정 테이블 제외 규칙
- 일정 시점의 메타데이터 스냅샷에 따라 대상 확장

## 이 결정이 의미하는 실제 변화

### 1. 운영 UI의 역할이 달라진다

현재의 Admin UI는 파이프라인을 생성/수정/삭제하는 인터페이스를 포함한다.

전환 이후에는 다음 중 하나로 바뀌어야 한다.

- pipeline CRUD 제거
- pipeline read-only 목록/상세 화면으로 축소
- 정의 파일 경로와 로딩 결과를 보여주는 운영 화면으로 재구성

### 2. SQLite `pipeline_configs` 테이블의 역할이 사라지거나 축소된다

가능한 방향:

- 완전 제거
- legacy migration용 임시 지원
- 운영 캐시/인덱스 용도만 유지

하지만 최소한 "source of truth"로는 더 이상 두지 않는다.

### 3. Settings 로더와 bootstrap 경로가 바뀌어야 한다

현재는 대략 아래 흐름이다.

1. YAML/SQLite에서 pipeline 목록 로드
2. `settings.pipelines` 구성
3. `runner_map` 구성
4. API와 scheduler가 이 스냅샷 사용

전환 이후에는 대략 아래 흐름이 필요하다.

1. 지정된 DAG Python 파일 경로 검색
2. DAG 정의 모듈 import 또는 안전한 로더로 평가
3. 코드에서 정의된 pipeline spec 수집
4. 그 결과를 `settings.pipelines` 또는 동등한 runtime model로 변환
5. `runner_map` 구성

즉 기존 로딩 source만 바꾸는 것이 아니라, 정의 모델 전체가 바뀐다.

### 4. reload 정책을 명시해야 한다

현재도 runtime snapshot 문제가 있었기 때문에, DAG 파일 모델에서는 다음을 반드시 설계해야 한다.

- 프로세스 시작 시 1회 로드만 할 것인지
- 파일 변경 감지 후 재로드할 것인지
- Windows Service 재시작이 유일한 반영 수단인지
- scheduler와 API가 동일한 DAG registry를 공유하는지

이 부분은 구현 전 반드시 정해야 한다.

## 구현 결과 (2026-04-21)

아래 항목은 위 결정 사항을 실제 코드에 반영한 결과다. 이 섹션이 현재 기준 최신 상태이며, 위의 분석/결정 섹션은 배경 문맥으로 유지한다.

### 1) DAG 파일 정의 API와 로더 도입

- `src/airflow_lite/dag_api.py` 신규 추가
  - `Pipeline` dataclass 추가
  - `id`, `table`, `source_where_template`, `source_bind_params`, `strategy`, `schedule`, `chunk_size`, `columns`, `incremental_key`를 코드에서 선언 가능
  - `to_pipeline_config()`로 기존 runtime이 쓰는 `PipelineConfig`로 변환

- `src/airflow_lite/config/dag_loader.py` 신규 추가
  - `resolve_dags_dir(config_path)`:
    - 기본 규칙: config 옆 `dags/` 사용
    - config 디렉토리명이 `config`면 프로젝트 루트 `dags/` 사용
    - `AIRFLOW_LITE_DAGS_DIR` 환경변수로 오버라이드 가능
  - `load_dag_pipelines(dags_dir)`:
    - `dags/*.py` 로드
    - `_` 접두 private 파일은 스킵 (`_migrated.py`만 예외 허용)
    - `pipelines` 목록에서 `Pipeline` 또는 `PipelineConfig` 수집
    - import 실패 파일은 로그만 남기고 계속 진행
  - ~~`migrate_sqlite_pipelines_to_dag_file_if_needed(sqlite_path, dags_dir)`~~ — **PR #50에서 제거** (일회성 마이그레이션 완료)
    - legacy `pipeline_configs`가 있고 사용자 DAG가 없는 경우 `dags/_migrated.py` 자동 생성
    - 기존 row를 `Pipeline(...)` 코드로 변환해 이관
    - 경고 로그로 마이그레이션 완료 메시지 출력

### 2) Settings 로더 입력원 전환

- `src/airflow_lite/config/loader.py`
  - 파이프라인 로딩 순서 변경:
    1. DAG 파일 로딩
    2. (DAG 없을 때) YAML `pipelines` 폴백
  - legacy SQLite 파이프라인은 직접 source로 읽지 않고 `dags/_migrated.py`로 1회 이관

- `src/airflow_lite/config/settings.py`
  - `_load_pipelines_from_sqlite()` 제거
  - pipeline 정의는 더 이상 Settings 계층에서 SQLite source를 직접 읽지 않음

### 3) Admin REST/Web pipeline CRUD 제거

- REST 제거:
  - `src/airflow_lite/api/routes/admin.py`에서 `/api/v1/admin/pipelines` GET/POST/PUT/DELETE 제거

- Web Admin 제거:
  - `src/airflow_lite/api/routes/web_admin.py`에서 pipeline 생성/수정/삭제 POST 핸들러 제거
  - `src/airflow_lite/api/templates/admin.html`에서 pipeline CRUD 패널/스크립트 제거
  - `src/airflow_lite/api/presenters/admin_forms.py`의 pipeline form 파싱/CRUD 호출 제거
  - `src/airflow_lite/api/presenters/admin_page.py`, `src/airflow_lite/api/webui_admin.py`에서 pipeline view data 제거
  - `src/airflow_lite/api/viewmodels/admin.py`, `src/airflow_lite/api/viewmodels/__init__.py`에서 `PipelineVM` 제거

### 4) Storage pipeline 경로 제거

- 삭제:
  - `src/airflow_lite/storage/pipeline_repository.py`
  - `src/airflow_lite/storage/models.py`의 `PipelineModel`

- 수정:
  - `src/airflow_lite/storage/admin_repository.py` pipeline 위임/CRUD 메서드 제거
  - `src/airflow_lite/storage/yaml_admin_migration.py` pipeline 마이그레이션 분기 제거
  - `src/airflow_lite/storage/schema.sql`에서 `pipeline_configs` 테이블 DDL 제거
  - `src/airflow_lite/storage/database.py`에서 pipeline_configs 대상 마이그레이션 로직 제거

### 5) i18n/샘플 정리

- `src/airflow_lite/i18n/translations_en.py`
- `src/airflow_lite/i18n/translations_ko.py`
  - pipeline admin UI 관련 번역 키 제거
  - admin subtitle 문구를 pipeline 정의 편집 제외 방향으로 정리

- `dags/default.py` 신규 추가
  - DAG 파일 기반 파이프라인 정의 예시 제공

### 6) 테스트 갱신 및 검증

- 신규 테스트:
  - `tests/test_dag_loader.py`
    - public DAG 로딩
    - private 파일 스킵
    - import 에러 내성
    - SQLite -> `_migrated.py` 자동 생성
    - `resolve_dags_dir()` 분기

- 기존 테스트 정리:
  - `tests/test_api.py` pipeline admin CRUD 테스트 제거/정리
  - `tests/test_admin_repository.py` pipeline CRUD 테스트 제거
  - `tests/test_storage.py` legacy pipeline_configs 마이그레이션 테스트 제거
  - `tests/test_settings.py` DAG 우선 로딩 검증 추가

- 검증 결과:
  - `pytest tests/ -q` 실행
  - 결과: `402 passed, 46 skipped`

## 구현 후 운영 의미

- 파이프라인 정의 source of truth는 Admin UI/SQLite가 아니라 `dags/*.py`가 된다.
- 관리 UI는 connection/variable/pool 중심으로 축소되고, pipeline 정의 편집 기능은 사라진다.
- legacy 환경은 시작 시 `pipeline_configs` 내용을 `_migrated.py`로 옮겨 코드 정의로 전환할 수 있다.
- runtime snapshot 성격은 유지된다. 즉 DAG 파일 변경 반영은 현재 기본적으로 프로세스 재시작 시점 기준이다.

## 후속 agent 참고 포인트

- 다음 확장은 `dags/*.py` 코드 작성 또는 DAG 로더 확장으로 처리한다.
- discovery 규칙(`all_tables`, `prefix`, `contains`, `suffix`)이 필요하면 Admin CRUD를 복원하지 말고 DAG 코드/보조 유틸로 구현한다.
- 운영 문서나 runbook은 "pipeline 등록" 절차 대신 "DAG 파일 배포/검증" 절차로 갱신해야 한다.
