# AI Agent Coding Workflow

> GPT-5.3 / Codex를 포함한 코딩 에이전트와 자동화 도구를 이용해 범용 소프트웨어 개발 워크플로를 설계하기 위한 운영 문서
>
> 이 문서는 특정 벤더, 특정 모델, 특정 제품 유형에 종속되지 않는 `개발자 + AI agent + 자동화 도구` 협업 모델을 설명한다.
>
> 여기서 AI agent는 Codex, GPT-5.3 기반 code agent, 기타 코드 생성/리뷰/검증 agent를 모두 포함한다. 또한 이 문서는 GPT 연동 애플리케이션을 만드는 경우만 다루지 않는다. 일반 백엔드, 라이브러리, 배치, CLI, UI, 내부 업무 시스템 개발에도 그대로 적용할 수 있다.

---

## 1. 문서 목표

이 문서의 목표는 소프트웨어 개발을 아래의 `문제 해결 파이프라인`으로 운영하는 것이다.
아래 항목은 무작위 목록이 아니라, 기본 진행 순서를 나타내는 반복형 개발 루프다.

```text
문제 정의
  -> 기계가 읽을 수 있는 명세 생성
  -> 코드베이스 인덱싱
  -> 작업 단위 분해
  -> AI 구현
  -> 자동 검증
  -> 실패 번들 생성
  -> AI 수정
  -> 시나리오 검증
  -> 비기능 검증
  -> 릴리스 게이트
  -> 운영 피드백 축적
```

실행 중에는 일부 단계가 반복해서 되돌아가지만, 기본 흐름은 아래 순서를 따른다.
각 단계의 의미를 짧게 풀면 아래와 같다.

| 단계 | What | How |
|---|---|---|
| 문제 정의 | 이번 사이클에서 해결해야 할 문제를 한 문장과 경계 조건으로 고정한다. | 요구사항, 장애, 개선 요청을 정리하고 성공 조건과 제외 범위를 명시한다. |
| 기계가 읽을 수 있는 명세 생성 | 사람이 쓴 요구를 AI와 자동화 도구가 처리할 수 있는 구조화된 입력으로 바꾼다. | 목표, 범위, 승인 기준, 우선순위를 JSON/YAML 같은 정형 형식으로 정리한다. |
| 코드베이스 인덱싱 | AI가 저장소를 추측하지 않도록 현재 코드 구조를 기계적으로 설명한다. | 모듈, 심볼, 의존 관계, 테스트, 진입점을 스캔해 인덱스를 만든다. |
| 작업 단위 분해 | 큰 변경을 검증 가능한 작은 작업으로 나눈다. | 영향 범위, 완료 정의, 병렬 가능 여부를 기준으로 task를 쪼갠다. |
| AI 구현 | 각 task에 대한 실제 코드 변경 초안을 만든다. | task bundle을 입력으로 넣어 patch, 테스트 초안, 작업 로그를 생성하게 한다. |
| 자동 검증 | 변경이 기본 품질 기준을 통과하는지 즉시 확인한다. | 테스트, 린트, 타입체크, 계약 검증을 자동 실행한다. |
| 실패 번들 생성 | 실패 원인을 AI가 다시 수정할 수 있는 입력으로 압축한다. | 실패 명령, 로그, stack trace, 최근 diff, 재현 절차를 한 묶음으로 저장한다. |
| AI 수정 | 검증 실패를 반영해 patch를 반복 개선한다. | failure bundle을 입력으로 넣고 수정 patch와 보완 테스트를 다시 생성한다. |
| 시나리오 검증 | 개별 테스트 통과와 별개로 실제 사용 흐름이 성립하는지 본다. | CLI, API, UI, 배치 흐름을 fixture와 설정으로 재생한다. |
| 비기능 검증 | 기능 외 품질 속성이 목표 수준인지 확인한다. | 성능, 보안, 안정성, 운영성, 호환성 점검을 자동 실행한다. |
| 릴리스 게이트 | 결과를 종합해 배포 가능 여부를 판정한다. | diff, 검증 리포트, 위험 항목, 승인 기준 충족 여부를 한 번에 평가한다. |
| 운영 피드백 축적 | 이번 사이클의 성공/실패를 다음 사이클의 규칙으로 남긴다. | postmortem, 승인 패턴, 재발 방지 규칙, 체크리스트를 지식 저장소에 기록한다. |

핵심은 세 가지다.

1. 개발자는 문제 정의와 승인에 집중한다.
2. AI agent는 구현, 검증, 수정의 반복 실행자가 된다.
3. 자동화 도구는 문맥 정리, 실행, 판정, 기록을 맡는다.

