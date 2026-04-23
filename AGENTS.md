# AGENTS.md

> Canonical repository operating guide for Codex and local agents.
> `CLAUDE.md` is reserved for Claude Code and is not part of the Codex workflow.

## 프로젝트 개요

Oracle 11g -> Parquet 배치 ETL 파이프라인(`airflow_lite`)을 DuckDB 기반 MES 조회/분석 시스템으로 확장하는 프로젝트.
단일 Windows Server 환경에서 운영하며, 운영 Oracle 부하를 줄이고 대용량 이력/성능 데이터를 빠르게 제공하는 것이 목표.

## 하드 제약 (협의 없이 변경 금지)

- OS: Windows Server 2019
- Python: 3.11+
- 소스 DB: Oracle 11g (python-oracledb thick mode)
- 분석 엔진: DuckDB
- 배치 ETL만 지원 (실시간 CDC, Kafka, 스트리밍 범위 밖)
- 단일 서버, 비분산 (WSL, K8s, Celery, Redis 금지)
- 폐쇄망(사내망) 운영 가능해야 함

## 아키텍처 레이어

```text
Oracle 11g -> [ingest] -> Parquet raw -> [mart] -> DuckDB -> [serve] -> FastAPI -> Web UI
```

- `ingest`: Oracle에서 청크 단위 추출
- `raw`: 원본 보존용 Parquet (재현 가능한 원천)
- `mart`: DuckDB fact/dimension/summary (재생성 가능한 파생)
- `serve`: API, export, query service
- `ops`: 스케줄, 실행 이력, 로그, 알림

## 핵심 설계 원칙

- Raw(Parquet)와 Mart(DuckDB)를 분리. mart는 raw로부터 재빌드 가능해야 함
- DuckDB는 읽기 중심 서빙. mart 갱신은 임시 DB -> 검증 -> 교체(snapshot 방식)
- 화면은 집계 중심 (summary 우선, 상세는 페이징+필터)
- 다운로드: 소규모 xlsx, 대규모 csv.zip/parquet
- Oracle 부하 최소화: 조회 화면이 Oracle 직접 조회 금지, date/key range 기반 추출

## 기존 기능 (깨뜨리지 말 것)

- Oracle 11g 배치 추출 -> Parquet 적재
- 실행 이력 저장
- APScheduler 기반 스케줄링
- FastAPI 수동 실행/이력 API
- Windows 서비스 실행

## 코딩 규칙

- 새 의존성 추가 시 Windows Server 2019 + Python 3.11+ + 폐쇄망 호환성 필수 검토
- 큰 리라이트 대신 기존 구조 위에 작은 모듈 추가
- 비밀번호, 접속 정보, 경로는 코드에 하드코딩 금지 (설정 파일/환경변수 사용)
- Oracle 호환성, DuckDB 기능, Windows 제약은 추측 말고 검증
- 새 기능에는 최소 1개 이상 테스트 추가
- Oracle 실연동 테스트는 `integration` 영역으로 분리

## 모듈 확장 방향

기존 패키지(`engine`, `extract`, `api`, `storage`, `scheduler`, `service`) 재사용하면서 아래 추가:

- `src/airflow_lite/mart/` - DuckDB build/refresh/snapshot
- `src/airflow_lite/analytics/` - 집계 규칙, KPI 계산, mart SQL
- `src/airflow_lite/query/` - 조회 SQL 생성, 필터 조합, 페이징
- `src/airflow_lite/export/` - xlsx/csv/parquet 다운로드 생성

## 디렉토리 규칙

- `src/` - 애플리케이션 코드만
- `data/`, `var/` - 런타임 산출물, Git 관리 대상 아님
- `data/mart/staging/` -> 검증 후 `current/`로 승격
- `data/mart/snapshots/` - 롤백용 이전 버전 보관
- `tests/unit/` - 순수 로직 단위 테스트
- `tests/integration/` - Oracle, Parquet, DuckDB, API, 배치 흐름 검증

## API 설계 규칙

- summary(KPI), chart(시각화), detail(페이징 상세), export(다운로드), admin(배치/상태)로 구분
- 기본 응답은 UI 렌더링 최소 데이터만
- 서버 측 필터링/정렬/페이징 기본
- DuckDB에 ad-hoc SQL 자유도 직접 노출 금지
- 다운로드와 화면 조회 엔드포인트 분리

