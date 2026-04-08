# PLAN.md

## 목표

이 저장소를 다음 요소를 기반으로 한 Windows Server 2019 호환 MES 분석 시스템으로 확장한다:

- Oracle 11g 배치 추출
- Parquet raw 저장소
- DuckDB analytics mart
- FastAPI 조회 및 다운로드 API
- 대시보드와 대용량 결과 다운로드 지원

## 현재 마일스톤

`M4. 대시보드 및 시각화 계층`

이 마일스톤의 범위:

- 승격된 DuckDB mart를 사용하는 대시보드 화면 정의
- summary/chart API를 소비하는 시각화 요구사항 정리
- UI 렌더링, drilldown, export UX를 위한 후속 작업 분해

## 마일스톤 상태

- `M0. 기존 Oracle -> Parquet 파이프라인 기반선`: 사용 가능
- `M1. 협업 및 분석 기초`: 완료
- `M2. DuckDB mart 골격`: 완료
- `M3. 조회 및 다운로드 API 확장`: 완료
- `M4. 대시보드 및 시각화 계층`: 진행 중 (`T-025`~`T-030` 완료; 운영 정책/admin control 후속 범위 남음)

## 작업 목록

### 완료

- `T-001` 저장소 운영 가이드로서 `AGENTS.md`를 작성하고 유지한다.
  완료 조건: 저장소 제약, 목표 아키텍처, 디렉터리 구조, 협업 규칙이 문서화되어 있다.
- `T-002` 에이전트와 스킬을 위한 로컬 `.codex` 구성을 만든다.
  완료 조건: `.codex/config.toml`, 역할 설정, 기본 스킬이 추가되어 있다.
- `T-003` 재사용 가능한 Codex 조사 레퍼런스를 만든다.
  완료 조건: `reference/codex/` 문서, 인덱스, 조회 스크립트, 연동 지점이 추가되어 있다.
- `T-004` 저장소 실행 상태 문서를 정착시킨다.
  완료 조건: `PLAN.md`와 `PROGRESS.md`가 존재하고 현재 저장소 상태를 반영하며 다음 에이전트가 바로 사용할 수 있다.
- `T-010` `src/airflow_lite/mart/` 아래에 DuckDB mart 모듈 골격을 만든다.
  완료 조건: 기존 파이프라인을 깨지 않으면서 패키지와 초기 테스트가 존재한다.
- `T-013` 저장소 운영 문서와 Codex 워크플로 사용 지침을 정렬한다.
  완료 조건: `AGENTS.md`, `PLAN.md`, `PROGRESS.md`가 로컬 Codex 워크플로와 일치하고, 저장소가 `CLAUDE.md`에 의존하지 않고 agent/skill 선택법을 문서화한다.
- `T-017` draft PR `#1`의 실제 리뷰 블로커를 해소한다.
  완료 조건: PR `#1`의 조치 가능한 리뷰 3건이 코드/테스트로 반영되거나 저장소 근거로 명시 응답되며, 검증 결과가 `PROGRESS.md`에 기록된다.
- `T-019` 저장소 로컬 agent 레지스트리를 Codex 전용 예외만 남기도록 줄인다.
  완료 조건: `.codex/config.toml`에는 저장소 특화 역할만 남고, 운영 문서가 이를 Codex 내장 agent와 구분한다.
- `T-011` Parquet -> DuckDB refresh 단계 설계를 추가한다.
  완료 조건: refresh orchestration 흐름이 문서화되고 기존 파이프라인에 좁은 mart planning hook이 추가되어 있다.
- `T-012` summary 및 chart API 계약을 설계한다.
  완료 조건: summary/chart/filter 계약이 문서와 코드 기반 스키마 모델로 존재한다.
- `T-020` 저장소 로컬 draft-to-ready 승격 자동화를 제거한다.
  완료 조건: 현재 저장소 문서, skill 등록, CI 워크플로가 더 이상 자동 draft PR 승격을 광고하거나 실행하지 않는다.
- `T-021` 구조화된 GitHub 이슈 접수 폼을 정의하고 추가한다.
  완료 조건: 저장소에 구조화된 issue form YAML과 chooser 구성이 추가되고, 기존 라벨 정책을 유지하면서 상태/자동화 라벨은 maintainer나 workflow만 제어한다.
- `T-022` 구조화된 GitHub issue form용 triage 자동화를 추가한다.
  완료 조건: 새 폼으로 생성된 이슈가 contributor에게 상태/자동화 라벨을 노출하지 않으면서 문서화된 라벨 정책으로 정규화된다.
- `T-023` 구현된 issue intake 기준선에 맞춰 GitHub AI 자동화 플레이북을 정제한다.
  완료 조건: 플레이북이 이미 구현된 issue intake 파일과 미래 워크플로 후보를 명확히 구분하고, issue form과 GitHub Actions 워크플로를 혼동하지 않는다.