---

## 2. 기본 원칙

이 워크플로는 특정 언어, 프레임워크, 도메인에 묶이지 않는다. 대신 아래 원칙을 공통 규칙으로 둔다.

### 2.1 개발자가 소유해야 하는 것

- 문제 정의
- 제품/도메인 제약
- 우선순위 결정
- 운영 위험 판단
- 최종 승인

### 2.2 AI agent에게 위임할 수 있는 것

- 반복 구현
- 테스트 초안 생성
- 실패 로그 해석
- 패턴 기반 수정
- 비교 실험 요약
- 문서 초안 작성

### 2.3 도구가 맡아야 하는 것

- 문서 구조화
- 코드베이스 인덱싱
- 작업 패키지 생성
- 검증 실행
- 실패 정보 정리
- 릴리스 판정

### 2.4 프로젝트 제약은 하드코딩하지 않는다

이 문서는 어떤 프로젝트의 고유 제약도 전제로 하지 않는다.
대신 각 프로젝트는 별도의 `project-profile`을 이 워크플로에 주입한다.

예를 들어 프로젝트 프로파일에는 아래 같은 내용만 담는다.

- 런타임 환경
- 지원해야 하는 플랫폼
- 보안/규제 요구
- 성능 목표
- 호환성 규칙
- 릴리스 게이트
- 금지된 변경 영역

즉, 워크플로는 고정이고 제약은 주입된다.

### 2.5 개발 도구와 개발 대상은 구분한다

GPT-5.3이나 Codex를 사용해 개발한다고 해서 결과물이 GPT와 연동되는 제품일 필요는 없다.
이 문서에서 AI는 `개발 수행 수단`이며, 대상 프로젝트는 일반 소프트웨어 시스템 전체를 포함한다.

예를 들어 아래는 모두 이 문서의 대상이다.

- 배치 파이프라인
- 백엔드 API 서버
- 라이브러리 / SDK
- CLI 도구
- 프론트엔드 / UI
- 사내 업무 시스템

### 2.6 단일 agent를 전제하지 않는다

이 워크플로는 하나의 모델이나 하나의 agent만 쓰는 형태를 강제하지 않는다.
작업 성격에 따라 구현 agent, 리뷰 agent, 수정 agent, 시나리오 검증 agent를 분리할 수 있다.
같은 벤더의 모델을 역할별로 다르게 쓸 수도 있고, 서로 다른 AI agent를 조합할 수도 있다.

이 문서에서 이후 `AI`라는 표현은 단일 모델이 아니라, 작업에 따라 교체 가능한 하나 이상의 AI agent 집합을 뜻한다.

---

## 3. 필수 입력 산출물

이 워크플로를 자동화하려면 사람 문장만으로는 부족하다.
아래 산출물이 계속 갱신되어야 한다.

| 산출물 | 역할 |
|---|---|
| `project-profile.json` | 프로젝트별 제약, 금지사항, 비기능 목표 |
| `spec.json` | 이번 사이클에서 해결할 요구사항과 승인 기준 |
| `repo-index.json` | 코드베이스 구조, 심볼, 테스트, 진입점 인덱스 |
| `tasks/*.json` | AI agent가 처리할 원자 작업 단위와 역할, 쓰기 범위 |
| `bundles/*.json` | 특정 작업에 필요한 문맥 패키지와 agent 실행 지시 |
| `check-report.json` | 자동 검증 결과 |
| `failure-bundle.json` | 수정에 필요한 실패 정보 묶음 |
| `scenario-report.json` | 실제 사용 흐름 검증 결과 |
| `nonfunctional-report.json` | 성능, 보안, 운영성 결과 |
| `gate-report.json` | 릴리스 가능 여부 판정 |

---

## 4. 먼저 만들어야 하는 기반 도구

자동화된 AI 개발 루프는 모델보다 `도구 계층`이 먼저다.
가능하면 모든 도구는 CLI와 JSON 출력을 지원한다.

