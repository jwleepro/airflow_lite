"""FastAPI Request Context Middleware.

모든 HTTP 요청에 request_id를 주입하고 요청/응답을 로깅합니다.
X-Request-ID 헤더가 있으면 사용, 없으면 생성합니다.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import bind_request_context, clear_request_context

logger = logging.getLogger("airflow_lite.api.middleware")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """모든 HTTP 요청에 request_id를 주입하고 요청/응답을 로깅.

    - X-Request-ID 헤더가 있으면 사용, 없으면 생성
    - 응답 헤더에도 X-Request-ID를 포함시켜 클라이언트 추적 가능
    - 4xx 이상은 WARNING, 그 외는 INFO 레벨로 로깅
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = uuid.uuid4().hex[:8]

        bind_request_context(request_id=request_id)

        start_time = time.perf_counter()

        path = request.url.path
        if not self._should_skip_logging(path):
            logger.info(
                {
                    "event": "request_start",
                    "method": request.method,
                    "path": path,
                    "query": str(request.query_params)[:100]
                    if request.query_params
                    else None,
                    "client_ip": request.client.host if request.client else None,
                }
            )

        try:
            response = await call_next(request)
            elapsed = time.perf_counter() - start_time

            if not self._should_skip_logging(path):
                log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
                logger.log(
                    log_level,
                    {
                        "event": "request_end",
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                        "elapsed_ms": round(elapsed * 1000, 2),
                    },
                )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            logger.exception(
                {
                    "event": "request_error",
                    "method": request.method,
                    "path": path,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "error_type": type(exc).__name__,
                }
            )
            raise

        finally:
            clear_request_context()

    @staticmethod
    def _should_skip_logging(path: str) -> bool:
        """헬스체크 등 저빈도 경로는 로깅 스킵."""
        skip_paths = {"/health", "/api/v1/health", "/favicon.ico"}
        return path in skip_paths