- `T-024` GitHub 라벨 카탈로그를 저장소에서 선언하고 동기화한다.
  완료 조건: 플레이북 라벨이 저장소에 선언되고 저장소 관리 경로로 GitHub 라벨 상태를 동기화한다.
- `T-014` refresh plan으로부터 staged DuckDB mart build를 실행한다.
  완료 조건: 검증된 staging 데이터베이스를 `data/mart/current/`로 승격할 수 있다.
- `T-015` read-only analytics query service와 summary/chart endpoint를 추가한다.
  완료 조건: 문서화된 summary/chart 계약이 ad-hoc SQL 노출 없이 read-only endpoint로 제공된다.
- `T-025` analytics summary/chart/filter endpoint 위에 대시보드 정의 endpoint를 추가한다.
  완료 조건: 대시보드 화면이 필요한 카드/차트/필터/드릴다운/export 액션 메타데이터를 단일 API 응답으로 조회할 수 있고, 관련 테스트가 존재한다.
- `T-026` 대시보드 정의 endpoint를 소비하는 프론트엔드 통합 계약과 상세/detail-export 후속 API를 정리한다.
  완료 조건: 대시보드 화면이 `operations_overview` 메타데이터를 안정적으로 소비할 수 있는 계약이 문서화되고, detail/drilldown/export 후속 API 범위가 명시된다.
- `T-027` dataset KPI 계산과 paginated detail API를 구현한다.
  완료 조건: `mes_ops` dataset용 KPI 계산 로직이 summary 응답과 dashboard card 구성에 반영되고, `POST /api/v1/analytics/details/source-files/query`가 서버 측 pagination/sort로 동작하며 관련 테스트가 존재한다.
- `T-028` async export workflow와 `export/` 모듈을 추가한다.
  완료 조건: `POST /api/v1/analytics/exports`, `GET /api/v1/analytics/exports/{job_id}`, `GET /api/v1/analytics/exports/{job_id}/download`가 동작하고, csv.zip/parquet artifact 생성 및 상태 추적이 파일 시스템 기반으로 구현되며 관련 테스트가 존재한다.
- `T-029` `operations_overview` dashboard contract를 소비하는 read-only analytics Web UI와 export admin visibility를 추가한다.
  완료 조건: 운영자가 브라우저에서 dashboard KPI/차트/드릴다운 preview를 확인할 수 있고, export job 상태/만료/download 정보를 별도 화면에서 조회할 수 있으며 관련 테스트와 문서가 갱신된다.
- `T-030` `/monitor` 계열 read-only 운영 화면을 Airflow-inspired operations console 방향으로 재설계한다.
  완료 조건: `/monitor`, `/monitor/analytics`, `/monitor/exports`가 공통 shell, dense table/listing, 상태 배지, 요약 헤더를 공유하고, 기존 read-only 동작과 테스트가 유지된다.
- `T-031` `webui.py` 소스 파일 복구 및 Airflow-inspired 모니터링 UI 고도화.
  완료 조건: webui.py 복구, Run Status Grid/Auto-refresh/Duration/Next Run/Error Summary/Step Timeline 반영, 테스트 통과.

### 현재

- 현재 활성 작업 없음. `T-031` 완료 — `webui.py` 소스 복구 및 Airflow-inspired 모니터링 UI 개선.

### 다음

- `T-032` `/health` 헬스체크 엔드포인트 추가 — DB 연결, 스케줄러 상태, 디스크 여유 확인
- `T-033` export `cleanup_expired` 성능 개선 — 매 요청 전체 스캔 대신 쿨다운 기반 정리
- Windows 서비스 운영 기준에서 export retention/cleanup 정책과 admin visibility를 보강한다.

## 의존 관계

- `T-004`는 planning 워크플로가 완전히 운영되기 전에 완료되어야 한다.
- `T-010`은 `T-011`, `T-012`보다 먼저 시작하는 것이 좋다.
- `T-012`는 최소한 `T-010`의 가안 수준 mart shape에 의존한다.
- `T-014`는 `T-011`에 의존한다.
- `T-015`는 `T-012`와 `T-014`가 만든 실행 가능한 mart에 의존한다.

## 우선순위

1. `/health` 헬스체크 엔드포인트 (T-032)
2. export `cleanup_expired` 성능 개선 (T-033)
3. export job 운영 정책(retention, cleanup, admin visibility)을 강화한다.

## 완료 정의

계획된 작업은 다음을 만족할 때 완료로 간주한다:

- 대상 파일이 존재하거나 올바르게 갱신되어 있다
- 범위가 충분히 좁아 다음 에이전트가 안전하게 이어받을 수 있다
- 검증 상태가 `PROGRESS.md`에 기록되어 있다
- 후속 작업이 있으면 명시적으로 나열되어 있다

## 다음 추천 작업

Windows 서비스 운영 기준의 export retention/cleanup 정책을 구체화하고, 운영 모니터링 화면에서 필요한 후속 admin control 범위를 설계한다.
