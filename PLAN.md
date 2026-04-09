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
- `M4. 대시보드 및 시각화 계층`: 완료

## 작업 목록

### 완료

- `T-037` Pipeline CRUD Admin UI 1차 개선
  - `reference/gemini/pipeline-crud-admin-ui.md` 기반으로 Pipeline DB 모델/저장소/API/Web UI 및 설정 로딩 경로(DB 우선) 반영
  - 관련 테스트 보강 완료 (`test_admin_repository`, `test_settings`, `test_api`)

### 현재

- 현재 활성 작업 없음.

### 다음

- M4 마일스톤 후속 범위 검토 및 M5 정의.

## 의존 관계

- `T-004`는 planning 워크플로가 완전히 운영되기 전에 완료되어야 한다.
- `T-010`은 `T-011`, `T-012`보다 먼저 시작하는 것이 좋다.
- `T-012`는 최소한 `T-010`의 가안 수준 mart shape에 의존한다.
- `T-014`는 `T-011`에 의존한다.
- `T-015`는 `T-012`와 `T-014`가 만든 실행 가능한 mart에 의존한다.

## 우선순위

1. M4 마일스톤 후속 범위 검토 및 M5 정의.

## 완료 정의

계획된 작업은 다음을 만족할 때 완료로 간주한다:

- 대상 파일이 존재하거나 올바르게 갱신되어 있다
- 범위가 충분히 좁아 다음 에이전트가 안전하게 이어받을 수 있다
- 검증 상태가 `PROGRESS.md`에 기록되어 있다
- 후속 작업이 있으면 명시적으로 나열되어 있다

## 다음 추천 작업

M4 마일스톤의 남은 후속 범위를 검토하고, 다음 마일스톤(M5)의 방향을 정의한다.
