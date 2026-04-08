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

- `T-031` webui.py 소스 복구 및 Airflow-inspired 모니터링 UI 개선 (2026-04-08)
  - Run Status Grid, Auto-refresh, Duration, Next Run, Error Summary, Step Timeline(Gantt) 추가
  - `web.py`: `/monitor/pipelines/{name}/runs/{run_id}` 상세 라우트 추가, limit 5→25 변경, next_run 계산
  - `pytest tests/test_api.py` 33개 전체 통과
- `T-034` 운영 모니터링 UI 및 API 주변 dead code 정리와 경량 리팩토링 (2026-04-08)
  - `src/airflow_lite/api/dependencies.py` 추가로 analytics/web 라우트의 query/export service 접근 중복 제거
  - 운영 UI 주변과 저장소 전반의 unused import, 타입 annotation 잔여물, 테스트 dead code 제거
  - `python -m ruff check src tests`, `pytest tests/test_api.py tests/test_backfill.py tests/test_engine.py tests/test_extract.py tests/test_settings.py -q --basetemp .tmp_pytest`, `pytest tests -q --basetemp .tmp_pytest_unit -m "not integration"` 통과

## 진행 중

- 현재 활성 작업 없음.

## 다음 작업

- `T-032` `/health` 헬스체크 엔드포인트 추가 — DB 연결, 스케줄러 상태, 디스크 여유 확인
- `T-033` export `cleanup_expired` 성능 개선 — 쿨다운 기반 정리
- export retention/cleanup 정책과 admin visibility를 서비스 운영 관점에서 보강한다.

## 블로커 및 리스크

- 현재 활성 블로커 없음.

## 검증 메모

- Export service cleanup_expired 매 API 호출 시 전체 파일 스캔 — 성능 개선 필요 (T-033).
- 운영 UI(`webui.py`) 내부에는 고립된 top-level dead function은 없었고, 실제 정리 가치는 `api/routes` 서비스 접근 중복과 저장소 전반의 unused import/test residue 제거에 있었다.

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
