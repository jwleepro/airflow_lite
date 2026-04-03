# GitHub AI 자동화 플레이북

업데이트: `2026-04-03`

## 범위

이 문서는 현재 조사 결과를 다음 범위로 요약한다.

- 일반적인 개발 흐름에서 자주 쓰이는 GitHub 기능
- 이슈에서 병합까지 이어지는 실무형 자동화 패턴
- Codex, Claude Code, Gemini를 활용한 AI 보조 구현 및 리뷰 방식
- 저장소 자동화를 위한 초기 라벨 체계

이 문서는 의도적으로 GitHub 중심으로 작성했다. 먼저 GitHub 네이티브 워크플로 제어 수단에 집중하고, 그 다음 외부 AI 에이전트를 어디에 배치할지 설명한다.

## 일반적인 GitHub 개발 흐름

가장 흔한 GitHub 중심 전달 흐름은 다음과 같다.

`이슈 -> 프로젝트 -> 브랜치 작업 -> 풀 리퀘스트 -> 리뷰/체크 -> 병합 -> 릴리스`

이 흐름에서 가장 자주 쓰이는 GitHub 기능은 다음과 같다.

- `Issues`: 버그 리포트, 기능 요청, 잡무를 시작하는 기본 지점
- `Projects`: 우선순위와 상태 추적을 위한 보드 또는 테이블 뷰
- `Pull Requests`: 코드 리뷰, 토론, 승인, 병합이 이루어지는 표면
- `Actions`: CI, 정책 검사, 라벨링, 배포, 워크플로 자동화
- `CODEOWNERS`: 경로 기준 기본 리뷰어 지정
- `Rulesets` / 브랜치 보호: 필수 리뷰, 상태 체크, 병합 조건
- `Auto-merge`: 모든 필수 조건이 통과되면 자동 병합
- `Merge queue`: CI 경합이 중요한 경우 병합을 안전하게 직렬화
- `Security and quality`: Dependabot, 시크릿 스캐닝, 코드 스캐닝
- `Discussions` / `Wiki`: 필요 시 장문의 토론과 문서화

## 가장 흔한 자동화 패턴

현대적인 기본 패턴은 다음과 같다.

`GitHub 기본 제어 수단 + Actions + rulesets + 선택적 AI 에이전트`

실무에서는 보통 다음을 의미한다.

1. 구조화된 이슈 접수
2. 자동 분류와 라벨링
3. 표준 PR 생성과 연결된 이슈 종료
4. 자동화된 CI, 보안, 정책 검사
5. 리뷰어 할당
6. 필수 게이트 통과 후 조건부 자동 병합

모든 변경에 대해 완전한 "무인" 자동화를 적용하는 경우는 드물다. 일반적인 패턴은 다음과 같다.

- 반복적인 라우팅과 검사는 자동화한다
- AI가 코드 초안 작성이나 수정 제안을 맡는다
- 강한 병합 게이트는 GitHub 규칙에 남긴다
- 위험도가 높은 범위에만 사람 승인을 요구한다

## AI 보조 전달 모델

GitHub는 제어 평면으로 남아야 한다. Codex, Claude Code, Gemini는 외부 작업자이자 리뷰어로 동작한다.

권장 형태:

`GitHub Issue -> 오케스트레이터가 구현자 선택 -> 드래프트 PR -> AI 리뷰 -> GitHub 체크가 병합 결정`

### 이 구조가 잘 동작하는 이유

- GitHub가 작업 상태의 단일 진실 공급원으로 유지된다.
- AI 출력이 PR 코멘트와 체크 결과로 정규화된다.
- ruleset과 필수 체크가 병합 안전성을 계속 통제한다.
- 어떤 AI가 코드를 작성했는지와 무관하게 동일한 구현 경로를 재사용할 수 있다.

### 권장 역할 분리

기본값으로 구현자 1명과 리뷰어 2명을 둔다.

- `Claude Code`가 구현 -> `Codex`, `Gemini`가 리뷰
- `Codex`가 구현 -> `Claude Code`, `Gemini`가 리뷰
- `Gemini`가 구현 -> `Codex`, `Claude Code`가 리뷰

