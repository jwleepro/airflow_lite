"""파이프라인 실행 전용 in-process 스레드풀.

Airflow LocalExecutor 와 이름이 겹치지 않도록 PipelineLocalExecutor 로 명명한다.
단일 서버·Windows·폐쇄망 환경에서 별도 프로세스 도입 없이
웹/API 요청 스레드와 실제 실행 경로를 분리하기 위해 사용한다.
"""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

logger = logging.getLogger("airflow_lite.executor")


class PipelineLocalExecutor:
    def __init__(self, max_workers: int = 2):
        if max_workers < 1:
            raise ValueError("max_workers 는 1 이상이어야 합니다.")
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="airflow-lite-dispatch",
        )
        self._max_workers = max_workers

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def submit(self, fn: Callable, /, *args, **kwargs) -> Future:
        return self._pool.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)
