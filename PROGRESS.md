# PROGRESS.md

## 현재 상태 요약

- 저장소에는 `.codex` 관례에 맞춘 표준 `AGENTS.md` 운영 가이드가 정리되어 있다.
- 저장소에는 agent와 skill 기반 작업을 위한 로컬 `.codex` 레이아웃이 준비되어 있다.
- 저장소에는 `reference/codex/` 아래 재사용 가능한 Codex 레퍼런스가 있다.
- 저장소 루트에는 공유 실행 상태 문서가 존재한다.

## 최근 완료 작업

- `2026-04-06` Codex 저장소 운영 문서명을 `AGENT.md`에서 `AGENTS.md`로 변경하고, `.codex` 설정, skill, planning 문서, reference 문서의 모든 참조를 함께 갱신했다.
- `2026-04-06` 승격된 mart 데이터베이스를 기준으로 DuckDB 기반 analytics query service, FastAPI summary/chart/filter route, route 단위 테스트를 추가하여 `T-015`를 완료했다.
- `2026-04-06` staged DuckDB mart 실행, source table 재구축, mart validation, snapshot/current promotion, 서비스 성공 훅 실행 연결을 추가하여 `T-014`를 완료했다.
- `2026-04-02` 지원하지 않는 저장소 로컬 `.codex/commands/` 파일을 제거하고 `AGENTS.md`, planning 로그, `reference/codex/`의 명령 참조를 정리했다.
- `2026-04-02` backfill 요청의 기본 force 값을 안전한 기본값으로 되돌리고, incremental parquet 검증을 실제 partition row 증가 기준으로 강화했으며, SQLite 스키마 스크립트를 명시적 트랜잭션 안에서 statement 단위로 실행하도록 수정해 리뷰 이슈를 해소했다.
- `2026-03-31` 브랜치 `codex/default-draft-pr-workflow`에서 기본 draft PR 워크플로 업데이트용 draft PR `#1`을 열었다.
- `2026-03-31` 작업 완료 시 사용자나 환경이 막지 않는 한 GitHub publish 워크플로를 통해 draft PR 생성까지 기본 수행하도록 `AGENTS.md`를 갱신했다.
- `2026-03-31` 저장소 로컬 agent 역할과 명시적 skill 등록을 포함한 `.codex/config.toml`을 추가했다.
- `2026-03-31` bootstrap, progress discipline, indexing, task slicing, Oracle ETL, DuckDB mart design, query tuning, API contract design, export policy, Windows ops, failure bundling, reference reading용 기본 `.codex/skills/` 패키지를 추가했다.
- `2026-03-31` Markdown 레퍼런스 문서와 `index.json`을 포함한 `reference/codex/`를 추가했다.
- `2026-03-31` `reference-reader` 조회 스크립트와 테스트를 추가했다.
- `2026-03-31` 루트 `PLAN.md`, `PROGRESS.md`를 추가하고 저장소의 멀티 에이전트 워크플로에 맞게 정렬했다.
- `2026-03-31` build, refresh, snapshot, validation 인터페이스와 집중 테스트를 포함하는 `src/airflow_lite/mart/` 골격을 추가했다.
- `2026-03-31` Claude Code 전용 워크플로 파일은 건드리지 않고 루트 `AGENTS.md`를 추가하고 planning 문서를 현재 작업 상태에 맞게 정렬했다.
- `2026-03-31` mart refresh 설계 문서, 선택적 mart 설정, Windows 서비스 런타임의 success-hook mart refresh planner 연동을 추가하여 `T-011`을 완료했다.
- `2026-03-31` summary/chart/filter API 계약 문서와 후속 FastAPI 구현용 Pydantic 계약 모델을 추가하여 `T-012`를 완료했다.

## 진행 중

- 현재 진행 중으로 표시된 활성 작업은 없다.

## 다음 작업

- `M4`에는 아직 대시보드 및 시각화 계층 계획과 구현 작업이 남아 있다.

## 블로커 및 리스크

- 현재 analytics 계층은 mart 메타데이터 기반 summary와 chart만 제공한다. dataset별 KPI 로직, detail query, export 워크플로는 후속 작업이다.
- 현재 환경에서는 기본 temp 루트 아래 pytest temp-directory fixture가 막혀 있어 `tmp_path` 기반 검증을 그대로 쓰기 어렵다.

