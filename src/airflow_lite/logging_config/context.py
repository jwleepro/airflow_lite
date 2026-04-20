"""Request context management using ContextVar.

ContextVar를 사용하여 request-scoped 값을 관리합니다.
비동기 경계를 넘어 자동 전파되며, 동시성 요청 간 격리가 보장됩니다.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
pipeline_name_var: ContextVar[str | None] = ContextVar("pipeline_name", default=None)


def get_request_id() -> str:
    """현재 컨텍스트의 request_id 반환. 없으면 새로 생성."""
    rid = request_id_var.get()
    if rid is None:
        rid = uuid.uuid4().hex[:8]
        request_id_var.set(rid)
    return rid


def bind_request_context(
    request_id: str,
    user_id: str | None = None,
    pipeline_name: str | None = None,
) -> None:
    """미들웨어에서 호출. request 시작 시 컨텍스트 바인딩."""
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if pipeline_name:
        pipeline_name_var.set(pipeline_name)


def bind_pipeline_context(pipeline_name: str) -> None:
    """파이프라인 실행 시 컨텍스트에 파이프라인명 바인딩."""
    pipeline_name_var.set(pipeline_name)


def clear_request_context() -> None:
    """request 종료 시 컨텍스트 정리."""
    request_id_var.set(None)
    user_id_var.set(None)
    pipeline_name_var.set(None)


def get_context_dict() -> dict[str, str | None]:
    """현재 컨텍스트를 딕셔너리로 반환. 로그 프로세서에서 사용."""
    return {
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
        "pipeline": pipeline_name_var.get(),
    }
