# PROGRESS.md

## 현재 상태 요약

- 저장소에는 `.codex` 관례에 맞춘 표준 `AGENTS.md` 운영 가이드가 정리되어 있다.
- 저장소에는 agent와 skill 기반 작업을 위한 로컬 `.codex` 레이아웃이 준비되어 있다.
- 저장소에는 `reference/codex/` 아래 재사용 가능한 Codex 레퍼런스가 있다.
- 저장소 루트에는 공유 실행 상태 문서가 존재한다.
- `M4`는 더 이상 대기 상태가 아니며, 대시보드 정의 API(`T-025`)까지 구현된 상태다.
- `operations_overview` 대시보드 계약은 이제 위젯별 filter binding, action scope, planned detail/export endpoint 범위까지 포함한다.

## 최근 완료 작업

- `2026-04-06` `T-025` 대시보드 정의 endpoint를 추가했다. `operations_overview` 대시보드가 summary/chart/filter endpoint를 묶는 카드/차트/드릴다운/export 메타데이터를 `GET /api/v1/analytics/dashboards/{dashboard_id}`로 제공한다.
- `2026-04-06` `T-026` 대시보드 소비 계약을 구체화했다. `contract_version`, 위젯별 `filter_keys`, action `scope/target_key`, planned detail/export endpoint와 후속 API 범위를 코드와 `spec/query-api-contract.md`에 고정했다.

## 진행 중

- 현재 활성 작업 없음.

## 다음 작업

- dataset별 KPI 계산 로직과 대시보드 전용 summary 카드 구성을 확장한다.
- `T-026`에서 고정한 범위에 맞춰 paginated detail API와 async export API를 구현한다.

## 블로커 및 리스크

- 현재 analytics 계층은 mart 메타데이터 기반 summary와 chart만 제공한다. dataset별 KPI 로직, detail query, export 워크플로는 후속 작업이다.
- 현재 환경에서는 기본 temp 루트 아래 pytest temp-directory fixture가 막혀 있어 `tmp_path` 기반 검증을 그대로 쓰기 어렵다.

## 검증 메모

- `2026-04-06` `pytest tests/test_query_service.py tests/test_api.py -q --basetemp .tmp_pytest -p no:cacheprovider`가 `33 passed`로 성공했다.
- `2026-04-06` `python -m compileall src/airflow_lite/analytics src/airflow_lite/api src/airflow_lite/query tests/test_api.py tests/test_query_service.py`가 성공했다.
- `2026-04-06` `pytest tests/test_query_service.py tests/test_api.py -q --basetemp .tmp_pytest_contract -p no:cacheprovider`는 테스트 본문 실행 후 `pytest_sessionfinish` cleanup 단계에서 `PermissionError`로 종료됐다.
- `2026-04-06` inline Python 수동 검증으로 `DuckDBAnalyticsQueryService.get_dashboard_definition()`과 `GET /api/v1/analytics/dashboards/operations_overview?dataset=mes_ops`가 `contract_version`, widget `filter_keys`, drilldown `scope/target_key`, planned export endpoint를 기대대로 반환함을 확인했다.
- `2026-04-06` 브랜치 `codex/m4-dashboard-definition`를 푸시했고 draft PR `#8`을 열었다: `https://github.com/jwleepro/airflow_lite/pull/8`
## 인수인계

- 저장소는 승격된 DuckDB mart, analytics endpoint, dashboard definition endpoint 위에서 `M4` 후속 시각화 작업을 이어갈 준비가 되어 있다.
- detail/export 실구현은 아직 없고, 현재 dashboard action은 planned contract metadata만 제공한다.
- 다음 추천 담당자: Codex 내장 `planner-agent` 또는 프론트엔드 구현 성격의 agent
- 추천 수정 범위:
  - `src/airflow_lite/api/`
  - `src/airflow_lite/query/`
  - `src/airflow_lite/analytics/`
  - 대시보드/UI 파일이 도입되면 그 경로들
