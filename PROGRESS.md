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

- UI dead code cleanup 진행 중.
- 범위: `src/airflow_lite/api/static/css/`, `src/airflow_lite/api/templates/`, `tests/`에서 실제 미사용 선택자/자산 정리 및 회귀 확인.

## 다음 작업

- M4 마일스톤 후속 범위 검토 및 M5 정의

## 블로커 및 리스크

## 검증 메모

- UI 라우트/템플릿/렌더러 참조 그래프를 먼저 대조해 삭제 범위를 실제 미사용 코드로 한정했다.

## 인수인계