## Codex 협업 워크플로우

### Agent 선택 기준

이 저장소가 별도로 유지하는 repository-local custom agent는 아래 3개를 둔다.

- `codex-meta-agent`: `.codex/`와 `reference/codex/` 구조나 규칙 수정
- `github-automation-agent`: GitHub Actions CI, PR gate, label, publish workflow 자동화
- `github-issue-cycle-agent`: milestone 순서 이슈 처리, `In Progress` 상태 동기화, 이슈별 git worktree 분리 실행

그 외 planning, indexing, mart, query API, export, ops, review, test, docs 성격의 작업은 Codex 기본 제공 agent를 그대로 사용한다. 같은 이름의 역할이 있더라도 이 저장소에서는 별도 로컬 정의를 추가로 유지하지 않는다.

### Skill 선택 기준

- `project-bootstrap`: 새 Codex 스레드 시작, handoff 직후 현재 상태 요약
- `progress-discipline`: `PLAN.md`와 `PROGRESS.md`를 시작, 변경, 완료, handoff에 맞게 유지
- `repo-indexing`: 익숙하지 않은 코드 영역의 구조와 영향 범위 파악
- `task-slicing`: 일이 크거나 여러 agent로 쪼개야 할 때
- `reference-reader`: `.codex/` 또는 `reference/codex/` 수정 전 관련 reference 선별
- `github:yeet`: 로컬 변경을 의도적으로 커밋, 푸시하고 draft PR까지 열어야 할 때 사용
- `duckdb-mart-design`, `api-contract-design`, `export-policy`, `windows-ops`, `oracle-batch-etl` 등 도메인 skill: 해당 영역 설계나 구현에 직접 들어갈 때

### 추천 사용 흐름

1. 새 작업 시작: `project-bootstrap`
2. 다음 작업 선택이 애매함: Codex 기본 `planner-agent`
3. 수정 착수: `progress-discipline`
4. `.codex/` 수정: `reference-reader` -> 필요 시 `codex-meta-agent`
5. PR 자동화 설계/구현: `github-automation-agent`
6. 구현 후 검증: Codex 기본 `review-agent`, `test-agent`
7. 작업 종료: 관련 검증이 끝나면 `github:yeet` 또는 동등한 GitHub 흐름으로 draft PR 생성

### 작업 종료 및 PR 생성

- 기본 원칙: 사용자가 명시적으로 중단을 요청하지 않았다면 작업 종료 시 draft PR 생성까지 완료한다.
- 선행 조건: 변경 범위 확인, 관련 테스트/검증 실행, 혼합 워크트리 여부 확인을 먼저 끝낸다.
- 기본 수단: GitHub 플러그인의 `github:yeet` skill을 우선 사용해 브랜치, 커밋, 푸시, draft PR 생성까지 마무리한다.
- 예외: GitHub 원격 저장소 접근 불가, 인증 누락, 사용자의 PR 보류 지시가 있으면 PR 생성 대신 blocker를 보고한다.
- 기록: 최종 응답과 `PROGRESS.md`에는 검증 결과, 브랜치명, PR 상태 또는 생성 실패 사유를 남긴다.

## 작업 전 체크리스트

1. 기존 Oracle -> Parquet 파이프라인을 깨지 않는가?
2. Oracle 대신 DuckDB 조회로 해결되는가?
3. Windows Server 2019에서 운영 가능한가?
4. 배치 ETL 범위를 넘지 않는가?
5. 테스트나 로그로 검증 가능한가?

## 협업 문서

- `PLAN.md` - 작업 계획, 우선순위, 완료 조건
- `PROGRESS.md` - 진행 상태, 블로커, handoff 메모

## 빌드 & 테스트 명령어

```bash
# 테스트 실행
pytest tests/

# 패키지 설치 (개발 모드)
pip install -e ".[dev]"
```

- 로컬 agent는 저장소에 `.venv`가 있으면 해당 가상환경의 Python 인터프리터를 우선 사용해 설치·테스트를 실행한다.
