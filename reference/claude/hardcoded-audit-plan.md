# Hardcoded Values Refactoring Plan

감사일: 2026-04-08
상태: 계획 수립 완료, 미구현

---

## Context

프로젝트 전반, 특히 UI 레이어(webui.py, web.py)에 매직 넘버와 하드코딩된 기본값이 산재.
운영자가 새 환경에 배포하거나 동작을 조정하려면 Python 코드를 직접 수정해야 하는 상황.
기존 YAML 설정 체계(settings.py)를 확장하여 런타임 동작에 영향을 주는 수치 상수를 설정으로 빼는 것이 목표.

> 원칙: "큰 리라이트 대신 기존 구조 위에 작은 모듈 추가" (CLAUDE.md)

---

## 추출 대상 (이번 작업 범위)

| 항목 | 위치 | 현재값 | 용도 |
|---|---|---|---|
| Monitor auto-refresh | webui.py:429 | 30s | 파이프라인 모니터 자동 갱신 |
| Analytics auto-refresh | webui.py:812 | 60s | 대시보드 자동 갱신 |
| Exports active/idle refresh | webui.py:887 | 10s/30s | Export 페이지 자동 갱신 |
| Recent runs grid limit | web.py:96 | 25 | 파이프라인별 최근 실행 수 |
| Detail preview page size | web.py:210 | 8 | 드릴다운 미리보기 행 수 |
| Analytics export jobs limit | web.py:219 | 8 | 대시보드 내 최근 export 건수 |
| Export jobs list limit | web.py:363 | 50 | Export 목록 페이지 크기 |
| Error message truncation | webui.py:110 | 120자 | 에러 메시지 최대 표시 길이 |
| Default dataset | web.py:156,266 | "mes_ops" | Analytics 기본 데이터셋 |
| Default dashboard ID | web.py:157,267 | "operations_overview" | Analytics 기본 대시보드 |

## 추출하지 않는 항목 (사유)

| 항목 | 사유 |
|---|---|
| URL 경로 (/monitor, /api/v1/...) | FastAPI 라우터 정의와 1:1 결합; 분리 시 불일치 위험만 증가 |
| UI 텍스트 80+ (영문 라벨, 한글 메시지) | 사내망 관리자 콘솔, i18n은 시기상조 |
| CSS (_CSS 변수) | 이미 CSS custom property 사용 중, 별도 설정 불필요 |
| export/service.py max_workers, rows_per_batch | 이미 생성자 파라미터화 가능, 별도 PR 범위 |
| scheduler misfire_grace_time | SchedulerConfig 별도 설계 필요, 별도 PR |
| app.py title/version | 거의 변경 안 됨, 별도 사소한 변경 |

---

## 구현 단계

### Step 1: WebUIConfig dataclass 추가 — settings.py

```python
@dataclass
class WebUIConfig:
    monitor_refresh_seconds: int = 30
    analytics_refresh_seconds: int = 60
    exports_active_refresh_seconds: int = 10
    exports_idle_refresh_seconds: int = 30
    recent_runs_limit: int = 25
    detail_preview_page_size: int = 8
    analytics_export_jobs_limit: int = 8
    export_jobs_page_limit: int = 50
    error_message_max_length: int = 120
    default_dataset: str = "mes_ops"
    default_dashboard_id: str = "operations_overview"
```

- Settings.__init__에 webui 파라미터 추가 (기본값 WebUIConfig())
- Settings.load()에서 data.get("webui", {}) 파싱 (ExportConfig과 동일 패턴)
- 모든 기본값이 현재 하드코딩 값과 동일 → 동작 변화 없음

### Step 2: web.py 라우트 핸들러에서 설정 사용

- get_monitor_page: limit=25 → settings.webui.recent_runs_limit
- get_analytics_monitor_page:
  - Query(default="mes_ops") → Query(default=None), 함수 내에서 dataset = dataset or settings.webui.default_dataset
  - page_size=8 → settings.webui.detail_preview_page_size
  - limit=8 → settings.webui.analytics_export_jobs_limit
