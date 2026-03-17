# Task-009: Windows 서비스

## 목적

pywin32 ServiceFramework를 사용하여 Airflow Lite를 Windows 서비스로 등록/운영한다. APScheduler와 uvicorn(FastAPI)을 단일 프로세스 내에서 공존시키고, 서버 재부팅 시 자동 시작을 지원한다.

## 입력

- Task-006의 PipelineScheduler (APScheduler)
- Task-007의 create_app() (FastAPI)
- Settings (설정)

## 출력

- `src/airflow_lite/service/win_service.py` — Windows 서비스 래퍼
- `src/airflow_lite/__main__.py` — CLI 진입점 (서비스 install/start/stop/remove 명령)

## 구현 제약

- 단일 프로세스 (P1) — APScheduler + uvicorn이 하나의 프로세스에서 동작
- pywin32 (win32serviceutil.ServiceFramework) 사용
- Windows Server 2019 호환
- Graceful shutdown 지원 (실행 중인 파이프라인 완료 대기)

## 구현 상세

### win_service.py — Windows 서비스 래퍼

```python
import win32serviceutil
import win32service
import win32event
import servicemanager
import threading
import logging
import uvicorn

logger = logging.getLogger("airflow_lite.service")

class AirflowLiteService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AirflowLiteService"
    _svc_display_name_ = "Airflow Lite Pipeline Service"
    _svc_description_ = "MES 데이터 파이프라인 엔진"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.scheduler = None
        self.uvicorn_server = None
        self.api_thread = None

    def SvcDoRun(self):
        """서비스 시작.

        1. Settings 로드
        2. 로깅 설정
        3. PipelineScheduler 시작 (APScheduler — 메인 스레드)
        4. uvicorn을 별도 스레드에서 실행 (FastAPI)
        5. 종료 이벤트 대기
        """
        try:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )

            # 1. Settings 로드
            from airflow_lite.config.settings import Settings
            settings = Settings.load("config/pipelines.yaml")

            # 2. 로깅 설정
            from airflow_lite.logging_config.setup import setup_logging
            setup_logging(settings.storage.log_path)

            # 3. PipelineScheduler 시작
            from airflow_lite.scheduler.scheduler import PipelineScheduler
            self.scheduler = PipelineScheduler(settings, self._create_runner_factory(settings))
            self.scheduler.register_pipelines()
            self.scheduler.start()

            # 4. uvicorn을 별도 스레드에서 실행
            from airflow_lite.api.app import create_app
            app = create_app(settings)

            config = uvicorn.Config(
                app=app,
                host=getattr(settings.api, "host", "0.0.0.0"),
                port=getattr(settings.api, "port", 8000),
                log_level="info",
            )
            self.uvicorn_server = uvicorn.Server(config)

            self.api_thread = threading.Thread(
                target=self.uvicorn_server.run,
                daemon=True,
            )
            self.api_thread.start()

            logger.info("Airflow Lite 서비스 시작됨")

            # 5. 종료 이벤트 대기
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

        except Exception as e:
            logger.error(f"서비스 시작 실패: {e}")
            servicemanager.LogErrorMsg(f"서비스 시작 실패: {e}")

    def SvcStop(self):
        """Graceful shutdown.

        1. 서비스 상태를 STOP_PENDING으로 변경
        2. uvicorn 서버 종료
        3. PipelineScheduler shutdown(wait=True) — 실행 중인 파이프라인 완료 대기
        4. 종료 이벤트 시그널
        """
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info("서비스 종료 요청 수신")

        # uvicorn 종료
        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True

        # 스케줄러 종료 (실행 중인 작업 완료 대기)
        if self.scheduler:
            self.scheduler.shutdown(wait=True)

        # API 스레드 종료 대기
        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=30)

        # 종료 이벤트 시그널
        win32event.SetEvent(self.stop_event)
        logger.info("서비스 종료됨")

    def _create_runner_factory(self, settings):
        """pipeline_name을 받아 PipelineRunner를 생성하는 팩토리 함수 반환."""
        def factory(pipeline_name):
            # PipelineRunner 인스턴스 생성 로직
            # (Task-003의 PipelineRunner, Task-002의 Repository 등 조합)
            pass
        return factory
```

### 단일 프로세스 공존 구조 (P1)

```
AirflowLiteService (단일 프로세스)
├── 메인 스레드: APScheduler BackgroundScheduler
│   └── 파이프라인 실행 (스케줄/수동 트리거)
├── API 스레드: uvicorn.run() (FastAPI)
│   └── REST API 요청 처리
└── 종료 이벤트 대기 (WaitForSingleObject)
```

- APScheduler의 BackgroundScheduler는 자체 스레드풀에서 작업 실행
- uvicorn은 별도 daemon 스레드에서 실행
- 둘 다 같은 프로세스 내에서 동작하며, Settings/Repository 등 공유 가능
- Windows 서비스 관리자가 서버 재부팅 시 자동 시작

### __main__.py — CLI 진입점

```python
# src/airflow_lite/__main__.py
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m airflow_lite <command>")
        print("Commands: service [install|remove|start|stop]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "service":
        import win32serviceutil
        from airflow_lite.service.win_service import AirflowLiteService
        win32serviceutil.HandleCommandLine(AirflowLiteService)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 서비스 등록/관리 CLI

```bash
# 서비스 등록 (자동 시작 설정)
python -m airflow_lite service install --startup auto

# 서비스 제거
python -m airflow_lite service remove

# 서비스 시작
python -m airflow_lite service start

# 서비스 중지
python -m airflow_lite service stop
```

### Graceful Shutdown 순서

1. Windows SCM → `SvcStop()` 호출
2. `uvicorn.should_exit = True` → API 서버 종료 시작
3. `scheduler.shutdown(wait=True)` → 실행 중인 파이프라인 완료 대기
4. API 스레드 join (timeout=30초)
5. `SetEvent(stop_event)` → `SvcDoRun()` 루프 탈출
6. 서비스 종료 완료

## 완료 조건

- [ ] `AirflowLiteService` 클래스 구현 (ServiceFramework 상속)
- [ ] `SvcDoRun()` — Settings 로드 → 스케줄러 시작 → uvicorn 스레드 시작 → 이벤트 대기
- [ ] `SvcStop()` — uvicorn 종료 → 스케줄러 shutdown(wait=True) → 이벤트 시그널
- [ ] CLI 동작: `python -m airflow_lite service install` / `remove` / `start` / `stop`
- [ ] Graceful shutdown 테스트: 실행 중 파이프라인 완료 후 종료 확인
- [ ] 서비스 자동 시작 설정 확인 (--startup auto)

## 참고 (선택)

- Windows 서비스 설계: `docs/architecture.md` 섹션 9
- 단일 프로세스 구조: `docs/architecture.md` 설계 원칙 P1
- pywin32 서비스 문서: https://github.com/mhammond/pywin32
