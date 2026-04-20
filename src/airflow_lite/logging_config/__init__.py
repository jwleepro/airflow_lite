"""Logging configuration module.

주요 컴포넌트:
- setup_logging: 기존 표준 logging 설정 (하위 호환)
- setup_structlog: Structlog + 표준 logging 통합 설정
- RequestContextMiddleware: FastAPI 요청 컨텍스트 미들웨어
- log_execution, log_db_operation: 자동 로깅 데코레이터
"""

from .setup import setup_logging

__all__ = ["setup_logging"]