| 우선순위 | 도구명 | 목적 | 최소 입력 | 최소 출력 |
|---|---|---|---|---|
| 1 | `profile-compiler` | 프로젝트 문서를 `project-profile.json`으로 정규화 | 운영 문서, 설계 문서 | `project-profile.json` |
| 2 | `spec-compiler` | 요구사항과 승인 기준을 `spec.json`으로 변환 | 기획/이슈/문서 | `spec.json` |
| 3 | `repo-indexer` | 저장소 구조와 심볼을 인덱싱 | 소스, 테스트, 설정 | `repo-index.json` |
| 4 | `task-slicer` | 큰 요구사항을 원자 작업으로 분해 | `project-profile.json`, `spec.json`, `repo-index.json` | `tasks/*.json` |
| 5 | `context-bundler` | 특정 작업용 입력 패키지 생성 | `task.json` | `bundle.json` |
| 6 | `agent-runner` | AI 실행기. bundle을 읽고 지정된 agent를 호출해 구현 로그와 결과를 저장 | `bundle.json` | `result.json`, patch |
| 7 | `check-runner` | 테스트, 린트, 타입체크, 계약검증 실행 | 변경 파일 또는 `task-id` | `check-report.json` |
| 8 | `failure-bundler` | 실패한 실행 결과를 수정 패키지로 압축 | `check-report.json`, logs | `failure-bundle.json` |
| 9 | `scenario-runner` | 시스템을 실제로 사용해 시나리오 실행 | fixture, config, profile | `scenario-report.json` |
| 10 | `nonfunctional-runner` | 성능, 보안, 운영성, 호환성 점검 | profile, dataset, deploy config | `nonfunctional-report.json` |
| 11 | `release-gate` | 모든 결과를 모아 릴리스 판정 | reports, diff, profile | `gate-report.json` |
| 12 | `knowledge-writer` | 승인된 패턴과 실패 교훈을 규칙으로 축적 | reports, postmortem | `patterns/*.md`, `lessons/*.json` |

### 4.1 멀티 agent 운영 최소 규칙

- 각 task는 담당 역할과 쓰기 범위를 가진다.
- agent 간 handoff는 `task`, `bundle`, `result` 같은 구조화된 산출물로 한다.
- 병렬 실행 시 쓰기 범위가 겹치는 task는 동시에 실행하지 않는다.
- 구현 agent와 검증/review agent는 분리할 수 있다.
- 특정 agent에 종속된 프롬프트보다, 어떤 agent로도 해석 가능한 구조화 입력을 우선한다.

### 4.2 도구별 최소 기능

#### `profile-compiler`

프로젝트의 장기 제약을 정규화한다.

- 지원 플랫폼
- 배포 방식
- 성능 목표
- 보안/규제 요구
- 호환성 범위
- 금지사항

#### `spec-compiler`

이번 사이클에서 해결할 문제를 구조화한다.

- 목표
- 범위
- 제외 범위
- 승인 기준
- 우선순위

#### `repo-indexer`

AI가 코드베이스를 추측하지 않게 만든다.

- 모듈 목록
- 클래스/함수 시그니처
- import 관계
- 테스트 매핑
- 설정 파일 경로
- 엔트리포인트
- public API 표면

#### `task-slicer`

큰 일을 검증 가능한 작은 작업으로 쪼갠다.

- 수정 범위
- 영향받는 테스트
- 완료 정의
- 병렬 가능 여부
- 위험도

#### `context-bundler`

AI에게 전체 저장소를 주지 않고 필요한 문맥만 준다.

- 작업 설명
- 관련 파일
- 관련 코드
- 테스트 명령
- 금지사항
- 완료 정의

#### `agent-runner`

AI 실행을 재현 가능하게 만든다.

- agent / model 선택 규칙
- execution 프로파일
- 작업 로그 저장
- patch 추적
- 재시도 정책
- 파일별 쓰기 범위 제한
- handoff metadata 저장

#### `check-runner`

작업별 검증을 빠르게 실행한다.

- 관련 단위 테스트
- 영향받는 통합 테스트
- 린트
- 타입 체크
- 계약 검증

#### `failure-bundler`

실패를 수정 가능한 형태로 바꾼다.

- 실패 명령
- exit code
- stack trace
- 실패 테스트
- 최근 diff
- 재현 절차
- 로그 tail

#### `scenario-runner`

AI가 실제로 시스템을 사용해 보게 만든다.

- CLI 흐름
- API 흐름
- 사용자 플로우
- 설정 기반 실행
- 장애/복구 시나리오

#### `nonfunctional-runner`

기능 외 요구를 자동 판정한다.

- 성능
- 자원 사용량
- 보안 점검
- 운영성
- 호환성

#### `release-gate`

릴리스 전 판정기를 만든다.

- 필수 테스트 통과 여부
- 시나리오 통과 여부
- 비기능 기준 충족 여부
- 리스크 요약
- 차단 사유 명시

### 4.3 2026년 기준 현실 도구 예시

이 문서는 벤더 중립 추상화를 유지하지만, 실제 팀 도입 시에는 아래처럼 널리 쓰이는 도구 조합으로 구현하는 경우가 많다.