## 검증 메모

- `2026-04-06` `C:\Users\170731\.codex\memories` 아래에서 수행한 수동 inline Python 검증으로 staged mart refresh build가 source parquet 파일들을 DuckDB로 집계하고, 검증에 성공하며, `current/`와 `snapshots/`에 모두 승격되고, 재구축 중에도 다른 source table은 보존됨을 확인했다.
- `2026-04-06` `C:\Users\170731\.codex\memories` 아래에서 수행한 수동 inline Python 검증으로 `DuckDBAnalyticsQueryService`가 summary metric, month bucket chart 데이터, filter metadata를 승격된 mart 데이터베이스에서 정상 반환함을 확인했다.
- `2026-04-06` `fastapi.testclient.TestClient`를 이용한 수동 inline Python 검증으로 `/api/v1/analytics/summary`, `/api/v1/analytics/charts/{chart_id}/query`, `/api/v1/analytics/filters`가 샘플 DuckDB mart 기준으로 정상 응답함을 확인했다.
- `2026-04-06` `python -m compileall src/airflow_lite/mart src/airflow_lite/query src/airflow_lite/analytics src/airflow_lite/api tests/test_mart.py tests/test_query_service.py tests/test_api.py tests/test_service.py`가 성공했다.
- `2026-04-06` `pytest tests/test_mart.py tests/test_query_service.py tests/test_api.py tests/test_service.py -q --basetemp ... -p no:cacheprovider`는 실행 단계까지는 진행했지만, 이 sandbox에서는 선택한 base temp 디렉터리를 순회하는 cleanup 단계에서 `PermissionError`가 발생했다.
- `2026-04-06` 브랜치 `codex/mart-refresh-analytics`를 푸시했고, draft PR `#7`을 열었다: `https://github.com/jwleepro/airflow_lite/pull/7`
- `2026-04-04` `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`, `python -m pytest tests/test_issue_triage.py tests/test_label_sync.py -q --basetemp .tmp_pytest -p no:cacheprovider`가 `8 passed`로 성공했다.
- `2026-04-04` `python .github\scripts\sync_labels.py --repo jwleepro/airflow_lite --labels-path .github\labels.json --dry-run`이 `create=[]`, `update=[]`, `unchanged_count=31`을 보고했다.
- `2026-04-04` `python .github\scripts\sync_labels.py --repo jwleepro/airflow_lite --labels-path .github\labels.json`이 no-op으로 완료되었고 `create=[]`, `update=[]`, `unchanged_count=31` 상태였다.
- `2026-04-04` `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`, `python -B -m pytest tests/test_issue_triage.py -q -p no:cacheprovider`가 `5 passed`로 성공했다. 이때 issue form과 triage script에 명시적 `needs-human` 신호 처리를 추가했다.
- `2026-04-03` 정리 이후 `python .codex\skills\reference-reader\scripts\read_reference.py --list`가 성공했고 `document count: 4`를 보고했다.
- `2026-04-03` 수동 검증으로 `reference/codex/index.json`에 남아 있는 모든 경로가 실제 `reference/codex/` 아래 존재함을 확인했다.
- `2026-04-02` `pytest tests/test_api.py tests/test_backfill.py tests/test_extract.py tests/test_service.py tests/test_settings.py tests/test_storage.py tests/test_mart.py tests/test_reference_reader.py -q -p no:cacheprovider`는 수집과 실행 단계까지는 갔지만, 이 환경에서는 `tmp_path` 설정을 위해 필요한 `C:\Users\170731\AppData\Local\Temp\pytest-of-170731` 접근이 막혀 실패했다.
- `2026-04-02` SQLite 트랜잭션 근거 주석과 `trigger_type` 전달 회귀 테스트를 추가한 뒤 `python -m compileall src/airflow_lite/storage/database.py tests/test_engine.py`가 성공했다.
- `2026-04-02` workspace-local temp 디렉터리에서 수행한 inline Python 검증으로 `PipelineRunner.run(trigger_type="backfill")`가 `trigger_type`을 stage 실행과 `on_run_success` callback에 모두 전달하며, `_execute_script_atomically()`가 뒤늦게 실패한 statement가 있어도 앞선 statement를 롤백함을 확인했다.
- `2026-04-02` `pytest tests/test_engine.py tests/test_storage.py tests/test_service.py tests/test_settings.py tests/test_extract.py tests/test_backfill.py -q -p no:cacheprovider`는 명시적 `--basetemp`를 주어도 Windows 권한 문제로 pytest temp-directory setup/cleanup이 실패해 완료되지 못했다.
- `2026-04-02` 수동 검증으로 `.codex/commands/`가 더 이상 존재하지 않고 `reference/codex/command-format.md`가 파일 시스템과 `reference/codex/index.json` 양쪽에서 제거되었음을 확인했다.
- `2026-04-02` 수동 검증으로 `AGENTS.md`, `PLAN.md`, `PROGRESS.md`, `reference/codex/*.md`가 더 이상 저장소 로컬 slash command 사용을 지시하지 않음을 확인했다.
- `2026-04-02` inline Python 검증으로 `BackfillRequest.force` 기본값이 `False`이고, `BackfillManager.run_backfill()`이 기본적으로 `force_rerun=False`를 전달하며, `IncrementalMigrationStrategy.verify()`가 기대 증가분과 맞지 않는 partition row count를 거부함을 확인했다.
- `2026-04-02` inline Python 검증으로 `_execute_script_atomically()`가 예상된 `OperationalError` 뒤에 부분 적용된 SQL 시퀀스를 롤백하고, `Database.initialize()`가 여전히 새 executor로 `pipeline_runs`, `step_runs`를 생성함을 확인했다.
- `2026-04-02` `python -m compileall src/airflow_lite/api/schemas.py src/airflow_lite/engine/backfill.py src/airflow_lite/engine/strategy.py tests/test_api.py tests/test_backfill.py tests/test_extract.py tests/test_storage.py`가 성공했다.
- `2026-04-02` `pytest tests/test_api.py tests/test_backfill.py tests/test_extract.py tests/test_storage.py -q -p no:cacheprovider`는 기본 temp 루트와 저장소 로컬 `--basetemp` 모두에서 pytest temp-directory setup/cleanup 권한 문제로 완료되지 못했다.
- `2026-03-31` 브랜치 `codex/default-draft-pr-workflow`를 푸시하고 draft PR `#1`을 생성했다: `https://github.com/jwleepro/airflow_lite/pull/1`
- `2026-03-31` 기본 draft PR 생성 워크플로를 문서화하기 전에 `AGENTS.md`, `PLAN.md`, `PROGRESS.md`를 다시 읽었다.
- `2026-03-31` `python .codex\skills\reference-reader\scripts\read_reference.py --list`가 성공했다.
- `2026-03-31` `pytest tests\test_reference_reader.py -q`가 `2 passed`로 성공했다.
- `2026-03-31` `pytest tests\test_mart.py -q`가 `5 passed`로 성공했다.
- `2026-03-31` 문서 정렬 업데이트 뒤 `AGENTS.md`, `PLAN.md`, `PROGRESS.md`를 다시 읽었다.
- `2026-03-31` `pytest tests\test_mart.py -q -p no:cacheprovider`가 `7 passed`로 성공했다.
- `2026-03-31` `pytest tests\test_settings.py -q -k mart_config -p no:cacheprovider`가 `1 passed`로 성공했다.
- `2026-03-31` `pytest tests\test_api.py -q -k "summary_contract or chart_contract" -p no:cacheprovider`가 `2 passed`로 성공했다.
- `2026-03-31` inline Python 검증으로 `AirflowLiteService._create_runner_factory()`가 `mart.enabled=true`일 때 mart refresh planner hook을 호출함을 확인했다.
- `2026-03-31` `python -m compileall src/airflow_lite`가 성공했다.

## 인수인계

- 저장소는 승격된 DuckDB mart와 analytics endpoint 위에서 `M4` 대시보드 계획을 시작할 준비가 되어 있다.
- 다음 추천 담당자: Codex 내장 `planner-agent` 또는 프론트엔드 구현 성격의 agent
- 추천 수정 범위:
  - `src/airflow_lite/api/`
  - `src/airflow_lite/query/`
  - `src/airflow_lite/analytics/`
  - 대시보드/UI 파일이 도입되면 그 경로들
