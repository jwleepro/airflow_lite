"""T-032: /health 헬스체크 엔드포인트."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@dataclass
class ComponentCheck:
    name: str
    status: str  # "ok" | "degraded" | "error"
    detail: str | None = None


def _check_scheduler(request: Request) -> ComponentCheck:
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        return ComponentCheck(name="scheduler", status="ok", detail="not configured")
    running = getattr(scheduler.scheduler, "running", False) if hasattr(scheduler, "scheduler") else False
    if running:
        return ComponentCheck(name="scheduler", status="ok")
    return ComponentCheck(name="scheduler", status="error", detail="not running")


def _check_mart_db(request: Request) -> ComponentCheck:
    query_service = getattr(request.app.state, "analytics_query_service", None)
    if query_service is None:
        return ComponentCheck(name="mart_db", status="ok", detail="not configured")
    try:
        db_path = Path(query_service.db_path)
        if not db_path.exists():
            return ComponentCheck(name="mart_db", status="error", detail="database file missing")
        return ComponentCheck(name="mart_db", status="ok")
    except Exception as exc:
        return ComponentCheck(name="mart_db", status="error", detail=str(exc))


def _check_disk(request: Request) -> ComponentCheck:
    settings = getattr(request.app.state, "settings", None)
    check_path = "."
    if settings and hasattr(settings, "storage"):
        check_path = getattr(settings.storage, "parquet_base_path", ".")
    try:
        usage = shutil.disk_usage(check_path)
        free_gb = usage.free / (1024**3)
        if free_gb < 1.0:
            return ComponentCheck(name="disk", status="error", detail=f"{free_gb:.1f} GB free")
        if free_gb < 5.0:
            return ComponentCheck(name="disk", status="degraded", detail=f"{free_gb:.1f} GB free")
        return ComponentCheck(name="disk", status="ok", detail=f"{free_gb:.1f} GB free")
    except Exception as exc:
        return ComponentCheck(name="disk", status="error", detail=str(exc))


@router.get("/health")
def health_check(request: Request):
    checks = [
        _check_scheduler(request),
        _check_mart_db(request),
        _check_disk(request),
    ]

    overall = "healthy"
    for check in checks:
        if check.status == "error":
            overall = "unhealthy"
            break
        if check.status == "degraded":
            overall = "degraded"

    return {
        "status": overall,
        "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in checks],
    }
