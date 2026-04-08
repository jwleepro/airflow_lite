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

- `T-036` 런타임 부트스트랩/설정 외부화/운영 UI 상수 정리 (2026-04-08)
  - `src/airflow_lite/bootstrap.py` 추가 — config path 해석, runtime wiring, export root path 연결, API bind 공통화
  - `src/airflow_lite/config/settings.py` 확장 — `SchedulerConfig`, `WebUIConfig`, 확장된 `ExportConfig`(`max_workers`, `rows_per_batch`, compression) 추가
  - `src/airflow_lite/__main__.py`, `src/airflow_lite/service/win_service.py`가 공통 runtime bootstrap을 사용하도록 정리
  - `src/airflow_lite/api/paths.py`, `src/airflow_lite/api/errors.py` 추가 — 경로/예외 변환 중복 축소
  - `src/airflow_lite/api/routes/web.py`, `src/airflow_lite/api/webui.py`, `src/airflow_lite/scheduler/scheduler.py`, `src/airflow_lite/export/service.py`가 새 설정값을 사용하도록 리팩터링
  - `config/pipelines.sample.yaml`, `tests/test_bootstrap.py`, `tests/test_api.py`, `tests/test_scheduler.py`, `tests/test_service.py`, `tests/test_settings.py` 갱신
- `T-035` export retention/cleanup 정책 및 admin visibility 보강 (2026-04-08)
  - `ExportConfig` dataclass 추가 — YAML에서 `retention_hours`, `cleanup_cooldown_seconds`, `root_path` 설정 가능
  - `DELETE /api/v1/analytics/exports/{job_id}` — 개별 job 삭제 API
  - `DELETE /api/v1/analytics/exports` — 완료 job 일괄 삭제 API
  - `/monitor/exports` UI에 Delete 버튼(개별) + Delete All Completed 버튼 추가
  - `tests/test_export_cleanup.py` 3건, `tests/test_settings.py` 2건 테스트 추가
- `T-032` `/health` 헬스체크 엔드포인트 추가 (2026-04-08)
  - `GET /api/v1/health` — scheduler, mart_db, disk 3개 컴포넌트 상태 확인
  - `src/airflow_lite/api/routes/health.py` 신규, `app.py`에 라우터 등록
  - `tests/test_health.py` 2개 테스트 통과
- `T-033` export `cleanup_expired` 쿨다운 기반 성능 개선 (2026-04-08)
  - `cleanup_cooldown_seconds` 파라미터 추가 (기본 300초)
  - 매 API 호출 시 전체 스캔 → 쿨다운 내 스킵으로 변경
  - `tests/test_export_cleanup.py` 3개 테스트 통과
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

- M4 마일스톤 후속 범위 검토 및 M5 정의.

## 블로커 및 리스크

- draft PR 미생성 — 기존 더티 워크트리(`.claude/settings.local.json`, `reference/claude/`, 기존 health/export cleanup 관련 변경 포함)와 이번 변경이 혼재해 현재 상태로는 안전한 단일 PR 범위가 아님.

## 검증 메모

- Export service cleanup_expired는 이제 쿨다운 기반으로 동작 (T-033 완료).
- 운영 UI(`webui.py`) 내부에는 고립된 top-level dead function은 없었고, 실제 정리 가치는 `api/routes` 서비스 접근 중복과 저장소 전반의 unused import/test residue 제거에 있었다.
- `pytest tests/test_bootstrap.py tests/test_settings.py tests/test_scheduler.py tests/test_service.py tests/test_api.py tests/test_export_cleanup.py tests/test_health.py -q --basetemp .tmp_pytest` 통과 (135 passed)
- `pytest tests -q --basetemp .tmp_pytest_all -m "not integration"` 통과 (312 passed, 46 deselected)

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