아래 목록은 `2026-03` 기준 공개 자료가 있는 경우는 그 자료를 따르고, 없는 경우는 공식 문서와 생태계 채택 신호를 바탕으로 고른 `대표 예시`다.
즉, 엄밀한 전 세계 점유율 순위표가 아니라 "실무에서 자주 보이는 상위권 후보"로 읽는 편이 맞다.

| 운영 항목 | 대표 도구 예시 (2026) | 이 문서에서 대응되는 추상 계층 | 메모 |
|---|---|---|---|
| 코딩 agent 실행 | `GitHub Copilot coding agent`, `Claude Code`, `Cursor Agent` | `agent-runner`, Stage 4 | 구현, 수정, PR 생성까지 직접 수행하는 실행 계층 |
| 팀 규칙 / 헌법 / 온보딩 | `CLAUDE.md`, `Cursor Rules`, `GitHub Copilot custom instructions` | `project-profile`, `spec`, Stage 0-3 | AI가 문제를 임의 재정의하지 못하게 만드는 상위 규칙 계층 |
| 반복 명령 / 작업 템플릿 | `Claude Code slash commands`, `GitHub Copilot prompt files`, `Cursor Custom Modes` | `spec-compiler`, `context-bundler`, Stage 0-3 | 자주 쓰는 작업을 재사용 가능한 명령/프롬프트로 고정 |
| 외부 도구 연결 | `MCP`, `GitHub MCP Server`, `Playwright MCP` | `context-bundler`, `agent-runner`, `scenario-runner` | 저장소, 브라우저, 외부 시스템을 AI가 직접 다루게 하는 연결 계층 |
| 이슈 / 백로그 관리 | `Jira`, `GitHub Issues + Projects`, `Linear` | `spec-compiler`, `task-slicer` | 요구사항을 task로 구조화하고 우선순위를 관리하는 계층 |
| 품질 가드레일 / Hook | `Claude Code Hooks`, `pre-commit`, `Husky` | `check-runner`, `release-gate`, Stage 5-8 | 실수 방지, 규칙 강제, 커밋 전 자동 검사에 자주 사용 |
| PR / 코드리뷰 / CI | `GitHub Actions`, `CodeRabbit`, `SonarQube` | `check-runner`, `release-gate` | 자동 검증, PR 리뷰, 병합 전 차단 규칙에 주로 사용 |
| 브라우저 / E2E / 시나리오 검증 | `Playwright`, `Cypress`, `Selenium` | `scenario-runner` | unit test 밖의 실제 사용자 흐름 검증에 적합 |
| 인프라 / IaC / 배포 | `Terraform`, `OpenTofu`, `Pulumi` | `project-profile`, Stage 7-8 | 인프라 변경을 코드와 검증 파이프라인 안으로 넣는 계층 |
| 운영 관측 / 장애 추적 | `Grafana + Prometheus`, `Sentry`, `Langfuse` | `nonfunctional-runner`, Stage 7-9 | 서비스 운영 지표, 오류, AI 호출 품질을 추적하는 계층 |
| 멀티 agent / 오케스트레이션 | `LangChain`, `LangGraph`, `Ollama` | 멀티 agent 운영 규칙, handoff, Stage 2-6 | 여러 agent를 묶거나 로컬/사내 실행 환경을 구성할 때 자주 보임 |

#### 도구 표를 읽는 방법

- 이 문서의 `profile-compiler`, `task-slicer`, `context-bundler` 같은 이름은 "반드시 그 제품을 써라"가 아니라 "그 역할을 수행하는 계층이 필요하다"는 뜻이다.
- 예를 들어 규칙 계층은 `CLAUDE.md` 하나로 끝나는 것이 아니라, `CLAUDE.md` + `Hooks` + `prompt files` + 저장소 규칙 문서 조합으로 운영되는 경우가 많다.
- GitHub 중심 조직이면 `GitHub Copilot`, `GitHub Actions`, `GitHub Issues`, `CodeRabbit` 조합이 자연스럽고, Claude 중심 조직이면 `Claude Code`, `MCP`, `Playwright MCP`, `CLAUDE.md` 조합이 자연스럽다.
- 따라서 실제 도입에서는 "도구명"보다 "어떤 추상 계층을 어떤 조합으로 채우는가"를 먼저 결정하는 편이 안전하다.

---

## 5. 단계별 절차형 워크플로

아래 단계는 범용 순서다.
프로젝트마다 세부 체크 항목만 바뀌고 뼈대는 그대로 유지한다.

### Stage 0. 운영 계약 고정

#### 목적

AI가 문제를 임의로 재정의하지 못하게 한다.

#### 개발자가 할 일

- 이번 사이클의 목표를 한 문장으로 고정한다.
- 성공 기준을 테스트 가능한 문장으로 바꾼다.
- 이번 작업의 제외 범위를 적는다.
- 치명적 리스크를 명시한다.

