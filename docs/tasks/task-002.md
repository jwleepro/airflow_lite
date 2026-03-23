# Task-002: SQLite 상태 저장소

## 목적

파이프라인 실행 이력과 단계별 상태를 영구 저장하는 SQLite 기반 상태 저장소를 구현한다. WAL 모드로 API 읽기 동시성을 지원하며, Repository 패턴으로 데이터 접근을 추상화한다.

## 입력

- Task-001에서 생성된 프로젝트 구조
- SQLite 파일 경로: `Settings.storage.sqlite_path`

## 출력

- `src/airflow_lite/storage/database.py` — SQLite 연결 관리
- `src/airflow_lite/storage/models.py` — 데이터 모델 (dataclass)
- `src/airflow_lite/storage/repository.py` — CRUD Repository
- `src/airflow_lite/storage/schema.sql` — DDL

## 구현 제약

- SQLite WAL 모드 사용 (API 읽기 동시성 처리)
- foreign_keys = ON
- 단일 프로세스 환경 (P1) — 복잡한 동시성 제어 불필요

## 구현 상세

### schema.sql — DDL

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              TEXT PRIMARY KEY,     -- UUID
    pipeline_name   TEXT NOT NULL,
    execution_date  TEXT NOT NULL,        -- YYYY-MM-DD
    status          TEXT NOT NULL DEFAULT 'pending',
                    -- pending | running | success | failed
    started_at      TEXT,                 -- ISO 8601
    finished_at     TEXT,                 -- ISO 8601
    trigger_type    TEXT NOT NULL DEFAULT 'scheduled',
                    -- scheduled | manual | backfill
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(pipeline_name, execution_date, trigger_type)
);

CREATE TABLE IF NOT EXISTS step_runs (
    id                TEXT PRIMARY KEY,   -- UUID
    pipeline_run_id   TEXT NOT NULL REFERENCES pipeline_runs(id),
    step_name         TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',
                      -- pending | running | success | failed | skipped
    started_at        TEXT,
    finished_at       TEXT,
    records_processed INTEGER DEFAULT 0,
    error_message     TEXT,
    retry_count       INTEGER DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_exec_date
    ON pipeline_runs(execution_date);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_step_runs_pipeline_run
    ON step_runs(pipeline_run_id);
```

### models.py — 데이터 모델

```python
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import uuid

@dataclass
class PipelineRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_name: str = ""
    execution_date: date = None
    status: str = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trigger_type: str = "scheduled"
    created_at: datetime | None = None

@dataclass
class StepRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_run_id: str = ""
    step_name: str = ""
    status: str = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    records_processed: int = 0
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime | None = None
```

### database.py — SQLite 연결 관리

```python
import sqlite3
from pathlib import Path

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        """schema.sql을 실행하여 테이블 생성."""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn = self.get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()
```

### repository.py — CRUD Repository

```python
class PipelineRunRepository:
    """pipeline_runs 테이블 CRUD. 조회 시 execution_date, pipeline_name 기반 필터링 지원."""

    def __init__(self, database: Database):
        self.database = database

    def create(self, run: PipelineRun) -> PipelineRun:
        """INSERT. id는 UUID 자동 생성."""

    def update_status(
        self, run_id: str, status: str, finished_at: datetime | None = None
    ) -> None:
        """status, finished_at 업데이트."""

    def find_by_id(self, run_id: str) -> PipelineRun | None:
        """단건 조회."""

    def find_by_pipeline(
        self, pipeline_name: str, limit: int = 50
    ) -> list[PipelineRun]:
        """파이프라인 이름으로 최근 실행 이력 조회."""

    def find_by_execution_date(
        self, pipeline_name: str, execution_date: date
    ) -> PipelineRun | None:
        """특정 파이프라인의 특정 날짜 실행 조회."""


class StepRunRepository:
    """step_runs 테이블 CRUD. pipeline_run_id 기반 조회 지원."""

    def __init__(self, database: Database):
        self.database = database

    def create(self, step_run: StepRun) -> StepRun:
        """INSERT. id는 UUID 자동 생성."""

    def update_status(self, step_id: str, status: str, **kwargs) -> None:
        """status 업데이트. kwargs로 finished_at, records_processed,
        error_message, retry_count 등 선택적 필드 업데이트."""

    def find_by_pipeline_run(self, pipeline_run_id: str) -> list[StepRun]:
        """특정 파이프라인 실행의 모든 단계 조회."""
```

## 완료 조건

- [ ] `Database.initialize()` 호출 시 테이블/인덱스 생성 확인
- [ ] WAL 모드 활성화 확인 (`PRAGMA journal_mode` 쿼리 결과 = "wal")
- [ ] `PipelineRunRepository` CRUD 테스트 (create, update_status, find_by_*)
- [ ] `StepRunRepository` CRUD 테스트 (create, update_status, find_by_pipeline_run)
- [ ] `UNIQUE(pipeline_name, execution_date, trigger_type)` 제약 조건 동작 확인
- [ ] foreign key 제약 동작 확인 (존재하지 않는 pipeline_run_id로 step_run 생성 시 실패)
- [ ] 테스트에서 임시 DB 파일 사용 (conftest.py에 fixture 추가)

## 참고 (선택)

- DDL 원본: `docs/system_design/architecture.md` 섹션 4
- 전체 아키텍처: `docs/system_design/architecture.md`
