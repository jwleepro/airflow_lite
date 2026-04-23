import pytest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from airflow_lite.engine.backfill import BackfillManager
from airflow_lite.storage.models import PipelineRun


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_runner():
    runner = MagicMock()
    runner.run.return_value = PipelineRun(
        pipeline_name="test_pipeline",
        execution_date=date(2026, 1, 1),
        status="success",
    )
    return runner


@pytest.fixture
def manager(mock_runner, tmp_path):
    return BackfillManager(
        pipeline_runner=mock_runner,
        parquet_base_path=str(tmp_path),
    )


def _make_parquet_file(base_path: Path, table_name: str, year: int, month: int) -> Path:
    """테스트용 더미 parquet 파일 생성."""
    parquet_dir = base_path / table_name / f"year={year:04d}" / f"month={month:02d}"
    parquet_dir.mkdir(parents=True, exist_ok=True)
    parquet_file = parquet_dir / f"{table_name}_{year:04d}_{month:02d}.parquet"
    parquet_file.write_bytes(b"dummy parquet content")
    return parquet_file


# ── _split_into_months ────────────────────────────────────────────────────────

def test_split_same_month(manager):
    result = manager._split_into_months(date(2026, 3, 1), date(2026, 3, 31))
    assert result == [date(2026, 3, 1)]


def test_split_same_month_mid_range(manager):
    result = manager._split_into_months(date(2026, 3, 10), date(2026, 3, 25))
    assert result == [date(2026, 3, 1)]


def test_split_multiple_months(manager):
    result = manager._split_into_months(date(2026, 1, 15), date(2026, 4, 10))
    assert result == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
    ]


def test_split_year_boundary(manager):
    result = manager._split_into_months(date(2025, 11, 1), date(2026, 2, 28))
    assert result == [
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]


def test_split_single_day(manager):
    result = manager._split_into_months(date(2026, 6, 15), date(2026, 6, 15))
    assert result == [date(2026, 6, 1)]


def test_split_returns_first_day_of_each_month(manager):
    result = manager._split_into_months(date(2026, 1, 31), date(2026, 3, 1))
    assert all(d.day == 1 for d in result)


# ── backup_existing ───────────────────────────────────────────────────────────

def test_backup_existing_creates_bak_file(manager, tmp_path):
    parquet_file = _make_parquet_file(tmp_path, "MY_TABLE", 2026, 1)

    bak_path = manager.backup_existing("MY_TABLE", 2026, 1)

    assert bak_path is not None
    assert bak_path.exists()
    assert bak_path.suffix == ".bak"
    assert str(bak_path).endswith(".parquet.bak")
    assert not parquet_file.exists()


def test_backup_existing_returns_none_when_no_file(manager):
    result = manager.backup_existing("NONEXISTENT_TABLE", 2026, 1)
    assert result is None


def test_backup_existing_bak_path_is_correct(manager, tmp_path):
    _make_parquet_file(tmp_path, "MY_TABLE", 2026, 3)

    bak_path = manager.backup_existing("MY_TABLE", 2026, 3)

    expected = (
        tmp_path / "MY_TABLE" / "year=2026" / "month=03" / "MY_TABLE_2026_03.parquet.bak"
    )
    assert bak_path == expected


# ── remove_backup ─────────────────────────────────────────────────────────────

def test_remove_backup_deletes_bak_file(manager, tmp_path):
    _make_parquet_file(tmp_path, "MY_TABLE", 2026, 2)
    bak_path = manager.backup_existing("MY_TABLE", 2026, 2)
    assert bak_path.exists()

    manager.remove_backup(bak_path)

    assert not bak_path.exists()


def test_remove_backup_with_none_does_not_raise(manager):
    manager.remove_backup(None)  # 예외 없이 통과해야 함


def test_remove_backup_with_nonexistent_path_does_not_raise(manager, tmp_path):
    fake_path = tmp_path / "nonexistent.parquet.bak"
    manager.remove_backup(fake_path)  # 예외 없이 통과해야 함


# ── restore_backup ────────────────────────────────────────────────────────────

def test_restore_backup_restores_original(manager, tmp_path):
    parquet_file = _make_parquet_file(tmp_path, "MY_TABLE", 2026, 4)
    bak_path = manager.backup_existing("MY_TABLE", 2026, 4)
    assert not parquet_file.exists()
    assert bak_path.exists()

    manager.restore_backup(bak_path)

    assert parquet_file.exists()
    assert not bak_path.exists()


def test_restore_backup_with_none_does_not_raise(manager):
    manager.restore_backup(None)


def test_restore_backup_original_content_preserved(manager, tmp_path):
    original_content = b"original parquet data"
    parquet_file = _make_parquet_file(tmp_path, "MY_TABLE", 2026, 5)
    parquet_file.write_bytes(original_content)

    bak_path = manager.backup_existing("MY_TABLE", 2026, 5)
    manager.restore_backup(bak_path)

    restored_file = (
        tmp_path / "MY_TABLE" / "year=2026" / "month=05" / "MY_TABLE_2026_05.parquet"
    )
    assert restored_file.read_bytes() == original_content


# ── run_backfill ──────────────────────────────────────────────────────────────

def test_run_backfill_returns_list_of_runs(manager, mock_runner):
    results = manager.run_backfill("test_pipeline", date(2026, 1, 1), date(2026, 3, 31))

    assert len(results) == 3
    assert mock_runner.run.call_count == 3


def test_run_backfill_calls_runner_with_correct_dates(manager, mock_runner):
    manager.run_backfill("test_pipeline", date(2026, 1, 15), date(2026, 3, 10))

    calls = mock_runner.run.call_args_list
    execution_dates = [c.kwargs["execution_date"] for c in calls]
    assert execution_dates == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]


def test_run_backfill_uses_backfill_trigger_type(manager, mock_runner):
    manager.run_backfill("test_pipeline", date(2026, 1, 1), date(2026, 1, 31))

    call_kwargs = mock_runner.run.call_args_list[0].kwargs
    assert call_kwargs["trigger_type"] == "backfill"
    assert call_kwargs["force_rerun"] is False


def test_run_backfill_single_month(manager, mock_runner):
    results = manager.run_backfill("test_pipeline", date(2026, 6, 10), date(2026, 6, 20))

    assert len(results) == 1
    mock_runner.run.assert_called_once_with(
        execution_date=date(2026, 6, 1),
        trigger_type="backfill",
        force_rerun=False,
    )


def test_run_backfill_returns_runner_results(manager, mock_runner):
    fake_run = PipelineRun(
        pipeline_name="test_pipeline",
        execution_date=date(2026, 1, 1),
        status="success",
    )
    mock_runner.run.return_value = fake_run

    results = manager.run_backfill("test_pipeline", date(2026, 1, 1), date(2026, 1, 31))

    assert results[0] is fake_run


def test_run_backfill_can_disable_force_rerun(manager, mock_runner):
    manager.run_backfill(
        "test_pipeline",
        date(2026, 1, 1),
        date(2026, 1, 31),
        force_rerun=False,
    )

    assert mock_runner.run.call_args.kwargs["force_rerun"] is False


def test_run_backfill_rejects_invalid_date_range(manager):
    with pytest.raises(ValueError, match="end_date"):
        manager.run_backfill("test_pipeline", date(2026, 2, 1), date(2026, 1, 31))