#### AI가 할 일

- 모호한 표현을 표시한다.
- 누락된 승인 기준을 제안한다.
- 측정 가능한 acceptance criteria 초안을 만든다.

#### 필요한 도구

- `profile-compiler`
- `spec-compiler`

#### 절차

1. 개발자가 목표, 범위, 제외 범위를 입력한다.
2. `profile-compiler`가 장기 제약을 정리한다.
3. `spec-compiler`가 이번 사이클용 `spec.json`을 만든다.
4. AI가 모호성, 충돌, 누락을 검토한다.
5. 개발자가 최종 승인한다.

#### 산출물

- `project-profile.json`
- `spec.json`

#### 완료 기준

- "무엇을 왜 하는가"가 구조화되어 있다.
- 나중에 자동 판정 가능한 승인 기준이 있다.

---

### Stage 1. 코드베이스 문맥 기계화

#### 목적

AI가 매 작업마다 저장소를 처음부터 해석하지 않게 한다.

#### 개발자가 할 일

- 핵심 모듈과 진입점을 표시한다.
- 변경 금지 영역을 지정한다.
- 표준 테스트/실행 명령을 정한다.

#### AI가 할 일

- 저장소 구조를 분석한다.
- 모듈, 테스트, 설정, 엔트리포인트를 연결한다.
- 재사용 가능한 기존 패턴을 찾는다.

#### 필요한 도구

- `repo-indexer`

#### 절차

1. `repo-indexer`가 전체 저장소를 인덱싱한다.
2. 코드 구조, 심볼, 테스트, 엔트리포인트를 JSON으로 저장한다.
3. AI가 관련 영역을 요약한다.
4. 이 요약을 task slicing의 입력으로 사용한다.

#### 산출물

- `repo-index.json`
- `module-map.md`
- `test-map.json`

#### 완료 기준

- 관련 파일과 관련 테스트가 추측이 아니라 인덱스로 설명된다.

---

### Stage 2. 작업 단위 원자화

#### 목적

AI가 너무 넓은 변경을 하지 못하게 한다.

#### 개발자가 할 일

- 큰 목표를 리뷰 가능한 묶음으로 나눈다.
- 우선순위와 의존관계를 정한다.
- 병렬 가능한 작업과 순차 작업을 구분한다.

#### AI가 할 일

- 최소 수정 범위를 가진 task 분해안을 제안한다.
- 각 task에 테스트 전략과 위험도를 붙인다.
- 사람이 놓친 선행조건을 표시한다.

#### 필요한 도구

- `task-slicer`
- `repo-indexer`

#### 절차

1. `task-slicer`가 `project-profile.json`, `spec.json`, `repo-index.json`을 읽는다.
2. 요구사항을 원자 작업으로 분해한다.
3. 각 task에 아래 항목을 붙인다.
    - 목적
    - 담당 agent 역할
    - 선호 agent 또는 금지 agent
    - 수정 가능 파일
    - 영향받는 테스트
    - 금지사항
    - 완료 정의
4. 개발자가 분해 결과를 승인한다.

#### task 예시

```json
{
  "task_id": "TASK-042",
  "title": "Public API validation 강화",
  "owner_role": "implementation-agent",
  "preferred_agents": [
    "codex",
    "gpt-5.3-based-agent",
    "other-code-agent"
  ],
  "editable_files": [
    "src/package/api.py",
    "tests/test_api_contract.py"
  ],
  "write_scope": [
    "src/package/api.py",
    "tests/test_api_contract.py"
  ],
  "must_pass": [
    "tests/test_api_contract.py"
  ],
  "handoff_to": [
    "review-agent",
    "scenario-agent"
  ],
  "done_when": [
    "호환성 규칙을 위반하는 입력이 명확히 차단된다",
    "기존 public API 시그니처는 유지된다"
  ]
}
```

#### 산출물

- `tasks/*.json`
- `dependency-graph.json`

#### 완료 기준

- 각 작업이 작고 리뷰 가능하다.
- 각 작업마다 명확한 검증 경로가 있다.

---

### Stage 3. AI 입력 패키지 생성

#### 목적

AI에게 필요한 정보만 정제해서 준다.

#### 개발자가 할 일

- 이번 작업에서 특별히 조심해야 할 제약을 추가한다.
- 사람 승인 없이 바꾸면 안 되는 파일을 지정한다.

#### AI가 할 일

- 관련 코드와 참고 패턴을 수집한다.
- 이 작업에 필요한 최소 문맥만 묶는다.
- 불필요한 주변 정보는 제거한다.

