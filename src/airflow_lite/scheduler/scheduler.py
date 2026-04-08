from datetime import date
from typing import TYPE_CHECKING
import re

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

from airflow_lite.bootstrap import DEFAULT_CONFIG_PATH
from airflow_lite.runtime import run_scheduled_pipeline

if TYPE_CHECKING:
    from collections.abc import Callable
    from airflow_lite.config.settings import Settings

logger = logging.getLogger("airflow_lite.scheduler")
INTERVAL_PATTERN = re.compile(r"^interval:(\d+)([smhd]?)$", re.IGNORECASE)


class PipelineScheduler:
    """APScheduler BackgroundScheduler를 래핑하여 파이프라인 스케줄링을 관리한다.

    설계 제약:
    - SQLite JobStore 사용 (상태 영속화)
    - 동일 파이프라인 동시 실행 방지 (max_instances=1)
    - misfire_grace_time으로 놓친 실행 처리
    """

    def __init__(
        self,
        settings: "Settings",
        runner_factory: "Callable | None" = None,
        config_path: str = DEFAULT_CONFIG_PATH,
    ):
        """
        Args:
            settings: YAML 설정 객체
            runner_factory: pipeline_name을 받아 PipelineRunner를 생성하는 팩토리
        """
        self.settings = settings
        self.runner_factory = runner_factory
        self.config_path = config_path

        # APScheduler 설정
        self.scheduler = BackgroundScheduler(
            jobstores={
                "default": SQLAlchemyJobStore(
                    url=f"sqlite:///{settings.storage.sqlite_path}"
                )
            },
            job_defaults={
                "coalesce": settings.scheduler.coalesce,
                "max_instances": settings.scheduler.max_instances,
                "misfire_grace_time": settings.scheduler.misfire_grace_time_seconds,
            },
        )

    def register_pipelines(self) -> None:
        """설정의 모든 파이프라인을 스케줄러에 등록.

        각 파이프라인의 schedule을 CronTrigger 또는 IntervalTrigger로 변환하여 등록.
        replace_existing=True로 재등록 시 안전하게 덮어쓰기.
        """
        for pipeline_config in self.settings.pipelines:
            trigger = self._build_trigger(pipeline_config.schedule)
            self.scheduler.add_job(
                func=run_scheduled_pipeline,
                trigger=trigger,
                id=pipeline_config.name,
                args=[self.config_path, pipeline_config.name],
                replace_existing=True,
            )
            logger.info(
                f"파이프라인 등록: {pipeline_config.name} "
                f"(schedule: {pipeline_config.schedule})"
            )

    def _build_trigger(self, schedule: str):
        """schedule 문자열을 APScheduler trigger로 변환한다.

        지원 형식:
        - Cron: '0 2 * * *'
        - Interval: 'interval:30m', 'interval:6h', 'interval:15'
          기본 단위는 초.
        """
        match = INTERVAL_PATTERN.fullmatch(schedule.strip())
        if match:
            value = int(match.group(1))
            unit = (match.group(2) or "s").lower()
            unit_map = {
                "s": "seconds",
                "m": "minutes",
                "h": "hours",
                "d": "days",
            }
            return IntervalTrigger(**{unit_map[unit]: value})

        return CronTrigger.from_crontab(schedule)

    def _run_pipeline(self, pipeline_name: str) -> None:
        """스케줄러에 의해 호출되는 파이프라인 실행 함수.

        execution_date는 오늘 날짜, trigger_type은 'scheduled'.
        예외는 로깅 후 삼키며, APScheduler 잡 제거를 방지한다.
        """
        try:
            if self.runner_factory is None:
                run_scheduled_pipeline(self.config_path, pipeline_name)
                return

            runner = self.runner_factory(pipeline_name)
            runner.run(execution_date=date.today(), trigger_type="scheduled")
        except Exception:
            logger.exception("스케줄 실행 실패: %s", pipeline_name)

    def start(self) -> None:
        """스케줄러 시작."""
        self.scheduler.start()
        logger.info("스케줄러 시작됨")

    def shutdown(self, wait: bool = True) -> None:
        """Graceful shutdown: 실행 중인 작업 완료 대기 후 종료.

        Args:
            wait: True면 실행 중인 작업 완료까지 대기, False면 즉시 종료
        """
        self.scheduler.shutdown(wait=wait)
        logger.info(f"스케줄러 종료됨 (wait={wait})")
