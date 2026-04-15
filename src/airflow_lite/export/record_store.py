from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Iterator
from uuid import uuid4

from airflow_lite.api.paths import export_download_path
from airflow_lite.query.contracts import (
    ExportFormat,
    ExportJobResponse,
    ExportJobStatus,
)


class AnalyticsExportJobNotFoundError(LookupError):
    pass


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


def unlink_with_retry(
    path: Path, *, attempts: int = 5, delay_seconds: float = 0.05
) -> None:
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


class ExportJobRecordStore:
    """Thread-safe persistence of ExportJobRecord as JSON files on disk."""

    def __init__(self, jobs_path: Path):
        self.jobs_path = jobs_path
        self._lock = RLock()

    def read(self, job_id: str) -> ExportJobRecord:
        with self._lock:
            return self._read_unlocked(job_id)

    def _read_unlocked(self, job_id: str) -> ExportJobRecord:
        job_path = self._path_for(job_id)
        if not job_path.exists():
            raise AnalyticsExportJobNotFoundError(
                f"export job not found: {job_id}"
            )
        return self.read_file(job_path)

    @staticmethod
    def read_file(job_path: Path) -> ExportJobRecord:
        return ExportJobRecord.from_json(job_path.read_text(encoding="utf-8"))

    def write(self, record: ExportJobRecord) -> None:
        with self._lock:
            self._write_unlocked(record)

    def _write_unlocked(self, record: ExportJobRecord) -> None:
        job_path = self._path_for(record.job_id)
        temp_path = job_path.with_name(f"{job_path.name}.{uuid4().hex}.tmp")
        temp_path.write_text(record.to_json(), encoding="utf-8")
        temp_path.replace(job_path)

    def update(self, job_id: str, **updates) -> None:
        with self._lock:
            record = self._read_unlocked(job_id)
            updates.setdefault("updated_at", datetime.now())
            self._write_unlocked(
                ExportJobRecord(**{**record.__dict__, **updates})
            )

    def iter_records(self) -> Iterator[tuple[Path, ExportJobRecord]]:
        """Yield (job_file, record) for each persisted job under the lock."""
        with self._lock:
            for job_file in self.jobs_path.glob("*.json"):
                yield job_file, self.read_file(job_file)

    def _path_for(self, job_id: str) -> Path:
        return self.jobs_path / f"{job_id}.json"