#### 필요한 도구

- `context-bundler`
- `repo-indexer`

#### 절차

1. `context-bundler`가 `task.json`을 읽는다.
2. 관련 파일, 코드 발췌, 테스트, 제약을 묶는다.
3. 작업 전용 `bundle.json`을 만든다.
4. AI는 bundle 바깥의 사실을 함부로 가정하지 않는다.

#### bundle 최소 구성

- task 설명
- 목적
- 담당 agent 역할
- 선호 agent / fallback agent
- 수정 가능한 파일
- 쓰기 범위
- 관련 테스트
- 참고 구현
- 금지사항
- handoff 대상과 승인 체크포인트
- 완료 정의

#### 산출물

- `bundles/<task_id>.json`

#### 완료 기준

- AI가 구현보다 탐색에 더 많은 시간을 쓰지 않는다.

---

### Stage 4. 에이전트 구현 루프

#### 목적

선정된 구현 agent가 첫 구현과 첫 테스트 세트를 만든다.

#### 개발자가 할 일

- execution profile과 사용할 agent를 선택한다.
- 고위험 작업은 구조 초안이나 설계 힌트를 준다.
- 자동 재시도 한계를 정한다.

#### AI가 할 일

- 관련 파일을 읽고 영향 범위를 확인한다.
- 기존 패턴을 최대한 재사용한다.
- 필요한 최소 수정만 한다.
- 변경과 함께 테스트도 갱신한다.

#### 필요한 도구

- `agent-runner`
- `context-bundler`

#### 절차

1. `agent-runner`가 `bundle.json`을 읽고 적절한 구현 agent를 호출한다.
2. 구현 agent는 관련 파일을 읽고 작업 범위를 확정한다.
3. 구현 agent는 코드 수정안을 만든다.
4. 구현 agent는 관련 테스트를 보강한다.
5. 결과를 patch와 실행 로그로 저장한다.

#### 개발자가 개입해야 하는 시점

- 아키텍처 경계가 바뀌는 경우
- 데이터 모델이나 public API가 바뀌는 경우
- 보안 또는 운영 리스크가 큰 경우

#### 산출물

- 코드 patch
- 변경 요약
- AI 생성 테스트

#### 완료 기준

- 수정이 task 범위를 넘지 않는다.
- 로그만으로도 AI가 무엇을 했는지 추적 가능하다.

---

### Stage 5. 자동 검증과 자동 수정 루프

#### 목적

구현 agent가 만든 코드를 검증 agent 또는 동일 agent가 다시 검증하고, 실패하면 수정 agent가 고치게 한다.

#### 개발자가 할 일

- 필수 검증 세트를 정의한다.
- 무한 수정 루프를 막기 위한 재시도 횟수를 정한다.
- 사람 검토가 필요한 실패 유형을 구분한다.
- 같은 agent로 수정할지, 별도 수정 agent로 handoff할지 정한다.

#### AI가 할 일

- 테스트와 정적 검사를 실행한다.
- 실패 원인을 로그 기반으로 해석한다.
- 수정 가능한 실패는 즉시 패치한다.
- 같은 실패가 반복되면 가설을 바꿔 다시 시도한다.

#### 필요한 도구

- `check-runner`
- `failure-bundler`
- `agent-runner`

#### 절차

1. `check-runner`가 task 전용 검증을 실행한다.
2. 실패 시 `failure-bundler`가 수정용 패키지를 만든다.
3. `agent-runner`가 `failure-bundle.json`을 읽고 동일 agent 또는 별도 수정 agent를 호출한다.
4. 다시 `check-runner`를 실행한다.
5. N회 반복 후에도 실패하면 사람에게 에스컬레이션한다.

#### 권장 정책

- 단순 테스트 실패: AI 자동 수정 2~3회
- 설계 충돌: 즉시 사람 검토
- flaky 테스트 의심: 사람 승인 필요
- 보안 경고: 자동 병합 금지

#### 산출물

- `check-report.json`
- `failure-bundle.json`
- 수정된 patch

#### 완료 기준

- task 단위 필수 검증이 모두 통과한다.

---

### Stage 6. 시스템 자가 사용(Self-use) 루프

#### 목적

AI가 만든 결과물을 시나리오 검증 agent가 실제 사용 흐름으로 검증하게 한다.
이 단계가 없으면 unit test만 통과하고 실제 사용에서 무너질 수 있다.

#### 개발자가 할 일

- 대표 사용자 시나리오를 정의한다.
- 정상/실패/복구 경로를 모두 준비한다.
- fixture, sample config, example input을 제공한다.

#### AI가 할 일