여러 AI가 같은 이슈를 두고 동시에 구현 경쟁을 하는 방식보다 이런 구성이 더 깔끔한 신호를 만든다.

### 리뷰 출력 모델

각 AI 리뷰어는 다음을 내보내야 한다.

- 사람이 읽을 수 있는 리뷰 코멘트
- 기계가 읽을 수 있는 체크 결과 1개

권장 체크 이름:

- `ai/codex-review`
- `ai/claude-review`
- `ai/gemini-review`

권장 결과 값:

- `pass`
- `soft-fail`
- `fail`

권장 게이트:

- 어떤 `fail`이든 병합을 막는다
- `soft-fail`이면 한 번 더 수정 루프를 돈다
- 반복적인 불일치나 루프 소진 시 `needs-human`을 추가한다

## 권장 자동화 경계

### 보통 안전하게 자동화할 수 있는 것

- 이슈 폼 접수
- 기본 라벨 적용과 프로젝트 등록
- 연결된 작업으로부터 PR 생성
- 경로 기반 영역 라벨 부여
- 리뷰어 할당
- CI, lint, 테스트, 빌드, 보안 스캔
- 연결된 이슈 강제 같은 정책 검사
- 저위험 변경에 대한 조건부 자동 병합

### 조건부로 자동화할 것

- 이슈 기반 AI 구현
- AI 리뷰와 수정 루프
- 작고 저위험인 범위에 한한 무인 병합

### 고위험 작업은 사람 승인을 유지할 것

- 인증 및 권한 부여 로직
- 과금 또는 되돌릴 수 없는 비즈니스 로직
- 인프라와 배포 제어
- 워크플로 보안과 토큰 처리
- 스키마 마이그레이션 또는 파괴적 데이터 변경

## 라벨 체계

GitHub 저장소 전반에서 가장 흔한 공통 라벨 구조는 다음 접두사 축을 중심으로 한 작은 집합이다.

- `type`
- `status`
- `priority`
- `area`

`bug`, `documentation`, `enhancement`, `question`, `good first issue`, `help wanted` 같은 GitHub 기본 라벨은 보통 대체하지 않고 유지한다.

이 저장소에서 합의한 v1 라벨 체계는 다음과 같다.

### 기본 GitHub 라벨

- `bug`
- `documentation`
- `duplicate`
- `enhancement`
- `good first issue`
- `help wanted`
- `invalid`
- `question`
- `wontfix`

### Type

- `type:feature`
- `type:refactor`
- `type:test`
- `type:chore`

### Status

- `status:needs-triage`
- `status:in-progress`
- `status:blocked`
- `status:ready-for-review`

### Priority

- `priority:high`
- `priority:medium`
- `priority:low`

### Area

- `area:backend`
- `area:frontend`
- `area:infra`
- `area:ci`
- `area:docs`

### AI / Automation

- `ai:impl:codex`
- `ai:impl:claude`
- `ai:impl:gemini`
- `ai:review:all`
- `needs-human`
- `safe-automerge`

## 라벨 운영 규칙

- 이슈마다 `type:*`, `status:*`, `priority:*` 라벨은 각각 정확히 하나만 유지한다.
- `area:*` 라벨은 하나 이상 허용한다.
- `ai:*` 라벨은 해당 이슈나 PR이 AI 자동화 흐름에 포함될 때만 사용한다.
- 새 이슈의 기본값은 `status:needs-triage`, `priority:medium`으로 둔다.
- 상태는 가능하면 이슈에 저장하고, PR은 주로 `area:*`, `ai:*`, `needs-human`, `safe-automerge`를 상속받게 한다.

## 권장 라벨 자동화 규칙

### 이슈 생성 시

`issues.opened`와 `issues.edited`에서:

- `status:needs-triage`가 없으면 추가한다
- 우선순위 라벨이 없으면 `priority:medium`을 추가한다
- 이슈 폼 답변을 `type:*`, `area:*`, 우선순위 라벨로 매핑한다
- 해당하면 접수 답변을 바탕으로 `needs-human` 또는 `safe-automerge`를 추가한다
- 이슈를 GitHub Projects에 등록한다

### PR 생성 시

