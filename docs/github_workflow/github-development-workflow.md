# GitHub 기반 개발 워크플로우

## 전체 흐름

```
Issue 등록 → Branch 생성 → 개발 → PR 생성 → Code Review → CI 테스트 → Merge
```

## 각 단계 상세

### 1. Issue 등록

- 버그, 기능 요청, 개선사항을 GitHub Issue로 등록
- 담당자(Assignee) 지정, 라벨(Label) 부여
- 마일스톤이나 프로젝트 보드에 연결하여 진행 상황 추적

### 2. Branch 생성

- Issue 번호를 기반으로 브랜치 생성
- 예: `feature/#42-add-login`, `fix/#58-null-pointer`
- main(또는 develop) 브랜치에서 분기

### 3. 개발

- 해당 브랜치에서 코드 작성 및 커밋
- 커밋 메시지에 Issue 번호 포함 권장 (예: `#42 로그인 기능 추가`)
- 작은 단위로 자주 커밋

### 4. Pull Request 생성

- main/develop 브랜치로 PR 생성
- PR 본문에 Issue 번호 연결 (`Closes #42`, `Fixes #58`)
- 변경 사항 요약, 테스트 방법 기술

### 5. Code Review

- 팀원이 코드를 리뷰
- 수정 요청(Request Changes) → 반영 → 재리뷰 반복
- 최소 1명 이상의 승인(Approve)을 받으면 다음 단계로 진행

### 6. CI 테스트

- GitHub Actions 등 CI 도구로 자동 테스트, 린트, 빌드 검증
- 테스트 실패 시 PR에 자동으로 실패 표시
- 모든 체크가 통과해야 merge 가능 (Branch Protection Rule 설정 시)

### 7. Merge

- 리뷰 승인 + 테스트 통과 시 merge
- 연결된 Issue가 자동으로 close (`Closes #42` 키워드 사용 시)
- merge 후 feature 브랜치 삭제

## 주요 워크플로우 비교

| 워크플로우 | 특징 | 적합한 팀 |
|---|---|---|
| **GitHub Flow** | main + feature 브랜치. 가장 단순 | 지속 배포하는 팀 |
| **Git Flow** | develop, release, hotfix 브랜치 추가 | 릴리즈 주기가 긴 프로젝트 |
| **Trunk-Based** | 매우 짧은 브랜치, 빠른 merge | CI/CD가 강한 대규모 팀 |

## 소규모 팀 / 1인 개발 시 팁

- 1인 개발이라도 Issue → Branch → PR 흐름을 따르면 이력 추적에 큰 도움
- Code Review는 생략하거나 셀프 리뷰, 또는 AI 도구로 대체 가능
- CI 테스트는 팀 규모와 무관하게 설정해두는 것을 권장

## Branch Protection 권장 설정

- `Require pull request reviews before merging` — 최소 1명 승인 필수
- `Require status checks to pass before merging` — CI 통과 필수
- `Require branches to be up to date before merging` — 최신 base 반영 필수
- `Do not allow bypassing the above settings` — 관리자도 예외 없음

## 이 저장소의 PR 자동화

- GitHub Actions workflow `PR Checks`가 PR마다 `smoke`, `unit-core` 체크를 고정 이름으로 실행한다.
- `smoke`는 `python -m compileall src/airflow_lite`로 문법과 기본 import 오류를 빠르게 잡는다.
- `unit-core`는 non-integration 테스트 묶음을 실행해 PR review 전 품질 기준을 확인한다.
- 같은 workflow의 `draft-pr-ready-gate` job이 두 체크 성공 뒤에 드래프트 PR 승격 여부를 판단한다.
- 자동 승격 조건은 `draft` 상태, `ready:auto` 라벨 존재, `blocked`와 `wip` 라벨 부재다.
- `ready:auto` 라벨을 나중에 붙여도 workflow가 다시 실행되도록 `labeled`와 `unlabeled` PR 이벤트를 포함한다.
- 이 자동화는 `ready for review`를 merge 승인 대체로 보지 않는다. 리뷰 가능한 품질 확인까지만 담당한다.