- 실제 명령, API, UI, 설정 흐름을 실행한다.
- 장애나 오류를 일부러 유발해 복구 경로를 검증한다.
- 실제 사용 로그를 해석해 수정 필요 여부를 판단한다.

#### 필요한 도구

- `scenario-runner`
- `failure-bundler`
- `agent-runner`

#### 프로젝트 유형별 대표 시나리오 예시

- 라이브러리: 예제 consumer 프로젝트에서 import와 호출
- API 서버: 주요 엔드포인트 호출, 오류 응답, 재시도, 롤백
- CLI 도구: 실제 명령 시퀀스, 옵션 조합, 실패 복구
- 배치/파이프라인: 설정 파일 기반 실행, 재실행, 장애 복구
- 프론트엔드: 주요 사용자 플로우, 빈 상태, 오류 상태, 접근성

#### 절차

1. `scenario-runner`가 시나리오를 실행한다.
2. 시나리오 검증 agent가 실행 로그와 결과를 읽는다.
3. 실패 시 `failure-bundler`로 수정 패키지를 만든다.
4. 수정 agent가 패치 후 다시 시나리오를 실행한다.

#### 산출물

- `scenario-report.json`
- 시나리오 로그

#### 완료 기준

- 코드가 실제 사용 흐름에서도 동작한다.

---

### Stage 7. 비기능 검증과 hardening

#### 목적

기능이 맞는 것과 운영 가능한 것은 다르다는 점을 자동화한다.

#### 개발자가 할 일

- 비기능 목표를 수치화한다.
- 허용 가능한 리스크와 불가 리스크를 구분한다.
- 프로젝트 유형에 맞는 검증 프로파일을 정한다.

#### AI가 할 일

- 실험안과 비교안을 만든다.
- 성능, 자원 사용량, 보안, 운영성 리포트를 요약한다.
- 회귀 원인을 추정하고 수정안을 제안한다.

#### 필요한 도구

- `nonfunctional-runner`
- `scenario-runner`

#### 점검 항목 예시

- 성능: latency, throughput, build time, batch duration
- 자원 사용: memory, CPU, network, disk
- 보안: secret 노출, unsafe logging, dependency risk
- 운영성: startup/shutdown, health check, rollback, config validation
- 호환성: public API, schema, migration, 브라우저/OS/런타임 범위

#### 절차

1. `nonfunctional-runner`가 profile 기반 검증을 실행한다.
2. AI가 결과를 비교 요약한다.
3. 기준 미달 항목은 새 task로 환원한다.
4. 수정 후 기능 회귀가 없는지 다시 검증한다.

#### 산출물

- `nonfunctional-report.json`
- `tuning-notes.md`

#### 완료 기준

- 비기능 목표가 수치나 규칙으로 충족된다.

---

### Stage 8. 릴리스 게이트

#### 목적

개발 완료와 릴리스 가능을 분리한다.

#### 개발자가 할 일

- 최종 체크리스트를 승인한다.
- 차단 조건과 예외 승인 조건을 정의한다.
- 롤백 전략을 문서화한다.

#### AI가 할 일

- 보고서들을 수집해 릴리스 리포트를 만든다.
- 남은 리스크를 요약한다.
- 문서 누락과 운영 가이드 누락을 찾는다.

#### 필요한 도구

- `release-gate`
- `check-runner`
- `scenario-runner`
- `nonfunctional-runner`

#### 릴리스 게이트 최소 항목

- 필수 테스트 통과
- 대표 시나리오 통과
- 비기능 목표 충족
- 금지사항 위반 없음
- 민감정보 노출 없음
- 롤백 절차 존재
- 변경 요약과 리스크 문서 존재

#### 절차

1. `release-gate`가 모든 report와 diff를 수집한다.
2. 차단 항목을 명시적으로 판정한다.
3. 수정 가능한 항목은 다시 task로 생성한다.
4. 최종 승인 여부는 개발자가 결정한다.

#### 산출물

- `gate-report.json`
- `release-notes.md`
- `rollback-guide.md`

#### 완료 기준

- "작동한다"가 아니라 "릴리스해도 된다" 수준까지 검증된다.

---

### Stage 9. 운영 피드백 학습 루프

#### 목적

한 번 만든 성공/실패 패턴을 다음 사이클에 재사용한다.

#### 개발자가 할 일

- 실제 장애와 회귀를 기록한다.
- 자동화 규칙으로 승격할 리뷰 포인트를 고른다.
- 반복되는 실수를 공식 룰로 바꾼다.

#### AI가 할 일

- 실패 사례를 요약한다.
- 공통 원인을 분류한다.
- 다음 사이클에 자동 주입할 규칙 초안을 만든다.

