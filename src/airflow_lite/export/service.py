from __future__ import annotations

import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as papq

from airflow_lite.query.contracts import (
    ExportCreateRequest,
    ExportCreateResponse,
    ExportFormat,
    ExportJobResponse,
    ExportJobStatus,
)
from airflow_lite.api.paths import export_download_path
from airflow_lite.export.protocols import ExportQueryProvider
from airflow_lite.query.service import AnalyticsExportPlan


class AnalyticsExportJobNotFoundError(LookupError):
    pass


class AnalyticsExportNotReadyError(RuntimeError):
    pass


# ZIP 압축 방식 매핑 상수
ZIP_COMPRESSION_MAP: dict[str, int] = {
    "deflated": zipfile.ZIP_DEFLATED,
    "stored": zipfile.ZIP_STORED,
}


@dataclass
class ExportJobRecord:
    job_id: str
    dataset: str
    action_key: str
    status: ExportJobStatus
    format: ExportFormat
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    file_name: str
    artifact_path: str
    row_count: int | None = None
    error_message: str | None = None

    def to_response(self) -> ExportJobResponse:
        download_endpoint = None
        if self.status is ExportJobStatus.COMPLETED:
            download_endpoint = export_download_path(self.job_id)

        return ExportJobResponse(
            job_id=self.job_id,
            dataset=self.dataset,
            action_key=self.action_key,
            status=self.status,
            format=self.format,
            created_at=self.created_at,
            updated_at=self.updated_at,
            expires_at=self.expires_at,
            row_count=self.row_count,
            file_name=self.file_name,
            download_endpoint=download_endpoint,
            error_message=self.error_message,
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "job_id": self.job_id,
                "dataset": self.dataset,
                "action_key": self.action_key,
                "status": self.status.value,
                "format": self.format.value,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "expires_at": self.expires_at.isoformat(),
                "file_name": self.file_name,
                "artifact_path": self.artifact_path,
                "row_count": self.row_count,
                "error_message": self.error_message,
            },
            ensure_ascii=True,
            indent=2,
        )

    @classmethod
    def from_json(cls, payload: str) -> "ExportJobRecord":
        data = json.loads(payload)
        return cls(
            job_id=data["job_id"],
            dataset=data["dataset"],
            action_key=data["action_key"],
            status=ExportJobStatus(data["status"]),
            format=ExportFormat(data["format"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            file_name=data["file_name"],
            artifact_path=data["artifact_path"],
            row_count=data.get("row_count"),
            error_message=data.get("error_message"),
        )


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
        self._parquet_compression = parquet_compression
        self._zip_compression = self._resolve_zip_compression(zip_compression)
        self._record_lock = RLock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="analytics-export")
        self.jobs_path.mkdir(parents=True, exist_ok=True)
        self.artifacts_path.mkdir(parents=True, exist_ok=True)
        self.cleanup_expired(force=True)

    def create_export(self, request: ExportCreateRequest) -> ExportCreateResponse:
        self._maybe_cleanup()
        plan = self.query_service.build_export_plan(request)
        now = datetime.now()
        suffix = "zip" if request.format is ExportFormat.CSV_ZIP else "parquet"
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
        self._write_record(record)
        self.executor.submit(self._run_export, record.job_id, plan)
        return ExportCreateResponse(
            job_id=record.job_id,
            status=record.status,
            format=record.format,
            created_at=record.created_at,
        )

    def get_job(self, job_id: str) -> ExportJobResponse:
        self._maybe_cleanup()
        return self._read_record(job_id).to_response()

    def list_jobs(self, *, dataset: str | None = None, limit: int = 50) -> list[ExportJobResponse]:
        self._maybe_cleanup()
        records: list[ExportJobRecord] = []
        with self._record_lock:
            for job_file in self.jobs_path.glob("*.json"):
                record = self._read_record_file(job_file)
                if dataset and record.dataset != dataset:
                    continue
                records.append(record)

        records.sort(key=lambda item: (item.created_at, item.job_id), reverse=True)
        return [record.to_response() for record in records[:limit]]

    def get_download_path(self, job_id: str) -> tuple[Path, str]:
        self._maybe_cleanup()
        record = self._read_record(job_id)
        artifact_path = Path(record.artifact_path)
        if record.status is not ExportJobStatus.COMPLETED or not artifact_path.exists():
            raise AnalyticsExportNotReadyError(f"export job is not ready: {job_id}")
        return artifact_path, record.file_name

    @staticmethod
    def _unlink_with_retry(path: Path, *, attempts: int = 5, delay_seconds: float = 0.05) -> None:
        """Best-effort unlink for Windows file-handle lag."""
        for attempt in range(attempts):
            try:
                path.unlink()
                return
            except FileNotFoundError:
                return
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                time.sleep(delay_seconds)

    def delete_job(self, job_id: str) -> None:
        """Admin action: delete a specific export job and its artifact."""
        record = self._read_record(job_id)
        artifact_path = Path(record.artifact_path)
        if artifact_path.exists():
            self._unlink_with_retry(artifact_path)
        job_path = self.jobs_path / f"{job_id}.json"
        self._unlink_with_retry(job_path)

    def delete_all_completed(self) -> int:
        """Admin action: delete all completed export jobs. Returns count deleted."""
        count = 0
        with self._record_lock:
            for job_file in self.jobs_path.glob("*.json"):
                record = self._read_record_file(job_file)
                if record.status is not ExportJobStatus.COMPLETED:
                    continue
                artifact_path = Path(record.artifact_path)
                if artifact_path.exists():
                    self._unlink_with_retry(artifact_path)
                self._unlink_with_retry(job_file)
                count += 1
        return count

    def _maybe_cleanup(self) -> None:
        """Run cleanup only if cooldown has elapsed."""
        now = datetime.now()
        if (
            self._last_cleanup_at is not None
            and (now - self._last_cleanup_at).total_seconds() < self._cleanup_cooldown_seconds
        ):
            return
        self.cleanup_expired(force=True)

    def cleanup_expired(self, *, force: bool = False) -> None:
        if not force:
            self._maybe_cleanup()
            return
        now = datetime.now()
        self._last_cleanup_at = now
        with self._record_lock:
            for job_file in self.jobs_path.glob("*.json"):
                record = self._read_record_file(job_file)
                if record.expires_at > now:
                    continue
                artifact_path = Path(record.artifact_path)
                if artifact_path.exists():
                    artifact_path.unlink()
                job_file.unlink()

    def _run_export(self, job_id: str, plan: AnalyticsExportPlan) -> None:
        self._update_record(job_id, status=ExportJobStatus.RUNNING)

        try:
            row_count = self._write_artifact(plan, Path(self._read_record(job_id).artifact_path))
        except Exception as exc:
            self._update_record(job_id, status=ExportJobStatus.FAILED, error_message=str(exc))
            return

        self._update_record(job_id, status=ExportJobStatus.COMPLETED, row_count=row_count)

    def _write_artifact(self, plan: AnalyticsExportPlan, artifact_path: Path) -> int:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with self.query_service.execute_export_batches(
            plan.sql, plan.params, rows_per_batch=self._rows_per_batch
        ) as reader:
            if plan.format is ExportFormat.PARQUET:
                return self._write_parquet(artifact_path, reader)
            if plan.format is ExportFormat.CSV_ZIP:
                return self._write_csv_zip(artifact_path, reader)
        raise ValueError(f"unsupported export format: {plan.format.value}")

    def _write_parquet(self, artifact_path: Path, reader) -> int:
        row_count = 0
        with papq.ParquetWriter(
            str(artifact_path),
            reader.schema,
            compression=self._parquet_compression,
        ) as writer:
            for batch in reader:
                writer.write_batch(batch)
                row_count += batch.num_rows
        return row_count

    def _write_csv_zip(self, artifact_path: Path, reader) -> int:
        row_count = 0
        csv_name = f"{artifact_path.stem}.csv"
        csv_path = artifact_path.with_suffix(".csv")
        with pa.OSFile(str(csv_path), "wb") as sink:
            with pacsv.CSVWriter(sink, reader.schema) as writer:
                for batch in reader:
                    writer.write_batch(batch)
                    row_count += batch.num_rows

        with zipfile.ZipFile(artifact_path, "w", compression=self._zip_compression) as archive:
            archive.write(csv_path, arcname=csv_name)

        csv_path.unlink()
        return row_count

    @staticmethod
    def _resolve_zip_compression(zip_compression: str) -> int:
        """ZIP 압축 방식을 상수 매핑에서 조회하여 반환."""
        try:
            return ZIP_COMPRESSION_MAP[zip_compression.lower()]
        except KeyError as exc:
            raise ValueError(f"unsupported zip compression: {zip_compression}") from exc

    def _update_record(self, job_id: str, **updates) -> None:
        with self._record_lock:
            record = self._read_record_unlocked(job_id)
            updates.setdefault("updated_at", datetime.now())
            self._write_record_unlocked(ExportJobRecord(**{**record.__dict__, **updates}))

    def _read_record(self, job_id: str) -> ExportJobRecord:
        with self._record_lock:
            return self._read_record_unlocked(job_id)

    def _read_record_unlocked(self, job_id: str) -> ExportJobRecord:
        job_path = self.jobs_path / f"{job_id}.json"
        if not job_path.exists():
            raise AnalyticsExportJobNotFoundError(f"export job not found: {job_id}")
        return self._read_record_file(job_path)

    def _write_record(self, record: ExportJobRecord) -> None:
        with self._record_lock:
            self._write_record_unlocked(record)

    def _read_record_file(self, job_path: Path) -> ExportJobRecord:
        return ExportJobRecord.from_json(job_path.read_text(encoding="utf-8"))

    def _write_record_unlocked(self, record: ExportJobRecord) -> None:
        job_path = self.jobs_path / f"{record.job_id}.json"
        temp_path = job_path.with_name(f"{job_path.name}.{uuid4().hex}.tmp")
        temp_path.write_text(record.to_json(), encoding="utf-8")
        temp_path.replace(job_path)
