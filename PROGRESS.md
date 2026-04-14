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

- `docs/airflow-lite-user-manual.md`에 운영자/사용자용 설치 후 사용 절차, 모니터 화면, 수동 실행, 백필, export, 장애 대응을 정리한 매뉴얼을 추가했다.
- `README.md` Documentation 섹션에 사용자 매뉴얼 링크를 추가했다.
- WebUI helper/template layer에서 실제 템플릿이 사용하지 않는 SVG icon globals(`ICON_EXPORTS`, `ICON_API`)를 제거했다.
- `tests/test_webui_utils.py`에 template environment가 미사용 icon globals를 다시 노출하지 않는 회귀 테스트를 추가했다.
- `/monitor`를 Airflow식 Home 화면으로 축소하고, 기존 DAG inventory를 `/monitor/pipelines` list view로 분리했다.
- sidebar에 `Home`/`DAGs`를 분리 노출하고, run detail 화면이 `DAGs` 컨텍스트로 복귀하도록 정리했다.
- `/monitor/pipelines`에 name/source 검색과 latest-run state(`ok/warn/bad`) 필터를 추가했다.
- Windows export job 삭제 시 파일 잠금으로 인한 간헐 실패를 줄이기 위해 unlink retry를 추가했다.
- `/monitor/pipelines/{name}` DAG details 화면을 추가하고 `Overview / Grid View / Graph View / Runs / Tasks / Details` 탭을 구현했다.
- DAG list와 Home recent activity에서 pipeline 이름이 DAG details로 연결되도록 흐름을 정리했다.
- `/monitor/pipelines/{name}/runs/{run_id}`를 Dag Run view 구조로 재정렬하고 `Task Instances / Events / Code / Details / Graph View` 탭을 구현했다.
- run detail에 recent runs grid sidebar를 추가하고, code tab에는 configured pipeline + run payload snapshot을 노출했다.
- global shell에 breadcrumb를 추가하고, sidebar를 `Operations / Workspaces / Platform` 그룹으로 재정렬했다.
- `Exports`를 workspaces 섹션으로 승격하고, Home/DAGs/DAG Details/Dag Run/Assets/Admin 화면에 계층형 breadcrumb를 연결했다.
- DAG list 행 액션, DAG Details topbar, Dag Run topbar에 `trigger`/`force rerun` 버튼을 연결했다.
- DAG Details에 backfill window form과 action notice를 추가하고, Web UI POST route에서 `runner_map`/`backfill_map`을 직접 호출하도록 연결했다.
- `tests/test_api.py`에 Web UI 운영 액션 redirect와 파라미터 전달 회귀 테스트를 추가했다.

## 진행 중

- 현재 활성 작업 없음.

## 다음 작업

- `T-026` step 1~5 결과 평가 및 잔여 Airflow 차이 정리
- 지원하지 않는 운영 액션 확장 필요 여부 결정
- M4 마일스톤 후속 범위 검토 및 M5 정의

## 블로커 및 리스크

## 검증 메모

- 문서 변경만 포함되어 테스트는 실행하지 않았다.
- `python -m pytest tests\test_webui_utils.py -q --basetemp .tmp_pytest`
- `python -m pytest tests\test_webui_utils.py tests\test_api.py -k "monitor_page_renders_html_with_pipeline_summary or monitor_admin_page_renders_pipeline_section or monitor_analytics_page_renders_dashboard_view or monitor_export_page_creates_and_lists_jobs or root_redirects_to_monitor" -q --basetemp .tmp_pytest`
- `pytest tests\test_api.py tests\test_export_cleanup.py tests\test_webui_utils.py -q --basetemp .tmp_pytest`
- `pytest tests -q --basetemp .tmp_pytest`
- `pytest tests\test_api.py -q --basetemp .tmp_pytest`

## 인수인계

- 브랜치: `codex/docs-user-manual`
- Draft PR: `#34` (`[codex] add airflow_lite user manual`)
- 이번 변경은 문서 범위만 포함하며, 코드/템플릿 동작 변경은 없다.