#### 필요한 도구

- `knowledge-writer`
- `release-gate`
- `failure-bundler`

#### 축적해야 할 지식 종류

- 자주 깨지는 설계 규칙
- 자주 누락되는 테스트 유형
- 자주 발생하는 운영 사고 패턴
- 비기능 회귀 유발 패턴
- 프로젝트별 금지사항 위반 사례

#### 절차

1. 운영 이슈, 리뷰 이슈, 실패 보고서를 수집한다.
2. AI가 공통 패턴을 추출한다.
3. `knowledge-writer`가 이를 규칙과 패턴 문서로 저장한다.
4. 이후 `context-bundler`가 새 bundle을 만들 때 이 규칙을 자동 포함한다.

#### 산출물

- `patterns/*.md`
- `lessons/*.json`
- 차기 사이클용 rule set

#### 완료 기준

- 같은 실수를 반복할 확률이 줄어든다.

---

## 6. 프로젝트 유형별 추가 게이트

범용 워크플로는 같지만 프로젝트 유형마다 강조점은 다르다.

### 라이브러리 / SDK

- public API snapshot 유지
- 예제 코드 컴파일/실행
- semver 호환성 확인
- 문서와 실제 시그니처 일치 여부 확인

### 백엔드 서비스 / API 서버

- API contract test
- startup/shutdown smoke
- migration/rollback 안전성
- health check와 장애 복구 검증

### 배치 / 데이터 파이프라인

- 재실행 가능성
- 데이터 품질 기준
- partial failure 복구
- 자원 예산 준수

### CLI / 개발자 도구

- 주요 명령 시퀀스 검증
- 옵션 조합과 오류 메시지 확인
- 플랫폼별 동작 차이 점검
- backward compatible output 확인

### 프론트엔드 / UI

- 주요 사용자 플로우
- empty/loading/error state
- 접근성
- 시각 회귀

---

## 7. 실제 자동화 파이프라인 예시

아래는 위 단계를 스크립트로 연결한 예시다.

```text
1. profile-compiler docs/project docs/ops -> .ai/project-profile.json
2. spec-compiler issues/current-cycle.md -> .ai/spec.json
3. repo-indexer src tests config -> .ai/repo-index.json
4. task-slicer .ai/project-profile.json .ai/spec.json .ai/repo-index.json -> .ai/tasks/
5. context-bundler .ai/tasks/TASK-042.json -> .ai/bundles/TASK-042.json
6. agent-runner .ai/bundles/TASK-042.json -> patch + result.json
7. check-runner --task TASK-042 -> check-report.json
8. if failed: failure-bundler -> failure-bundle.json
9. agent-runner failure-bundle.json -> patch
10. scenario-runner --profile core -> scenario-report.json
11. nonfunctional-runner --profile release -> nonfunctional-report.json
12. release-gate reports diff profile -> gate-report.json
13. knowledge-writer postmortem -> patterns/
```

---

## 8. 도입 순서

처음부터 모든 단계를 자동화할 필요는 없다.
실무적으로는 아래 순서가 가장 안전하다.

1. `profile-compiler`, `spec-compiler`, `repo-indexer`, `check-runner`를 먼저 만든다.
2. 그 다음 `task-slicer`, `context-bundler`, `agent-runner`를 붙인다.
3. 이후 `failure-bundler`, `scenario-runner`로 self-repair 루프를 만든다.
4. 마지막으로 `nonfunctional-runner`, `release-gate`, `knowledge-writer`를 붙인다.

---

## 9. 이 문서를 실제로 쓰는 방법

새 기능, 리팩터링, 마이그레이션, 안정화 작업을 시작할 때마다 아래 순서로 쓴다.

1. `Stage 0`에서 목표와 승인 기준을 고정한다.
2. `Stage 1`에서 저장소 문맥을 인덱싱한다.
3. `Stage 2`에서 작업을 원자화한다.
4. `Stage 3 -> Stage 5`로 에이전트 구현과 자동 수정 루프를 돌린다.
5. `Stage 6`에서 실제 사용 시나리오를 검증한다.
6. `Stage 7`에서 비기능 검증을 통과시킨다.
7. `Stage 8`에서 릴리스 가능 여부를 판정한다.
8. `Stage 9`에서 교훈을 규칙으로 축적한다.

이 구조가 자리 잡으면 개발자는 "모든 코드를 직접 쓰는 사람"에서 "문제를 구조화하고 승인하는 사람"으로 이동하고, AI agent 계층은 "가끔 도와주는 조수"가 아니라 "반복 구현과 검증을 담당하는 실행자"가 된다.
