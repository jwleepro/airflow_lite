# GitHub AI 자동화 플레이북

업데이트: `2026-04-04`

## 문서 목적

이 문서는 GitHub 자동화 구상을 단계별로 정리하는 작업 문서다. 핵심은 전체 목표 흐름에서 무엇이 이미 확정되었고, 무엇이 아직 정해지지 않았는지 분리해서 기록하는 것이다.

전체 목표 흐름:

`이슈 -> 프로젝트 -> 브랜치 작업 -> 풀 리퀘스트 -> 리뷰/체크 -> 병합 -> 릴리스`

## 단계별 상태

| 단계 | 상태 | 현재 기준 |
| --- | --- | --- |
| 이슈 | 확정 및 구현 | 구조화된 이슈 폼, 라벨 정책, 이슈 triage 자동화 |
| 프로젝트 | 미정 | 필요성만 확인됨 |
| 브랜치 작업 | 미정 | 기준 없음 |
| 풀 리퀘스트 | 미정 | 기준 없음 |
| 리뷰/체크 | 미정 | 기준 없음 |
| 병합 | 미정 | 기준 없음 |
| 릴리스 | 미정 | 기준 없음 |

현재 저장소에서 확정된 범위는 `이슈` 단계까지다. 프로젝트 이후 단계는 모두 다음 결정 항목으로 남겨 둔다.

## 현재 확정된 기준

### 구조화된 이슈 접수

현재 저장소에서 사용하는 이슈 폼 파일:

- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/ISSUE_TEMPLATE/01-bug.yml`
- `.github/ISSUE_TEMPLATE/02-feature.yml`
- `.github/ISSUE_TEMPLATE/03-task-request.yml`

구조화된 이슈 접수의 현재 원칙:

- 사용자는 구조화된 폼으로만 이슈를 등록한다.
- 사용자가 `status:*`, `needs-human`, `safe-automerge` 같은 운영 라벨을 직접 선택하지 않는다.
- `area:*`, 요청 유형, 긴급도는 폼 입력으로 받고 후속 triage 자동화가 라벨로 정규화한다.
- `needs-human`은 자유서술 추론이 아니라 명시적 위험 신호 체크 항목으로만 판단한다.
- 폼 기본 라벨은 현재 정책상 확정적인 값만 둔다.

### 현재 확정된 라벨 정책

#### 라벨 체계

기본 GitHub 라벨:

- `bug`
- `documentation`
- `duplicate`
- `enhancement`
- `good first issue`
- `help wanted`
- `invalid`
- `question`
- `wontfix`

Type:

- `type:feature`
- `type:refactor`
- `type:test`
- `type:chore`

Status:

- `status:needs-triage`
- `status:in-progress`
- `status:blocked`
- `status:ready-for-review`

Priority:

- `priority:high`
- `priority:medium`
- `priority:low`

Area:

- `area:backend`
- `area:frontend`
- `area:infra`
- `area:ci`
- `area:docs`

AI / Automation:

- `ai:impl:codex`
- `ai:impl:claude`
- `ai:impl:gemini`
- `ai:review:all`
- `needs-human`
- `safe-automerge`

#### 라벨 운영 규칙

- 이슈마다 `type:*`, `status:*`, `priority:*` 라벨은 각각 정확히 하나만 유지한다.
- `area:*` 라벨은 하나 이상 허용한다.
- `ai:*` 라벨은 해당 이슈나 PR이 AI 자동화 흐름에 포함될 때만 사용한다.
- 새 이슈의 기본값은 `status:needs-triage`, `priority:medium`으로 둔다.
- 상태는 가능하면 이슈에 저장한다.
- PR 단계 기준은 아직 확정하지 않았지만, 라벨 상속을 검토할 경우 `area:*`, `ai:*`, `needs-human`, `safe-automerge`를 우선 후보로 본다.

### 현재 확정된 이슈 자동화 기준

현재 구현 파일:

- `.github/scripts/issue_triage.py`
- `.github/workflows/issue-triage.yml`

현재 구현된 자동화 범위:

- `issues.opened`
- `issues.edited`

현재 구현된 자동화 규칙:

- `status:needs-triage`가 없으면 추가한다.
- 우선순위 라벨이 없으면 `priority:medium`을 추가한다.
- 이슈 폼 답변을 읽어 `type:*`, `area:*`, 우선순위 라벨을 정규화한다.
- 이슈 폼의 사람 검토 필요 신호가 하나라도 선택되면 `needs-human`을 추가한다.

현재 구현되지 않은 것:

- `safe-automerge` 자동 부여
- GitHub Projects 자동 등록

## 다음 단계에서 정해야 할 정보

### 프로젝트

정해야 할 것:

- GitHub Projects를 실제 사용할지
- 단일 프로젝트인지, 여러 프로젝트인지
- 이슈 생성 시 자동 등록할지
- 어떤 필드를 자동으로 채울지

후보 파일:

- `.github/workflows/project-sync.yml`

### 브랜치 작업

정해야 할 것:

- 이슈에서 브랜치를 어떤 규칙으로 만들지
- 브랜치 이름에 이슈 번호를 강제할지
- AI 구현을 어떤 조건에서 시작할지
- 브랜치 생성과 초안 PR 생성을 한 흐름으로 묶을지

### 풀 리퀘스트

정해야 할 것:

- PR 템플릿 본문 구조
- 연결 이슈를 어떤 문법으로 강제할지
- 이슈 라벨을 PR에 어디까지 상속할지
- 경로 기반 `area:*` 라벨링을 어느 시점에 할지

후보 파일:

- `.github/pull_request_template.md`
- `.github/labeler.yml`
- `.github/workflows/pr-labeler.yml`
- `.github/workflows/pr-policy.yml`

### 리뷰/체크

정해야 할 것:

- 실제 필수 CI 체크 목록
- AI 리뷰를 체크 런으로 둘지, 코멘트만 둘지
- `ai/codex-review`, `ai/claude-review`, `ai/gemini-review`를 실제 필수 게이트로 올릴지
- CODEOWNERS와 ruleset을 어떻게 결합할지

후보 파일:

- `.github/workflows/ai-review-dispatch.yml`

### 병합

정해야 할 것:

- `safe-automerge`를 어떤 조건에서 붙일지
- `needs-human`을 어떤 조건에서 강제할지
- 자동 병합 허용 범위를 어디까지 둘지
- 보호 경로를 어느 수준까지 둘지
- merge queue가 필요한지

후보 파일:

- `.github/workflows/automerge-gate.yml`

### 릴리스

정해야 할 것:

- 태그 전략
- changelog 생성 방식
- 릴리스 노트 자동화 여부
- 배포 또는 배포 후 검증 연결 여부

## 메모

- 이 문서는 현재 저장소 구현 상태를 기준으로 다시 정리한 버전이다.
- 기존 브레인스토밍 메모 중 현재 확정 기준과 충돌하는 서술은 남기지 않았다.
- 후속 단계는 실제 파일을 만들기 전에 이 문서에서 먼저 기준을 확정한다.
