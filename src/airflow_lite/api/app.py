from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from airflow_lite.config.settings import Settings
    from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository


def create_app(
    settings: "Settings",
    runner_map: dict | None = None,
    backfill_map: dict | None = None,
    run_repo: "PipelineRunRepository | None" = None,
    step_repo: "StepRunRepository | None" = None,
) -> FastAPI:
    """FastAPI 앱 팩토리.

    설계 제약:
    - CORS: 사내망 IP 대역만 허용 [NFR-11]
    - API prefix: /api/v1
    """
    app = FastAPI(
        title="Airflow Lite API",
        version="1.0.0",
    )

    # 의존성을 app.state에 저장
    app.state.settings = settings
    app.state.runner_map = runner_map or {}
    app.state.backfill_map = backfill_map or {}
    app.state.run_repo = run_repo
    app.state.step_repo = step_repo

    # CORS 미들웨어 설정 — 사내망 전용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.allowed_origins,
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
