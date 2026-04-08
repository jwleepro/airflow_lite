# PROGRESS.md

## 현재 상태 요약

- 저장소에는 `.codex` 관례에 맞춘 표준 `AGENTS.md` 운영 가이드가 정리되어 있다.
- 저장소에는 agent와 skill 기반 작업을 위한 로컬 `.codex` 레이아웃이 준비되어 있다.
- 저장소에는 `reference/codex/` 아래 재사용 가능한 Codex 레퍼런스가 있다.
- 저장소 루트에는 공유 실행 상태 문서가 존재한다.
- `M4`는 더 이상 대기 상태가 아니며, 대시보드 정의 API(`T-025`)까지 구현된 상태다.
- `operations_overview` 대시보드 계약은 이제 위젯별 filter binding, action scope, live detail/export endpoint 범위까지 포함한다.
- read-only 운영 모니터링 화면은 이제 파이프라인 실행 현황(`/monitor`)뿐 아니라 analytics dashboard 뷰(`/monitor/analytics`)와 export job 운영 화면(`/monitor/exports`)까지 포함한다.
- `/monitor` 계열 화면은 공통 shell, 상단 상태 요약, dense listing/table, Airflow-inspired muted palette를 공유하는 운영 콘솔 형태로 정리되어 있다.

## 최근 완료 작업

## 진행 중

- 현재 활성 작업 없음.

## 다음 작업

- export retention/cleanup 정책과 admin visibility를 서비스 운영 관점에서 보강한다.
- 운영 모니터링 화면에서 필요한 후속 admin control 범위를 정의한다.

## 블로커 및 리스크

- 현재 작업 기준 활성 블로커 없음.

## 검증 메모

## 인수인계

- 저장소는 승격된 DuckDB mart, analytics endpoint, dashboard definition endpoint 위에서 detail/export까지 포함한 `M4` backend 범위와 read-only 운영 모니터링 화면을 함께 이어받을 준비가 되어 있다.
- dashboard action은 더 이상 planned metadata만 제공하지 않고, detail/export backend endpoint를 실제로 가리킨다.
- `/monitor`는 pipeline inventory + execution history, `/monitor/analytics`는 filterable dashboard workspace, `/monitor/exports`는 export inventory monitor 역할로 분리되어 있다.
- 다음 추천 담당자: Codex 내장 `planner-agent` 또는 운영/API 후속 설계 성격의 agent
- 추천 수정 범위:
  - `src/airflow_lite/api/`
  - `src/airflow_lite/export/`
  - `src/airflow_lite/query/`
  - `src/airflow_lite/analytics/`
  - `README.md`
