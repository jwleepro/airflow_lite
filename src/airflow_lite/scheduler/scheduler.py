from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger("airflow_lite.scheduler")


class PipelineScheduler:
    """APScheduler BackgroundScheduler를 래핑하여 파이프라인 스케줄링을 관리한다.

    설계 제약:
    - SQLite JobStore 사용 (상태 영속화)
    - 동일 파이프라인 동시 실행 방지 (max_instances=1)
    - misfire_grace_time으로 놓친 실행 처리
    """

    def __init__(self, settings: "Settings", runner_factory: "Callable"):
        """
        Args:
            settings: YAML 설정 객체
            runner_factory: pipeline_name을 받아 PipelineRunner를 생성하는 팩토리
        """
        self.settings = settings
        self.runner_factory = runner_factory

        # APScheduler 설정
        self.scheduler = BackgroundScheduler(
            jobstores={
                "default": SQLAlchemyJobStore(
                    url=f"sqlite:///{settings.storage.sqlite_path}"
                )
            },
            job_defaults={
                "coalesce": True,              # 누적 실행 방지: 여러 번 놓쳤어도 1회만 실행
                "max_instances": 1,            # 동시 실행 방지: 같은 파이프라인 중복 실행 차단
                "misfire_grace_time": 3600,    # 1시간 유예: 이 시간 내 놓친 실행은 즉시 실행
            },
        )

    def register_pipelines(self) -> None:
        """설정의 모든 파이프라인을 스케줄러에 등록.

        각 파이프라인의 schedule (cron 표현식)을 CronTrigger로 변환하여 등록.
        replace_existing=True로 재등록 시 안전하게 덮어쓰기.
        """
        for pipeline_config in self.settings.pipelines:
            trigger = CronTrigger.from_crontab(pipeline_config.schedule)
            self.scheduler.add_job(
                func=self._run_pipeline,
                trigger=trigger,
                id=pipeline_config.name,
                args=[pipeline_config.name],
                replace_existing=True,
            )
            logger.info(
                f"파이프라인 등록: {pipeline_config.name} "
                f"(schedule: {pipeline_config.schedule})"
            )

    def _run_pipeline(self, pipeline_name: str) -> None:
        """스케줄러에 의해 호출되는 파이프라인 실행 함수.

        execution_date는 오늘 날짜, trigger_type은 'scheduled'.
        """
        runner = self.runner_factory(pipeline_name)
        runner.run(execution_date=date.today(), trigger_type="scheduled")

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