- create_analytics_export_from_monitor: 폼 기본값을 설정에서 읽기
- get_export_monitor_page: limit=50 → settings.webui.export_jobs_page_limit
- 각 render 함수 호출 시 webui_config=vars(settings.webui) dict 전달

**Query default 처리 방식:**

```python
@router.get("/monitor/analytics", response_class=HTMLResponse)
def get_analytics_monitor_page(
    request: Request,
    dataset: str | None = Query(default=None),
    dashboard_id: str | None = Query(default=None),
):
    settings = request.app.state.settings
    dataset = dataset or settings.webui.default_dataset
    dashboard_id = dashboard_id or settings.webui.default_dashboard_id
```

web router는 include_in_schema=False (web.py line 29)이므로 OpenAPI에 영향 없음.

### Step 3: webui.py render 함수에서 설정 소비

- 각 render 함수에 webui_config: dict | None = None 파라미터 추가
- 함수 내부에서 cfg = webui_config or {}; refresh = cfg.get("monitor_refresh_seconds", 30) 형태로 fallback 유지
- _first_failed_step_error에 max_length 파라미터 추가 (기본값 120)
- 한글 자동 갱신 문구를 설정값 기반으로 동적 생성: f'{refresh}초마다 자동 갱신'
- auto_refresh_seconds 값을 설정에서 읽기

**하위 호환:** webui_config 없이 호출해도 기존 기본값으로 동작

### Step 4: 샘플 설정 문서화

config/pipelines.sample.yaml에 주석 처리된 webui: 섹션 추가:

```yaml
# Web UI tuning (all optional — sensible defaults apply)
# webui:
#   monitor_refresh_seconds: 30
#   analytics_refresh_seconds: 60
#   exports_active_refresh_seconds: 10
#   exports_idle_refresh_seconds: 30
#   recent_runs_limit: 25
#   detail_preview_page_size: 8
#   analytics_export_jobs_limit: 8
#   export_jobs_page_limit: 50
#   error_message_max_length: 120
#   default_dataset: "mes_ops"
#   default_dashboard_id: "operations_overview"
```

실제 pipelines.yaml은 수정하지 않음 (dataclass 기본값으로 충분).

### Step 5: 테스트 추가

tests/test_settings.py에 추가:
1. webui: 섹션 있는 YAML 파싱 → 값 정확히 로딩 확인
2. webui: 섹션 없는 YAML → 기본값 확인

tests/test_webui_config.py (신규):
1. render_monitor_page(rows) — webui_config 없이 호출 시 기본값(30초) 동작 확인
2. render_monitor_page(rows, webui_config={"monitor_refresh_seconds": 15}) — HTML에 content="15" 포함 확인

---

## 수정 대상 파일

| 파일 | 변경 내용 |
|---|---|
| src/airflow_lite/config/settings.py | WebUIConfig 추가, Settings 확장 |
| src/airflow_lite/api/routes/web.py | 하드코딩 → settings.webui 참조 |
| src/airflow_lite/api/webui.py | render 함수에 webui_config 파라미터 추가, 매직넘버 제거 |
| tests/test_settings.py | WebUIConfig 파싱 테스트 추가 |
| tests/test_webui_config.py | render 함수 설정 반영 테스트 (신규) |

---

## 리스크 및 완화

| 리스크 | 완화 방안 |
|---|---|
| render 함수 호출 깨짐 | 모든 새 파라미터 default=None, 내부 fallback dict |
| YAML 파싱 회귀 | ExportConfig/MartConfig과 동일 패턴, 기존 테스트 커버리지 |
| Query default 동작 변경 | include_in_schema=False 라우터, 외부 소비자 없음 |
| 한글 안내 문구/실제 값 불일치 | 동일 설정값에서 동적 생성 |

---

## 검증 방법

1. pytest tests/test_settings.py — 설정 로딩 테스트 통과
2. pytest tests/test_webui_config.py — render 함수 테스트 통과
3. pytest tests/ — 전체 테스트 회귀 없음
4. 서버 기동 후 /monitor, /monitor/analytics, /monitor/exports 접속하여 동일 동작 확인
5. pipelines.yaml에 webui: 섹션 추가 후 값 변경이 실제 반영되는지 확인
