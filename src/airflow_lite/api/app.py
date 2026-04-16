import re
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from airflow_lite.api.paths import API_PREFIX

if TYPE_CHECKING:
    from airflow_lite.config.settings import Settings
    from airflow_lite.storage.repository import PipelineRunRepository, StepRunRepository


def _split_cors_origins(origins: list[str]) -> tuple[list[str], str | None]:
    exact_origins: list[str] = []
    wildcard_patterns: list[str] = []

    for origin in origins:
        if "*" in origin:
            wildcard_patterns.append(re.escape(origin).replace(r"\*", r"[^/]+"))
        else:
            exact_origins.append(origin)

    if not wildcard_patterns:
        return exact_origins, None

    regex = f"^(?:{'|'.join(wildcard_patterns)})$"
    return exact_origins, regex


def create_app(
    settings: "Settings",
    runner_map: dict | None = None,
    backfill_map: dict | None = None,
    run_repo: "PipelineRunRepository | None" = None,
    step_repo: "StepRunRepository | None" = None,
    analytics_query_service=None,
    analytics_export_service=None,
    admin_repo=None,
    dispatch_service=None,
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
    app.state.analytics_query_service = analytics_query_service
    app.state.analytics_export_service = analytics_export_service
    app.state.admin_repo = admin_repo
    app.state.dispatch_service = dispatch_service

    # CORS 미들웨어 설정 — 사내망 전용
    allowed_origins, allowed_origin_regex = _split_cors_origins(settings.api.allowed_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    from airflow_lite.api.routes.web import router as web_router
    from airflow_lite.api.routes.pipelines import router as pipelines_router
    from airflow_lite.api.routes.analytics import router as analytics_router
    from airflow_lite.api.routes.backfill import router as backfill_router
    from airflow_lite.api.routes.health import router as health_router
    from airflow_lite.api.routes.admin import router as admin_router

    # 브라우저 자동 요청 처리 — favicon 없으면 404 로그가 매 페이지마다 찍힘
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    # 정적 파일(webui CSS/JS 등) 서빙
    _static_dir = Path(__file__).parent / "static"
    if _static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    app.include_router(web_router)
    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(pipelines_router, prefix=API_PREFIX)
    app.include_router(backfill_router, prefix=API_PREFIX)
    app.include_router(analytics_router, prefix=API_PREFIX)
    app.include_router(admin_router, prefix=API_PREFIX)

    return app
