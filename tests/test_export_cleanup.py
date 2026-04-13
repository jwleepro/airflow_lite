"""T-033/admin: export cleanup 쿨다운 및 admin ���제 테스트."""
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from airflow_lite.api.analytics_contracts import ExportFormat, ExportJobStatus
from airflow_lite.export.service import (
    AnalyticsExportJobNotFoundError,
    ExportJobRecord,
    FilesystemAnalyticsExportService,
)


@pytest.fixture
def export_service(tmp_path):
    query_service = MagicMock()
    svc = FilesystemAnalyticsExportService(
        root_path=tmp_path,
        query_service=query_service,
        retention_hours=1,
        cleanup_cooldown_seconds=60,
    )
    return svc


def _write_expired_job(svc: FilesystemAnalyticsExportService, job_id: str = "expired-1") -> None:
    now = datetime.now()
    record = ExportJobRecord(
        job_id=job_id,
        dataset="test",
        action_key="export-source-files",
        status=ExportJobStatus.COMPLETED,
        format=ExportFormat.CSV_ZIP,
        created_at=now - timedelta(hours=10),
        updated_at=now - timedelta(hours=10),
        expires_at=now - timedelta(hours=1),
        file_name=f"{job_id}.zip",
        artifact_path=str(svc.artifacts_path / f"{job_id}.zip"),
    )
    svc._write_record(record)


def test_cleanup_expired_removes_expired_jobs(export_service):
    _write_expired_job(export_service, "exp-1")
    assert (export_service.jobs_path / "exp-1.json").exists()
    export_service.cleanup_expired(force=True)
    assert not (export_service.jobs_path / "exp-1.json").exists()


def test_cooldown_prevents_repeated_cleanup(export_service):
    """After a cleanup, subsequent _maybe_cleanup calls within cooldown should not scan."""
    export_service.cleanup_expired(force=True)
    first_cleanup_time = export_service._last_cleanup_at

    # Write an expired job after cleanup
    _write_expired_job(export_service, "exp-2")

    # _maybe_cleanup should be a no-op within cooldown
    export_service._maybe_cleanup()
    assert export_service._last_cleanup_at == first_cleanup_time
    # The expired job should still exist (cleanup was skipped)
    assert (export_service.jobs_path / "exp-2.json").exists()


def test_cooldown_allows_cleanup_after_elapsed(export_service):
    """After cooldown elapses, _maybe_cleanup should run."""
    export_service.cleanup_expired(force=True)
    # Simulate cooldown elapsed
    export_service._last_cleanup_at = datetime.now() - timedelta(seconds=120)

    _write_expired_job(export_service, "exp-3")
    export_service._maybe_cleanup()
    assert not (export_service.jobs_path / "exp-3.json").exists()


# ── Admin delete tests ──────────────────────────────────────────────────────


def _write_active_job(svc, job_id="active-1", status=ExportJobStatus.COMPLETED):
    now = datetime.now()
    record = ExportJobRecord(
        job_id=job_id,
        dataset="test",
        action_key="export-source-files",
        status=status,
        format=ExportFormat.CSV_ZIP,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=24),
        file_name=f"{job_id}.zip",
        artifact_path=str(svc.artifacts_path / f"{job_id}.zip"),
    )
    svc._write_record(record)
    # Create a fake artifact file
    artifact = svc.artifacts_path / f"{job_id}.zip"
    artifact.write_bytes(b"fake")
    return record


def test_delete_job_removes_record_and_artifact(export_service):
    _write_active_job(export_service, "del-1")
    assert (export_service.jobs_path / "del-1.json").exists()
    assert (export_service.artifacts_path / "del-1.zip").exists()

    export_service.delete_job("del-1")

    assert not (export_service.jobs_path / "del-1.json").exists()
    assert not (export_service.artifacts_path / "del-1.zip").exists()


def test_delete_job_not_found_raises(export_service):
    with pytest.raises(AnalyticsExportJobNotFoundError):
        export_service.delete_job("nonexistent")


def test_delete_all_completed(export_service):
    _write_active_job(export_service, "c1", status=ExportJobStatus.COMPLETED)
    _write_active_job(export_service, "c2", status=ExportJobStatus.COMPLETED)
    _write_active_job(export_service, "r1", status=ExportJobStatus.RUNNING)

    count = export_service.delete_all_completed()
    assert count == 2
    assert not (export_service.jobs_path / "c1.json").exists()
    assert not (export_service.jobs_path / "c2.json").exists()
    # Running job should remain
    assert (export_service.jobs_path / "r1.json").exists()


def test_get_job_reads_existing_json_while_update_writes_temp_file(export_service, monkeypatch):
    _write_active_job(export_service, "race-1", status=ExportJobStatus.QUEUED)
    original_write_text = Path.write_text
    write_started = threading.Event()
    allow_write_finish = threading.Event()
    reader_finished = threading.Event()
    observed = {}

    def slow_write_text(self, text, encoding=None, errors=None, newline=None):
        if self.name.startswith("race-1.json") and not write_started.is_set():
            original_write_text(self, "", encoding=encoding, errors=errors, newline=newline)
            write_started.set()
            allow_write_finish.wait(timeout=2)
        return original_write_text(self, text, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", slow_write_text)

    worker = threading.Thread(
        target=export_service._update_record,
        args=("race-1",),
        kwargs={"status": ExportJobStatus.RUNNING},
    )
    worker.start()
    assert write_started.wait(timeout=2)

    def read_job():
        try:
            observed["response"] = export_service.get_job("race-1")
        except Exception as exc:  # pragma: no cover - regression capture
            observed["error"] = exc
        finally:
            reader_finished.set()

    reader = threading.Thread(target=read_job)
    reader.start()
    time.sleep(0.1)

    assert not reader_finished.is_set()

    allow_write_finish.set()
    worker.join(timeout=2)
    reader.join(timeout=2)

    assert "error" not in observed
    assert observed["response"].job_id == "race-1"
    assert observed["response"].status is ExportJobStatus.RUNNING
    assert export_service.get_job("race-1").status is ExportJobStatus.RUNNING
