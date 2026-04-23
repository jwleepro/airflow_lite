# Jira 초기 구성 가이드

> 신성이넥스 SF팀 Jira 설정 기록 (2026-03-23 기준)
> 사이트: https://shinsung-innex-sf.atlassian.net

---

## 1. 현재 구성 현황

### 프로젝트 목록

| 프로젝트 이름 | 키 | 관리 방식 | 보드 | 용도 |
|---|---|---|---|---|
| Airflow Lite | `AFL` | 팀이 관리 | 칸반 | airflow-lite 제품 개발 전용 |
| Team Operations | `TO` | 팀이 관리 | 칸반 | 팀 운영/유지보수/인프라 |
| IT 통합 개발 | `DEV` | 회사가 관리 | 클래식 | (기존 유지) |
| shinsung-innex-sf | `SIS` | 회사가 관리 | 클래식 | (기존 유지) |

### 칸반 보드 컬럼 구조 (AL, TO 공통)

```
해야 할 일  →  진행 중  →  코드리뷰  →  완료
```

---

## 2. 에픽 구조

### Airflow Lite (AL) 에픽

| 이슈 키 | 에픽 이름 | 설명 |
|---|---|---|
| AL-1 | 코어 엔진 | DAG 파싱, 스케줄링, 태스크 실행 엔진 |
| AL-2 | 모니터링/로깅 | 로깅 시스템, 실행 이력 추적, 알림 |
| AL-3 | 테스트/품질 | 통합 테스트, CI/CD, 코드 품질 |
| AL-4 | 문서화 | 기술 문서, API 문서, 사용 가이드 |

### Team Operations (TO) 에픽

| 이슈 키 | 에픽 이름 | 설명 |
|---|---|---|
| TO-1 | 인프라/환경 | 서버, DB, 개발 환경 관리 |
| TO-2 | 버그/장애 대응 | 운영 시스템 버그 수정, 장애 대응 |
| TO-3 | 요청/지원 | 사내 요청 사항 처리 |

---

## 3. 새 프로젝트 만드는 방법

1. https://shinsung-innex-sf.atlassian.net/jira/create-project 접속
2. **칸반** 템플릿 선택 → "템플릿 사용" 클릭
3. 이름 입력, 관리 방식 → **팀이 관리** 선택
4. "다음" → 팀 초대 단계는 "나중에" → "완료"
5. 생성 후 보드에서 컬럼 추가 (아래 참고)

> **팀이 관리** vs **회사가 관리**
> - 팀이 관리: 소규모 팀, 자유롭게 설정 변경 가능, 에픽/스토리/작업 지원
> - 회사가 관리: 조직 전체 표준 적용, 워크플로우 중앙 관리

---

## 4. 칸반 보드에 컬럼 추가하는 방법

1. 해당 프로젝트 보드 화면 접속
2. 보드 오른쪽 끝 **+** 버튼 클릭
3. 컬럼 이름 입력 후 Enter
4. 컬럼 헤더를 드래그해서 원하는 위치로 이동

> 현재 설정: 해야 할 일 → 진행 중 → **코드리뷰** → 완료

---

## 5. 이슈 유형 및 계층 구조

```
에픽 (Epic)          ← 큰 기능/목표 단위 (예: "코어 엔진")
  └── 스토리 (Story) ← 사용자 관점의 기능 요구사항
  └── 작업 (Task)    ← 구체적인 개발 작업
      └── 하위 작업  ← 작업을 더 잘게 쪼갤 때
  └── 버그 (Bug)     ← 결함/오류
```

### 이슈 생성 방법
- 보드에서 **+ 만들기** 버튼 클릭
- 또는 보드 컬럼 하단 **+ 만들기** 클릭 (해당 상태로 바로 생성)

### 에픽에 이슈 연결하는 방법
이슈 생성 시 또는 이슈 상세 화면에서:
- **"상위 항목"** 필드에 에픽 키 입력 (예: `AL-1`)

---

## 6. 우선순위 기준

