# Task-007: FastAPI REST API

## 목적

FastAPI 기반 REST API를 구현하여 수동 트리거, 백필 요청, 파이프라인 상태 조회 기능을 제공한다. 사내망 전용으로 CORS를 제한하고, 앱 팩토리 패턴으로 구성한다.

## 입력

- Task-003의 PipelineRunner (수동 트리거)
- Task-005의 BackfillManager (백필 요청)
- Task-002의 Repository (실행 이력 조회)
- Settings (API 설정)

## 출력

- `src/airflow_lite/api/app.py` — FastAPI 앱 팩토리
- `src/airflow_lite/api/routes/pipelines.py` — 파이프라인 엔드포인트
- `src/airflow_lite/api/routes/backfill.py` — 백필 엔드포인트
- `src/airflow_lite/api/schemas.py` — Pydantic 요청/응답 모델

## 구현 제약

- CORS: 사내망 IP 대역만 허용 (NFR-11)
- API prefix: `/api/v1`
- 내부망 제한: uvicorn 바인딩 또는 방화벽으로 외부 접근 차단

## 구현 상세

### app.py — 앱 팩토리 + CORS 미들웨어

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app(settings: "Settings") -> FastAPI:
    """FastAPI 앱 팩토리.

    설계 제약:
    - CORS: 사내망 IP 대역만 허용 [NFR-11]
    - API prefix: /api/v1
    """
    app = FastAPI(
        title="Airflow Lite API",
        version="1.0.0",
    )

    # CORS 미들웨어 설정 — 사내망 전용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.allowed_origins,  # 예: ["http://10.0.0.*"]
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    from airflow_lite.api.routes.pipelines import router as pipelines_router
    from airflow_lite.api.routes.backfill import router as backfill_router

    app.include_router(pipelines_router, prefix="/api/v1")
    app.include_router(backfill_router, prefix="/api/v1")

    return app
```

### 엔드포인트 정의

| Method | Path | 설명 | Request Body | Response |
|--------|------|------|--------------|----------|
| `POST` | `/api/v1/pipelines/{name}/trigger` | 수동 즉시 실행 | `TriggerRequest` | `PipelineRunResponse` |
| `POST` | `/api/v1/pipelines/{name}/backfill` | 백필 요청 | `BackfillRequest` | `list[PipelineRunResponse]` |
| `GET`  | `/api/v1/pipelines` | 파이프라인 목록 | - | `list[PipelineInfo]` |
| `GET`  | `/api/v1/pipelines/{name}/runs` | 실행 이력 (pagination) | query: page, page_size | `PaginatedResponse` |
| `GET`  | `/api/v1/pipelines/{name}/runs/{run_id}` | 실행 상세 | - | `PipelineRunResponse` |

### routes/pipelines.py — 파이프라인 엔드포인트

```python
from fastapi import APIRouter, HTTPException, Depends
from datetime import date

router = APIRouter(tags=["pipelines"])

@router.post("/pipelines/{name}/trigger")
def trigger_pipeline(name: str, request: TriggerRequest):
    """수동 즉시 실행.
    execution_date 미지정 시 오늘 날짜 사용.
    """

@router.get("/pipelines")
def list_pipelines():
    """설정에 정의된 모든 파이프라인 목록 조회."""

@router.get("/pipelines/{name}/runs")
def list_runs(name: str, page: int = 1, page_size: int = 50):
    """파이프라인 실행 이력 조회 (pagination).

    응답 포맷 (AG Grid 호환):
    {
        "items": [...],
        "total": 120,
        "page": 1,
        "page_size": 50
    }
    """

@router.get("/pipelines/{name}/runs/{run_id}")
def get_run_detail(name: str, run_id: str):
    """실행 상세 조회. 단계별 상태 포함."""
```

### routes/backfill.py — 백필 엔드포인트

```python
router = APIRouter(tags=["backfill"])

@router.post("/pipelines/{name}/backfill")
def request_backfill(name: str, request: BackfillRequest):
    """백필 요청. start_date~end_date 범위를 월별 분할하여 실행."""
```

### schemas.py — Pydantic 모델

```python
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class TriggerRequest(BaseModel):
    execution_date: date | None = None    # 미지정 시 오늘

class BackfillRequest(BaseModel):
    start_date: date
    end_date: date

class StepRunResponse(BaseModel):
    step_name: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    records_processed: int
    error_message: str | None
    retry_count: int

class PipelineRunResponse(BaseModel):
    id: str
    pipeline_name: str
    execution_date: date
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    trigger_type: str
    steps: list[StepRunResponse]

class PaginatedResponse(BaseModel):
    items: list[PipelineRunResponse]
    total: int
    page: int
    page_size: int
```

### CORS 설정 상세

```python
# Settings에 api 섹션 추가 필요
# config/pipelines.yaml:
#
# api:
#   allowed_origins:
#     - "http://10.0.0.*"
#     - "http://192.168.1.*"
#   host: "0.0.0.0"
#   port: 8000
```

- `allow_origins`: 사내망 IP 대역만 명시적으로 허용
- `allow_credentials: True`: 인증 쿠키/헤더 허용
- `allow_methods: ["*"]`: 모든 HTTP 메서드 허용 (사내망 전용이므로)
- `allow_headers: ["*"]`: 모든 헤더 허용

**내부망 추가 보안**: uvicorn 바인딩 주소를 사내 IP로 지정하거나, Windows 방화벽 규칙으로 외부 접근을 차단한다.

## 완료 조건

- [ ] `create_app()` 팩토리 동작 확인
- [ ] CORS 미들웨어 설정 확인 (허용 origin만 통과)
- [ ] `POST /api/v1/pipelines/{name}/trigger` — 수동 실행 테스트
- [ ] `POST /api/v1/pipelines/{name}/backfill` — 백필 요청 테스트
- [ ] `GET /api/v1/pipelines` — 파이프라인 목록 조회 테스트
- [ ] `GET /api/v1/pipelines/{name}/runs` — 페이지네이션 테스트
- [ ] `GET /api/v1/pipelines/{name}/runs/{run_id}` — 상세 조회 + 단계별 상태 포함 확인
- [ ] 존재하지 않는 파이프라인/실행 ID 요청 시 404 응답
- [ ] TestClient 기반 통합 테스트

## 참고 (선택)

- API 설계: `docs/architecture.md` 섹션 7
- Request/Response 스키마: `docs/architecture.md` 섹션 7
- AG Grid 호환 응답 포맷: `docs/architecture.md` 섹션 10
