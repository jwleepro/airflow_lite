from datetime import date
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import logging

from airflow_lite.bootstrap import DEFAULT_CONFIG_PATH
from airflow_lite.scheduler.schedule_validator import build_trigger
from airflow_lite.service.dispatch_service import PipelineBusyError

if TYPE_CHECKING:
    from airflow_lite.config.settings import Settings
    from airflow_lite.service.dispatch_service import PipelineDispatchService

logger = logging.getLogger("airflow_lite.scheduler")

# 모듈 레벨 dispatcher 참조. APScheduler 의 SQLAlchemyJobStore 가 잡을 pickle 로 저장하므로,
# 콜백에 bound method 를 넘기면 PipelineScheduler(및 Lock 을 가진 dispatcher) 가 같이 직렬화되어 실패한다.
# 프로세스 싱글톤 한 개만 사용하면 충분하므로 모듈 레벨에서 잡아둔다.
_process_dispatcher: "PipelineDispatchService | None" = None


def _set_process_dispatcher(dispatcher: "PipelineDispatchService") -> None:
    global _process_dispatcher
    _process_dispatcher = dispatcher


def _scheduled_dispatcher_callback(pipeline_name: str) -> None:
    """APScheduler 잡 콜백 (모듈 레벨 함수라 pickle 안전).

    현재 프로세스에 등록된 dispatcher 를 통해 queued run 을 생성하고 즉시 반환한다.
    실제 실행은 PipelineLocalExecutor 워커가 소비한다.
    """
    dispatcher = _process_dispatcher
    if dispatcher is None:
        logger.error("스케줄 dispatcher 가 초기화되지 않았습니다: %s", pipeline_name)
        return
    try:
        dispatcher.submit_manual_run(
            pipeline_name=pipeline_name,
            execution_date=date.today(),
            force_rerun=False,
            trigger_type="scheduled",
        )
    except PipelineBusyError as exc:
        logger.info(
            "스케줄 dispatcher 스킵: pipeline=%s run_id=%s status=%s",
            pipeline_name,
            exc.run_id,
            exc.status,
        )
    except Exception:
        logger.exception("스케줄 dispatcher 호출 실패: %s", pipeline_name)


class PipelineScheduler:
    """APScheduler BackgroundScheduler 를 래핑하여 파이프라인 스케줄링을 관리한다.

    설계 제약:
    - SQLite JobStore 사용 (상태 영속화)
    - 동일 파이프라인 동시 실행 방지 (max_instances=1)
    - misfire_grace_time 으로 놓친 실행 처리
    - 모든 스케줄 트리거는 PipelineDispatchService 를 경유하여 queued run 생성 후 워커에 위임한다.
    """

    def __init__(
        self,
        settings: "Settings",
        dispatch_service: "PipelineDispatchService",
        config_path: str = DEFAULT_CONFIG_PATH,
    ):
        self.settings = settings
        self.config_path = config_path
        self.dispatch_service = dispatch_service
        _set_process_dispatcher(dispatch_service)

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

        모든 잡 콜백은 _scheduled_dispatcher_callback (모듈 레벨) 경유로 통일된다.
        replace_existing=True 로 재등록 시 안전하게 덮어쓴다.
        """
        for pipeline_config in self.settings.pipelines:
            trigger = build_trigger(pipeline_config.schedule)
            self.scheduler.add_job(
                func=_scheduled_dispatcher_callback,
                trigger=trigger,
                id=pipeline_config.name,
                args=[pipeline_config.name],
                replace_existing=True,
            )
            logger.info(
                f"파이프라인 등록: {pipeline_config.name} "
                f"(schedule: {pipeline_config.schedule})"
            )

    def start(self) -> None:
        self.scheduler.start()
        logger.info("스케줄러 시작됨")

    def shutdown(self, wait: bool = True) -> None:
        """Graceful shutdown: 실행 중인 작업 완료 대기 후 종료.

        Args:
            wait: True 면 실행 중인 작업 완료까지 대기, False 면 즉시 종료
        """
        self.scheduler.shutdown(wait=wait)
        logger.info(f"스케줄러 종료됨 (wait={wait})")