| 우선순위 | 의미 | 예시 |
|---|---|---|
| **Highest** | 즉시 대응 필요 | 운영 장애, 긴급 버그 |
| **High** | 이번 주 내 처리 | 중요 기능 버그 |
| **Medium** | 일반 업무 (기본값) | 신규 기능 개발 |
| **Low** | 여유 시 처리 | 개선 사항, 문서 보완 |

---

## 7. 팀원 초대 방법

1. 프로젝트 보드 접속
2. 상단 프로젝트 이름 옆 **팀원 아이콘** 클릭 또는 프로젝트 설정 → 팀원
3. 이메일 입력 → 역할 선택 (관리자 / 멤버)
4. 초대 전송

---

## 8. 이슈 상태 변경 방법

**방법 1 (보드에서):** 이슈 카드를 원하는 컬럼으로 드래그

**방법 2 (이슈 상세에서):** 이슈 클릭 → 상단 상태 버튼 클릭 → 다음 상태 선택

---

## 9. 자주 쓰는 JQL 검색 쿼리

Jira 상단 검색창 → "고급 검색" 에서 사용

```
# AL 프로젝트 진행 중인 이슈
project = AL AND status = "진행 중"

# 내가 담당한 이슈 전체
assignee = currentUser()

# 이번 주 완료된 이슈
project in (AL, TO) AND status = 완료 AND updated >= -7d

# 버그만 보기
project = AL AND issuetype = 버그

# 에픽별 이슈 보기
project = AL AND "Epic Link" = AL-1
```

---

## 10. 앞으로 해야 할 설정

- [ ] 이슈에 담당자 배정
- [x] GitHub 코드 저장소 연결 완료 (2026-03-23) → 아래 11번 참고
- [ ] 알림 설정 (이슈 상태 변경 시 이메일/Slack 알림)

---

## 11. GitHub 연결 (완료)

> 2026-03-23 완료

### 설치된 앱

- **GitHub for Atlassian** (Atlassian 공식, 무료)
- 설치 경로: AL 프로젝트 설정 → 도구 체인 → 소스 코드 관리 → GitHub for Atlassian 설치

### 연결 정보

| 항목 | 내용 |
|------|------|
| GitHub 계정 | jwleepro (github.com/jwleepro) |
| 연결 저장소 | jwleepro/airflow_lite |
| 접근 방식 | Only select repositories (특정 저장소만) |
| Rovo Search 연동 | 활성화 (GitHub 데이터를 Atlassian AI 검색에서 조회 가능) |

### 연결 방법 (재설정 시 참고)

1. AL 프로젝트 설정 → **도구 체인** 접속
2. **소스 코드 관리** 섹션 → **GitHub for Atlassian 설치** 클릭
3. 사이트 선택 (`shinsung-innex-sf`) → **Review** → **Get it now**
4. **앱 구성** 클릭 → **Continue** → **GitHub Cloud** 선택 → **Next**
5. GitHub OAuth 승인 ("Authorize Atlassian" 클릭)
6. Rovo Search 활성화 → **Next**
7. GitHub App 설정 페이지에서 연결할 저장소 선택

### GitHub ↔ Jira 연동 사용법

커밋 메시지에 Jira 이슈 키를 포함하면 해당 이슈에 자동 연결됨:

```bash
# 커밋 예시
git commit -m "AL-5: DAG 파서 구현"
git commit -m "AL-3: 통합 테스트 추가 [AL-3]"
```

브랜치 이름에도 이슈 키 포함 가능:

```bash
git checkout -b AL-5/dag-parser
```

연결되면 Jira 이슈 상세 화면 → **개발** 섹션에서 커밋/브랜치/PR 확인 가능.

---

## 참고

- Jira 사이트: https://shinsung-innex-sf.atlassian.net
- AL 보드: https://shinsung-innex-sf.atlassian.net/jira/software/projects/AL/boards/37
- TO 보드: https://shinsung-innex-sf.atlassian.net/jira/software/projects/TO/boards/38
- GitHub 저장소: https://github.com/jwleepro/airflow_lite
- Jira 공식 문서: https://support.atlassian.com/jira-software-cloud/
