# airflow_lite WebUI 구조 분석 (SOLID / DRY)

## Context

사용자는 기능은 완성된 airflow_lite 프로젝트의 WebUI를 교체하려 함. 실제 리스킨 작업에 착수하기 전에, 현재 UI 레이어가 비즈니스 로직과 충분히 분리되어 있어 "UI만" 안전하게 바꿀 수 있는 구조인지 SOLID/DRY 관점에서 진단이 필요함.

## 현재 구조 요약

```
FastAPI app
├─ routes/pipelines.py, analytics.py, admin.py, backfill.py, health.py  ← JSON API (/api/v1/*)
├─ routes/web.py (651줄)                                                  ← HTML 라우트 (/monitor/*)
├─ webui_helpers.py (≈5000줄 CSS/SVG/위젯 포함)                           ← 공통 렌더 유틸
├─ webui_monitor.py / webui_analytics.py / webui_exports.py
├─ webui_admin.py (361줄)                                                 ← 설정 모델 직접 참조
└─ webui_run_detail.py
service 계층: query/service.py, export/service.py, engine/backfill.py
```

HTML은 Jinja 템플릿이 아니라 **Python 문자열 조립**으로 생성. CSS/아이콘은 `webui_helpers.py`에 문자열 상수로 내장.

## SOLID / DRY 진단

### 잘 지켜진 부분

- **ISP / 경로 분리**: JSON API(`/api/v1/*`)와 HTML(`/monitor/*`)이 라우터 레벨에서 완전히 분리. `include_in_schema=False`로 OpenAPI에도 노출되지 않음 → UI만 교체 시 JSON API는 무영향.
- **SRP (부분)**: `query/service.py`, `export/service.py`, `engine/backfill.py` 등 도메인 서비스가 분리돼 있어 핵심 비즈니스 로직은 라우터 바깥에 존재.
- **약결합 렌더러**: `webui_monitor.py`, `webui_analytics.py`는 dict 기반 입력만 받아 HTML 반환 → 이 파일들은 UI 교체 시 전면 재작성 대상이지만, 외부 의존성이 좁다.
- **최근 리스킨 커밋(638e3ae)의 범위**: `webui_helpers.py` 위주로만 +552/-128, 라우터/서비스 무영향 → 테마 수준 변경은 이미 "안전하게" 가능함이 증명됨.

### 위반/냄새

1. **SRP 위반 — `routes/web.py`가 너무 많은 역할을 겸함**
   - 폼 파싱(`_read_form_values`, `_first_value`), 쿼리 조립(`_build_dashboard_data`), 리다이렉트, HTML 렌더 호출, 다음 실행시각 계산(`_calc_next_run`)까지 한 파일에 공존.
   - 비즈니스 로직이 라우터 핸들러 몸통에 녹아있어, UI 레이어를 바꾸면 이 로직을 새 라우터로 복사해야 함(=DRY 위반의 씨앗).

2. **DIP 위반 — `webui_admin.py`가 설정/ORM 모델에 직접 의존**
   - `web.py`에서 `from airflow_lite.storage.models import ConnectionModel, PipelineModel, VariableModel, PoolModel` 을 import하고, `webui_admin.py`는 `connection.conn_id`, `pool.pool_name` 같은 속성명을 하드코딩.
   - UI 측이 스토리지 모델에 직접 결합 → UI 교체 시 모델 스키마까지 알아야 함. "프리젠테이션 DTO"가 없음.

3. **OCP 취약 — 템플릿 엔진 미사용**
   - HTML이 Python f-string으로 조립되어, 디자이너/프론트엔드 도구(HMR, 컴포넌트 라이브러리, Tailwind 빌드 등)를 끼울 수 없음.
   - 새로운 UI 프레임워크(예: Jinja2 템플릿, HTMX, 혹은 별도 SPA) 도입 시 **렌더 함수 전체 재작성 + 라우터 내 데이터 조립 코드 추출**이 동시에 필요.

