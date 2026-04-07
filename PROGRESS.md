# PROGRESS.md

## 현재 상태 요약

- 저장소에는 `.codex` 관례에 맞춘 표준 `AGENTS.md` 운영 가이드가 정리되어 있다.
- 저장소에는 agent와 skill 기반 작업을 위한 로컬 `.codex` 레이아웃이 준비되어 있다.
- 저장소에는 `reference/codex/` 아래 재사용 가능한 Codex 레퍼런스가 있다.
- 저장소 루트에는 공유 실행 상태 문서가 존재한다.
- `M4`는 더 이상 대기 상태가 아니며, 대시보드 정의 API(`T-025`)까지 구현된 상태다.
- `operations_overview` 대시보드 계약은 이제 위젯별 filter binding, action scope, live detail/export endpoint 범위까지 포함한다.

## 최근 완료 작업

- `2026-04-07` `T-027` `mes_ops` dataset KPI 계산 로직과 paginated detail API를 추가했다. summary 응답은 dataset KPI catalog를 사용하고, `POST /api/v1/analytics/details/source-files/query`가 server-side pagination/sort를 제공한다.
- `2026-04-07` `T-028` filesystem-backed async export workflow를 추가했다. 새 `export/` 모듈이 csv.zip/parquet artifact를 background thread로 생성하고, `POST /api/v1/analytics/exports`, `GET /api/v1/analytics/exports/{job_id}`, `GET /api/v1/analytics/exports/{job_id}/download`가 동작한다.
- `2026-04-07` analytics 테스트용 DuckDB mart fixture를 `tests/conftest.py`로 공통화하고, pipeline/backfill route의 run response 조립 중복을 내부 helper로 축소했다. `tests/test_query_service.py`와 `tests/test_api.py`는 같은 seed mart를 공유하고 기존 응답 계약은 유지된다.
- `2026-04-06` `T-025` 대시보드 정의 endpoint를 추가했다. `operations_overview` 대시보드가 summary/chart/filter endpoint를 묶는 카드/차트/드릴다운/export 메타데이터를 `GET /api/v1/analytics/dashboards/{dashboard_id}`로 제공한다.
- `2026-04-06` `T-026` 대시보드 소비 계약을 구체화했다. `contract_version`, 위젯별 `filter_keys`, action `scope/target_key`, planned detail/export endpoint와 후속 API 범위를 코드와 `spec/query-api-contract.md`에 고정했다.

## 진행 중

- 현재 활성 작업 없음.

## 다음 작업

- Web UI 범위를 별도 작업으로 쪼개고 `operations_overview` dashboard contract를 실제 화면으로 연결한다.
- export retention/cleanup 정책과 admin visibility를 서비스 운영 관점에서 보강한다.

## 블로커 및 리스크

- 현재 analytics backend는 summary/chart/detail/export까지 제공하지만, Web UI와 export admin visibility는 아직 없다.
- 현재 환경에서는 기본 temp 루트 아래 pytest temp-directory fixture가 막혀 있어 `tmp_path` 기반 검증을 그대로 쓰기 어렵다.

## 검증 메모

- `2026-04-07` `python -m compileall src/airflow_lite/analytics src/airflow_lite/api src/airflow_lite/export src/airflow_lite/query tests/test_query_service.py tests/test_api.py tests/test_service.py`가 성공했다.
- `2026-04-07` inline smoke 검증으로 `DuckDBAnalyticsQueryService.query_detail()`, `GET /api/v1/analytics/dashboards/operations_overview?dataset=mes_ops`, `POST /api/v1/analytics/exports`, `GET /api/v1/analytics/exports/{job_id}`, `GET /api/v1/analytics/exports/{job_id}/download`가 기대대로 동작함을 확인했다.
- `2026-04-07` `pytest tests/test_query_service.py tests/test_api.py tests/test_service.py tests/test_settings.py -q --basetemp .tmp_pytest_analytics -p no:cacheprovider`는 테스트 본문 실행 전후 Windows basetemp cleanup 단계의 `PermissionError`로 정상 완료를 기록하지 못했다.
- `2026-04-07` `pytest tests/test_query_service.py tests/test_api.py -q --basetemp .tmp_pytest_refactor -p no:cacheprovider`가 `33 passed`로 성공했다.
- `2026-04-07` 브랜치 `codex/conservative-refactor-fixtures`를 푸시했고 draft PR `#9`를 열었다: `https://github.com/jwleepro/airflow_lite/pull/9`
- `2026-04-06` `pytest tests/test_query_service.py tests/test_api.py -q --basetemp .tmp_pytest -p no:cacheprovider`가 `33 passed`로 성공했다.
- `2026-04-06` `python -m compileall src/airflow_lite/analytics src/airflow_lite/api src/airflow_lite/query tests/test_api.py tests/test_query_service.py`가 성공했다.
- `2026-04-06` `pytest tests/test_query_service.py tests/test_api.py -q --basetemp .tmp_pytest_contract -p no:cacheprovider`는 테스트 본문 실행 후 `pytest_sessionfinish` cleanup 단계에서 `PermissionError`로 종료됐다.
- `2026-04-06` inline Python 수동 검증으로 `DuckDBAnalyticsQueryService.get_dashboard_definition()`과 `GET /api/v1/analytics/dashboards/operations_overview?dataset=mes_ops`가 `contract_version`, widget `filter_keys`, drilldown `scope/target_key`, planned export endpoint를 기대대로 반환함을 확인했다.
- `2026-04-06` 브랜치 `codex/m4-dashboard-definition`를 푸시했고 draft PR `#8`을 열었다: `https://github.com/jwleepro/airflow_lite/pull/8`
## 인수인계

- 저장소는 승격된 DuckDB mart, analytics endpoint, dashboard definition endpoint 위에서 detail/export까지 포함한 `M4` backend 범위를 이어받을 준비가 되어 있다.
- dashboard action은 더 이상 planned metadata만 제공하지 않고, detail/export backend endpoint를 실제로 가리킨다.
- 다음 추천 담당자: Codex 내장 `planner-agent` 또는 프론트엔드 구현 성격의 agent
- 추천 수정 범위:
  - `src/airflow_lite/api/`
  - `src/airflow_lite/export/`
  - `src/airflow_lite/query/`
  - `src/airflow_lite/analytics/`
  - 대시보드/UI 파일이 도입되면 그 경로들