`pull_request.opened`, `pull_request.edited`, `pull_request.ready_for_review`, `pull_request.synchronize`에서:

- `Closes #...` 또는 `Refs #...`를 통해 연결된 이슈를 요구한다
- 연결된 이슈에서 `ai:*`, `needs-human`, `safe-automerge`를 복사한다
- 변경된 파일 경로로부터 `area:*` 라벨을 도출한다
- PR이 리뷰 가능한 상태가 되면 AI 리뷰를 디스패치한다

### 자동 병합 가드레일

다음 조건이 모두 참일 때만 자동 병합을 허용한다.

- `safe-automerge`가 존재한다
- `needs-human`이 없다
- 필수 CI 체크가 통과한다
- 필수 AI 리뷰 체크가 통과한다
- 보호 대상 파일 경로가 변경되지 않았다

대표적인 보호 경로:

- `.github/workflows/**`
- `infra/**`
- `auth/**`
- `billing/**`
- `db/migrations/**`

보호 경로 아래의 변경은 자동으로 `needs-human`을 추가해야 한다.

## 권장 저장소 워크플로 파일

- `.github/ISSUE_TEMPLATE/feature.yml`
- `.github/ISSUE_TEMPLATE/bug.yml`
- `.github/pull_request_template.md`
- `.github/labeler.yml`
- `.github/workflows/issue-triage.yml`
- `.github/workflows/project-sync.yml`
- `.github/workflows/pr-labeler.yml`
- `.github/workflows/pr-policy.yml`
- `.github/workflows/ai-review-dispatch.yml`
- `.github/workflows/automerge-gate.yml`

## 출처

이 요약에 사용한 주요 출처:

- GitHub Issues 문서: <https://docs.github.com/issues>
- GitHub Projects 개요: <https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects>
- GitHub Actions 문서: <https://docs.github.com/en/actions>
- GitHub Actions 이벤트: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>
- GitHub 이슈/PR 템플릿: <https://docs.github.com/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates>
- GitHub 이슈 폼: <https://docs.github.com/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms>
- PR과 이슈 연결: <https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue>
- Pull request 리뷰: <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews>
- CODEOWNERS: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners>
- 팀 리뷰 할당: <https://docs.github.com/en/organizations/organizing-members-into-teams/managing-code-review-settings-for-your-team>
- Rulesets: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
- 보호 브랜치: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>
- 자동 병합: <https://docs.github.com/github/collaborating-with-issues-and-pull-requests/automatically-merging-a-pull-request>
- Merge queue: <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue>
- 코드 스캐닝: <https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning>
- Dependabot 알림: <https://docs.github.com/en/code-security/concepts/supply-chain-security/about-dependabot-alerts>
- 시크릿 스캐닝: <https://docs.github.com/en/code-security/concepts/secret-security/about-secret-scanning>
- 보안 개요: <https://docs.github.com/en/code-security/concepts/security-at-scale/about-security-overview>
- Webhooks: <https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks>
- GitHub Apps: <https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps>
- Actions에서 GitHub App 인증: <https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow>
- Copilot coding agent: <https://docs.github.com/copilot/concepts/agents/coding-agent/about-coding-agent>
- Copilot code review: <https://docs.github.com/copilot/concepts/code-review>

조사 중 함께 참고한 대표적인 공개 라벨 규칙:

- GitHub Docs 라벨 레퍼런스: <https://docs.github.com/en/contributing/collaborating-on-github-docs/label-reference>
- GitHub `actions/labeler`: <https://github.com/actions/labeler>
- Python 이슈 라벨: <https://devguide.python.org/triage/labels/>
- Amundsen 이슈 라벨링: <https://www.amundsen.io/amundsen/issue_labeling/>

## 메모

- 위 GitHub 기능 및 자동화 가이드는 `2026-04-03` 기준 공개 문서를 바탕으로 정리했다.
- Codex, Claude Code, Gemini의 정확한 무인 실행 경로는 대상 환경에서 제공되는 인증 방식과 비대화형 실행 옵션에 따라 달라진다. 이 문서에서는 그 권한 상태나 CLI/API 준비 여부를 별도로 검증하지 않았다.
