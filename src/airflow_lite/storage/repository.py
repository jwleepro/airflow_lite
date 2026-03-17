from datetime import date, datetime
from typing import Optional

from .database import Database
from .models import PipelineRun, StepRun


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _row_to_pipeline_run(row) -> PipelineRun:
    return PipelineRun(
        id=row["id"],
        pipeline_name=row["pipeline_name"],
        execution_date=_parse_date(row["execution_date"]),
        status=row["status"],
        started_at=_parse_datetime(row["started_at"]),
        finished_at=_parse_datetime(row["finished_at"]),
        trigger_type=row["trigger_type"],
        created_at=_parse_datetime(row["created_at"]),
    )


def _row_to_step_run(row) -> StepRun:
    return StepRun(
        id=row["id"],
        pipeline_run_id=row["pipeline_run_id"],
        step_name=row["step_name"],
        status=row["status"],
        started_at=_parse_datetime(row["started_at"]),
        finished_at=_parse_datetime(row["finished_at"]),
        records_processed=row["records_processed"],
        error_message=row["error_message"],
        retry_count=row["retry_count"],
        created_at=_parse_datetime(row["created_at"]),
    )


class PipelineRunRepository:
    """pipeline_runs 테이블 CRUD. 조회 시 execution_date, pipeline_name 기반 필터링 지원."""

    def __init__(self, database: Database):
        self.database = database

    def create(self, run: PipelineRun) -> PipelineRun:
        """INSERT. id는 UUID 자동 생성."""
        conn = self.database.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO pipeline_runs
                    (id, pipeline_name, execution_date, status, started_at,
                     finished_at, trigger_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
                """,
                (
                    run.id,
                    run.pipeline_name,
                    run.execution_date.isoformat() if run.execution_date else None,
                    run.status,
                    run.started_at.isoformat() if run.started_at else None,
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.trigger_type,
                    run.created_at.isoformat() if run.created_at else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return run

    def update_status(
        self, run_id: str, status: str, finished_at: datetime | None = None
    ) -> None:
        """status, finished_at 업데이트."""
        conn = self.database.get_connection()
        try:
            conn.execute(
                "UPDATE pipeline_runs SET status = ?, finished_at = ? WHERE id = ?",
                (
                    status,
                    finished_at.isoformat() if finished_at else None,
                    run_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def find_by_id(self, run_id: str) -> PipelineRun | None:
        """단건 조회."""
        conn = self.database.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)
            ).fetchone()
        finally:
            conn.close()
        return _row_to_pipeline_run(row) if row else None

    def find_by_pipeline(
        self, pipeline_name: str, limit: int = 50
    ) -> list[PipelineRun]:
        """파이프라인 이름으로 최근 실행 이력 조회."""
        conn = self.database.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM pipeline_runs
                WHERE pipeline_name = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (pipeline_name, limit),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_pipeline_run(r) for r in rows]

    def find_by_pipeline_paginated(
        self, pipeline_name: str, page: int = 1, page_size: int = 50
    ) -> tuple[list[PipelineRun], int]:
        """파이프라인 이름으로 실행 이력 조회 (pagination). (runs, total) 반환."""
        offset = (page - 1) * page_size
        conn = self.database.get_connection()
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM pipeline_runs WHERE pipeline_name = ?",
                (pipeline_name,),
            ).fetchone()[0]
            rows = conn.execute(
                """
                SELECT * FROM pipeline_runs
                WHERE pipeline_name = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (pipeline_name, page_size, offset),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_pipeline_run(r) for r in rows], total

    def find_by_execution_date(
        self, pipeline_name: str, execution_date: date
    ) -> PipelineRun | None:
        """특정 파이프라인의 특정 날짜 실행 조회."""
        conn = self.database.get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM pipeline_runs
                WHERE pipeline_name = ? AND execution_date = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (pipeline_name, execution_date.isoformat()),
            ).fetchone()
        finally:
            conn.close()
        return _row_to_pipeline_run(row) if row else None


class StepRunRepository:
    """step_runs 테이블 CRUD. pipeline_run_id 기반 조회 지원."""

    def __init__(self, database: Database):
        self.database = database

    def create(self, step_run: StepRun) -> StepRun:
        """INSERT. id는 UUID 자동 생성."""
        conn = self.database.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO step_runs
                    (id, pipeline_run_id, step_name, status, started_at,
                     finished_at, records_processed, error_message, retry_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
                """,
                (
                    step_run.id,
                    step_run.pipeline_run_id,
                    step_run.step_name,
                    step_run.status,
                    step_run.started_at.isoformat() if step_run.started_at else None,
                    step_run.finished_at.isoformat() if step_run.finished_at else None,
                    step_run.records_processed,
                    step_run.error_message,
                    step_run.retry_count,
                    step_run.created_at.isoformat() if step_run.created_at else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return step_run

    def update_status(self, step_id: str, status: str, **kwargs) -> None:
        """status 업데이트. kwargs로 finished_at, records_processed,
        error_message, retry_count 등 선택적 필드 업데이트."""
        allowed = {"finished_at", "records_processed", "error_message", "retry_count"}
        sets = ["status = ?"]
        params: list = [status]

        for key, value in kwargs.items():
            if key not in allowed:
                raise ValueError(f"허용되지 않은 필드: {key}")
            if key == "finished_at" and isinstance(value, datetime):
                value = value.isoformat()
            sets.append(f"{key} = ?")
            params.append(value)

        params.append(step_id)
        sql = f"UPDATE step_runs SET {', '.join(sets)} WHERE id = ?"
        conn = self.database.get_connection()
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def find_by_pipeline_run(self, pipeline_run_id: str) -> list[StepRun]:
        """특정 파이프라인 실행의 모든 단계 조회."""
        conn = self.database.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM step_runs WHERE pipeline_run_id = ? ORDER BY created_at",
                (pipeline_run_id,),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_step_run(r) for r in rows]
