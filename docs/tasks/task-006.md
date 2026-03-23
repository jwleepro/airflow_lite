# Task-006: APScheduler 스케줄러

## 목적

APScheduler BackgroundScheduler를 래핑하여 YAML 설정 기반의 주기적 파이프라인 실행을 관리한다. SQLite JobStore로 스케줄 상태를 영속화하고, misfire 처리와 graceful shutdown을 지원한다.

## 입력

- Task-003의 PipelineRunner (파이프라인 실행)
- Settings (YAML 설정 — 파이프라인별 cron 스케줄)
- Settings.storage.sqlite_path (SQLite 경로 — JobStore 공유)

## 출력

- `src/airflow_lite/scheduler/scheduler.py` — PipelineScheduler

## 구현 제약

- 단일 프로세스 (P1) — BackgroundScheduler 사용 (별도 프로세스 X)
- 동일 파이프라인 동시 실행 방지 (`max_instances=1`)
- SQLite JobStore 사용 (서버 재시작 시 스케줄 복구)
- misfire_grace_time으로 놓친 실행 처리

## 구현 상세

### scheduler.py — PipelineScheduler

```python
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
        from datetime import date
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
```

### misfire 처리 동작

| 상황 | 동작 |
|------|------|
| 서버 다운타임 < 1시간 | 재시작 시 놓친 실행 즉시 수행 |
| 서버 다운타임 > 1시간 | 놓친 실행 건너뛰고 다음 스케줄 대기 |
| 같은 파이프라인 이미 실행 중 | 새 실행 건너뛰기 (max_instances=1) |
| 여러 번 놓침 | 1회만 실행 (coalesce=True) |

### APScheduler 설정값 근거

- `coalesce: True` — 서버 장기 다운 후 재시작 시 동일 파이프라인이 여러 번 쌓이는 것을 방지
- `max_instances: 1` — 파이프라인은 순차 실행만 지원 (P1). 동일 파이프라인 병렬 실행은 데이터 충돌 위험
- `misfire_grace_time: 3600` (1시간) — MES 환경에서 서버 점검 등으로 1시간 이내 다운타임은 빈번. 이 범위 내 놓친 실행은 복구 실행
- `SQLAlchemyJobStore(sqlite)` — 메인 SQLite DB와 동일 파일 사용. 별도 DB 서버 불필요 (P1)

## 완료 조건

- [ ] `PipelineScheduler` 생성 시 APScheduler 설정 적용 확인
- [ ] `register_pipelines()` — CronTrigger 등록 테스트
- [ ] `start()` / `shutdown()` 생명주기 테스트
- [ ] misfire 처리 테스트: grace time 내/외 동작 확인
- [ ] `max_instances=1` 동작 확인: 동일 파이프라인 중복 실행 차단
- [ ] `coalesce=True` 동작 확인: 누적 실행 1회로 병합
- [ ] graceful shutdown 테스트: `shutdown(wait=True)` 시 실행 중 작업 완료 대기

## 참고 (선택)

- 스케줄러 설계: `docs/system_design/architecture.md` 섹션 6
- APScheduler 공식 문서: https://apscheduler.readthedocs.io/
