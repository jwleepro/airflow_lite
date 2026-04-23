"""Automatic logging decorators (Spring AOP alternative).

ParamSpec(PEP 612)을 활용하여 타입 안전성을 보장하면서
함수 진입/퇴장/에러를 자동으로 로깅합니다.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import TYPE_CHECKING, Callable, ParamSpec, TypeVar

if TYPE_CHECKING:
    pass

P = ParamSpec("P")
R = TypeVar("R")

_SENSITIVE_KEYS = frozenset({"password", "token", "secret", "api_key", "credential"})


def _mask_sensitive(kwargs: dict) -> dict:
    """민감 키워드가 포함된 인자 마스킹."""
    result = {}
    for k, v in kwargs.items():
        k_lower = k.lower()
        if any(s in k_lower for s in _SENSITIVE_KEYS):
            result[k] = "***"
        else:
            result[k] = v
    return result


def log_execution(
    logger_name: str | None = None,
    *,
    log_args: bool = False,
    log_result: bool = False,
    level: int = logging.DEBUG,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """함수 진입/퇴장/에러 자동 로깅 데코레이터.

    Args:
        logger_name: 로거 이름. None이면 모듈+함수명으로 자동 생성
        log_args: True면 kwargs를 로깅 (민감정보 마스킹)
        log_result: True면 반환값 타입을 로깅
        level: 진입/퇴장 로그 레벨 (에러는 항상 ERROR)

    Examples:
        @log_execution("airflow_lite.api.routes.pipelines", log_args=True)
        def trigger_pipeline(name: str, body: TriggerRequest):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        nonlocal logger_name
        if logger_name is None:
            logger_name = f"airflow_lite.{func.__module__}.{func.__qualname__}"

        logger = logging.getLogger(logger_name)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            func_name = func.__qualname__

            entry_extra: dict = {"event": "function_enter", "function": func_name}
            if log_args and kwargs:
                safe_kwargs = _mask_sensitive(kwargs)
                entry_extra["kwargs"] = str(safe_kwargs)[:200]
            logger.log(level, entry_extra)

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time

                exit_extra: dict = {
                    "event": "function_exit",
                    "function": func_name,
                    "elapsed_ms": round(elapsed * 1000, 2),
                }
                if log_result and result is not None:
                    exit_extra["result_type"] = type(result).__name__
                logger.log(level, exit_extra)

                return result

            except Exception as exc:
                elapsed = time.perf_counter() - start_time
                logger.exception(
                    {
                        "event": "function_error",
                        "function": func_name,
                        "elapsed_ms": round(elapsed * 1000, 2),
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                )
                raise

        return wrapper

    return decorator


def log_db_operation(table_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Repository 메서드용 간소화 데코레이터.

    Args:
        table_name: 테이블명 (로거 이름에 포함)

    Examples:
        @log_db_operation("pipeline_runs")
        def create(self, run: PipelineRun) -> PipelineRun:
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        logger = logging.getLogger(f"airflow_lite.storage.{table_name}")

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            operation = func.__name__
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.debug(
                    {
                        "event": "db_operation",
                        "table": table_name,
                        "operation": operation,
                        "elapsed_ms": round(elapsed * 1000, 2),
                    }
                )
                return result
            except Exception as exc:
                elapsed = time.perf_counter() - start
                logger.error(
                    {
                        "event": "db_operation_error",
                        "table": table_name,
                        "operation": operation,
                        "elapsed_ms": round(elapsed * 1000, 2),
                        "error": str(exc)[:500],
                    }
                )
                raise

        return wrapper

    return decorator


def log_async_execution(
    logger_name: str | None = None,
    *,
    log_args: bool = False,
    log_result: bool = False,
    level: int = logging.DEBUG,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """비동기 함수용 로깅 데코레이터."""
    import asyncio

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        nonlocal logger_name
        if logger_name is None:
            logger_name = f"airflow_lite.{func.__module__}.{func.__qualname__}"

        logger = logging.getLogger(logger_name)

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            func_name = func.__qualname__

            entry_extra: dict = {"event": "function_enter", "function": func_name}
            if log_args and kwargs:
                safe_kwargs = _mask_sensitive(kwargs)
                entry_extra["kwargs"] = str(safe_kwargs)[:200]
            logger.log(level, entry_extra)

            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time

                exit_extra: dict = {
                    "event": "function_exit",
                    "function": func_name,
                    "elapsed_ms": round(elapsed * 1000, 2),
                }
                if log_result and result is not None:
                    exit_extra["result_type"] = type(result).__name__
                logger.log(level, exit_extra)

                return result

            except Exception as exc:
                elapsed = time.perf_counter() - start_time
                logger.exception(
                    {
                        "event": "function_error",
                        "function": func_name,
                        "elapsed_ms": round(elapsed * 1000, 2),
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                )
                raise

        return wrapper

    return decorator