4. **DRY 위반 — CSS/아이콘/레이아웃이 한 파일에 덩어리로 존재**
   - `webui_helpers.py` 5000+줄에 CSS, SVG, 내비게이션, 카드/테이블 위젯이 섞여 있음.
   - 개별 페이지 렌더러가 같은 HTML 스캐폴딩(head, nav, footer)을 각자 호출 → 공통 레이아웃 추출은 되어있지만, 테마 토큰(색/간격/폰트)은 문자열 하드코딩.

5. **프리젠테이션 DTO 부재**
   - `_build_dashboard_data()` 같은 함수가 `run_repo.find_by_pipeline(...)` 결과를 곧바로 UI용 dict로 말아넣음.
   - "조회 서비스 → ViewModel → 렌더러" 계층이 없어, UI 교체 시 조회+변환 로직까지 끌고 가야 함.

## UI 교체 난이도 평가

| 교체 시나리오 | 난이도 | 이유 |
|---|---|---|
| CSS/색상/아이콘 리스킨 (현 커밋 수준) | **낮음** | `webui_helpers.py`만 수정. 이미 검증됨. |
| 레이아웃/컴포넌트 구조 변경 | **중간** | 각 `webui_*.py` 렌더러 재작성. 라우터는 대체로 유지. |
| 템플릿 엔진(Jinja2) 전환 | **중상** | 렌더러 전부 재작성 + 라우터의 데이터 조립 로직을 서비스로 밀어내야 DRY 유지 가능. |
| SPA(React/Vue) 전환 | **상** | HTML 라우트 폐기 + JSON API 확장 필요. `web.py` 내 비즈니스 로직을 서비스 계층으로 이동해야 하고, admin 폼도 JSON API로 재노출 필요. |

## 권장 리팩터링 (UI 교체 전 선행)

1. **ViewModel 레이어 신설** — `src/airflow_lite/api/viewmodels/`
   라우터에서 수집·변환한 dict를 Pydantic/dataclass로 표준화. 렌더러는 ViewModel만 받도록 시그니처 고정.
   *효과*: DIP 확보, 어떤 UI 프레임워크든 ViewModel만 소비하면 됨.

2. **`web.py`에서 데이터 조립 함수 추출**
   `_build_dashboard_data`, admin 폼 처리 로직 등을 `service/webui_presenter.py`(또는 기존 `query.service`/`admin` 서비스)로 이동. 라우터는 "요청 → 서비스 호출 → ViewModel → 렌더러" 4줄 수준으로 축소.

3. **Jinja2 템플릿 엔진 도입 검토**
   폐쇄망·Windows 제약 무영향(순수 Python 패키지). `templates/` 디렉터리로 HTML을 옮기면 디자이너 협업·HMR·테마 토큰 관리 용이. `webui_helpers.py`의 CSS는 `static/css/`로 분리.

4. **테마 토큰 파일 분리**
   색/간격/폰트를 CSS 변수(`:root { --color-primary: ... }`)로 모아 한 파일(예: `static/css/tokens.css`)에서 관리 → 향후 리스킨은 토큰 교체만으로 가능.

5. **admin 렌더러의 모델 의존성 제거**
   `webui_admin.py`가 `ConnectionModel` 등을 직접 import하지 않도록, 라우터에서 `ConnectionVM(conn_id=..., host=..., ...)` 형태로 미리 변환.

## 결론 (한 줄)

> **JSON API와 HTML 경로는 잘 분리돼 있지만, HTML 라우트 내부(특히 `web.py`, `webui_admin.py`)에는 비즈니스 로직·모델 의존성이 섞여 있어, "테마 리스킨"은 쉬우나 "UI 프레임워크 교체"는 ViewModel 레이어와 템플릿 엔진 도입이 선행되지 않으면 DRY/DIP를 크게 해친다.**

## 검증 방법 (리팩터링 시)

- 기존 pytest(`tests/`) 통과 유지
- `/monitor/*` 페이지 수동 접속 후 시각 diff 없음 확인
- `/api/v1/*` JSON 응답 스냅샷 변화 없음 확인
- admin 폼(Connection/Variable/Pool/Pipeline CRUD) 동작 확인
