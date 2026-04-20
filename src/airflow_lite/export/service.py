from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from airflow_lite.export.protocols import ExportQueryProvider
from airflow_lite.export.record_store import (
    AnalyticsExportJobNotFoundError,
    ExportJobRecord,
    ExportJobRecordStore,
    unlink_with_retry,
)
from airflow_lite.export.writers import build_export_writers
from airflow_lite.query.contracts import (
    ExportCreateRequest,
    ExportCreateResponse,
    ExportFormat,
    ExportJobResponse,
    ExportJobStatus,
)
from airflow_lite.logging_config.decorators import log_execution
from airflow_lite.query.service import AnalyticsExportPlan

logger = logging.getLogger("airflow_lite.export.service")

FILE_SUFFIX_BY_FORMAT = {
    ExportFormat.CSV_ZIP: "zip",
    ExportFormat.PARQUET: "parquet",
    ExportFormat.XLSX: "xlsx",
}


class AnalyticsExportNotReadyError(RuntimeError):
    pass


class FilesystemAnalyticsExportService:
    """Persist export jobs on disk and execute exports in background threads."""

    def __init__(
        self,
        root_path: str | Path,
        query_service: ExportQueryProvider,
        retention_hours: int = 72,
        max_workers: int = 2,
        cleanup_cooldown_seconds: int = 300,
        rows_per_batch: int = 10_000,
        parquet_compression: str = "snappy",
        zip_compression: str = "deflated",
    ):
        self.root_path = Path(root_path)
        self.jobs_path = self.root_path / "jobs"
        self.artifacts_path = self.root_path / "artifacts"
        self.query_service = query_service
        self.retention_hours = retention_hours
        self._cleanup_cooldown_seconds = cleanup_cooldown_seconds
        self._last_cleanup_at: datetime | None = None
        self._rows_per_batch = rows_per_batch
        self._writers = build_export_writers(
            parquet_compression=parquet_compression,
            zip_compression=zip_compression,
        )
        self.jobs_path.mkdir(parents=True, exist_ok=True)
        self.artifacts_path.mkdir(parents=True, exist_ok=True)
        self._records = ExportJobRecordStore(self.jobs_path)
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="analytics-export"
        )
        self.cleanup_expired(force=True)

    # --- Public API ---
    @log_execution(log_args=True, level=logging.INFO)
    def create_export(self, request: ExportCreateRequest) -> ExportCreateResponse:
        self._maybe_cleanup()
        plan = self.query_service.build_export_plan(request)
        now = datetime.now()
        suffix = FILE_SUFFIX_BY_FORMAT.get(request.format)
        if suffix is None:
            raise ValueError(f"unsupported export format: {request.format.value}")
        job_id = uuid4().hex
        file_name = f"{plan.file_stem}-{job_id[:8]}.{suffix}"
        record = ExportJobRecord(
            job_id=job_id,
            dataset=request.dataset,
            action_key=request.action_key,
            status=ExportJobStatus.QUEUED,
            format=request.format,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=self.retention_hours),
            file_name=file_name,
            artifact_path=str(self.artifacts_path / file_name),
        )
        self._records.write(record)
        self.executor.submit(self._run_export, record.job_id, plan)
        return ExportCreateResponse(
            job_id=record.job_id,
            status=record.status,
            format=record.format,
            created_at=record.created_at,
        )

    @log_execution(log_args=True, level=logging.DEBUG)
    def get_job(self, job_id: str) -> ExportJobResponse:
        self._maybe_cleanup()
        return self._records.read(job_id).to_response()

    @log_execution(level=logging.DEBUG)
    def list_jobs(
        self, *, dataset: str | None = None, limit: int = 50
    ) -> list[ExportJobResponse]:
        self._maybe_cleanup()
        records = [
            record
            for _, record in self._records.iter_records()
            if dataset is None or record.dataset == dataset
        ]
        records.sort(key=lambda item: (item.created_at, item.job_id), reverse=True)
        return [record.to_response() for record in records[:limit]]

    @log_execution(log_args=True, level=logging.INFO)
    def get_download_path(self, job_id: str) -> tuple[Path, str]:
        self._maybe_cleanup()
        record = self._records.read(job_id)
        artifact_path = Path(record.artifact_path)
        if record.status is not ExportJobStatus.COMPLETED or not artifact_path.exists():
            raise AnalyticsExportNotReadyError(f"export job is not ready: {job_id}")
        return artifact_path, record.file_name

    @log_execution(log_args=True, level=logging.INFO)
    def delete_job(self, job_id: str) -> None:
        """Admin action: delete a specific export job and its artifact."""
        record = self._records.read(job_id)
        artifact_path = Path(record.artifact_path)
        if artifact_path.exists():
            unlink_with_retry(artifact_path)
        unlink_with_retry(self.jobs_path / f"{job_id}.json")

    @log_execution(level=logging.INFO)
    def delete_all_completed(self) -> int:
        """Admin action: delete all completed export jobs. Returns count deleted."""
        count = 0
        for job_file, record in self._records.iter_records():
            if record.status is not ExportJobStatus.COMPLETED:
                continue
            artifact_path = Path(record.artifact_path)
            if artifact_path.exists():
                unlink_with_retry(artifact_path)
            unlink_with_retry(job_file)
            count += 1
        return count

    def cleanup_expired(self, *, force: bool = False) -> None:
        if not force:
            self._maybe_cleanup()
            return
        now = datetime.now()
        self._last_cleanup_at = now
        for job_file, record in self._records.iter_records():
            if record.expires_at > now:
                continue
            artifact_path = Path(record.artifact_path)
            if artifact_path.exists():
                unlink_with_retry(artifact_path)
            unlink_with_retry(job_file)

    # --- Internals ---
    def _maybe_cleanup(self) -> None:
        """Run cleanup only if cooldown has elapsed."""
        now = datetime.now()
        if (
            self._last_cleanup_at is not None
            and (now - self._last_cleanup_at).total_seconds()
            < self._cleanup_cooldown_seconds
        ):
            return
        self.cleanup_expired(force=True)

    def _run_export(self, job_id: str, plan: AnalyticsExportPlan) -> None:
        self._update_record(job_id, status=ExportJobStatus.RUNNING)
        try:
            row_count = self._write_artifact(
                plan, Path(self._read_record(job_id).artifact_path)
            )
        except Exception as exc:
            self._update_record(
                job_id, status=ExportJobStatus.FAILED, error_message=str(exc)
            )
            return
        self._update_record(
            job_id, status=ExportJobStatus.COMPLETED, row_count=row_count
        )

    def _write_artifact(
        self, plan: AnalyticsExportPlan, artifact_path: Path
    ) -> int:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        writer = self._writers.get(plan.format)
        if writer is None:
            raise ValueError(f"unsupported export format: {plan.format.value}")
        with self.query_service.execute_export_batches(
            plan.sql, plan.params, rows_per_batch=self._rows_per_batch
        ) as reader:
            return writer.write(artifact_path, reader)

    # --- Thin pass-throughs kept for backward compat with tests ---
    def _read_record(self, job_id: str) -> ExportJobRecord:
        return self._records.read(job_id)

    def _write_record(self, record: ExportJobRecord) -> None:
        self._records.write(record)

    def _update_record(self, job_id: str, **updates) -> None:
        self._records.update(job_id, **updates)


# Backward-compat re-exports (tests import ExportJobRecord from this module)
__all__ = [
    "AnalyticsExportJobNotFoundError",
    "AnalyticsExportNotReadyError",
    "ExportJobRecord",
    "FilesystemAnalyticsExportService",
]
