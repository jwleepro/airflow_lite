from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from airflow_lite.config.settings import PipelineConfig
from airflow_lite.engine.stage import StageContext
from airflow_lite.mart import (
    DuckDBMartBuilder,
    MartRefreshCoordinator,
    MartRefreshMode,
    MartRefreshPlanner,
    MartRefreshRequest,
    MartSnapshotLayout,
    MartValidationReport,
)
from airflow_lite.mart.builder import MartBuildRequest


def test_snapshot_layout_plans_expected_paths() -> None:
    layout = MartSnapshotLayout(root_dir=Path("mart-root"))

    paths = layout.plan_paths(build_id="20260331-010000", snapshot_name="ops-20260331-010000")

    assert paths.current_db_path == Path("mart-root") / "current" / "analytics.duckdb"
    assert paths.staging_db_path == Path("mart-root") / "staging" / "20260331-010000" / "analytics.duckdb"
    assert paths.snapshot_db_path == Path("mart-root") / "snapshots" / "ops-20260331-010000" / "analytics.duckdb"


def test_builder_rejects_empty_sources() -> None:
    layout = MartSnapshotLayout(root_dir=Path("mart-root"))
    builder = DuckDBMartBuilder(layout)

    with pytest.raises(ValueError, match="source_paths must not be empty"):
        builder.plan_build(
            MartBuildRequest(
                dataset_name="ops",
                source_paths=(),
                build_id="20260331-010000",
            )
        )


def test_prepare_build_calls_layout_directory_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    layout = MartSnapshotLayout(root_dir=Path("mart-root"))
    builder = DuckDBMartBuilder(layout)
    captured_paths = []

    def fake_ensure_directories(self, paths) -> None:
        captured_paths.append(paths)

    monkeypatch.setattr(MartSnapshotLayout, "ensure_directories", fake_ensure_directories)

    plan = builder.prepare_build(
        MartBuildRequest(
            dataset_name="ops",
            source_paths=(Path("raw") / "part-0001.parquet",),
            build_id="20260331-010000",
        )
    )

    assert captured_paths == [plan.paths]


def test_refresh_planner_maps_mode_to_build_request() -> None:
    layout = MartSnapshotLayout(root_dir=Path("mart-root"))
    builder = DuckDBMartBuilder(layout)
    planner = MartRefreshPlanner(builder)

    plan = planner.plan_refresh(
        MartRefreshRequest(
            dataset_name="ops",
            source_paths=(Path("raw") / "part-0001.parquet",),
            build_id="20260331-010000",
            mode=MartRefreshMode.INCREMENTAL,
        )
    )

    assert plan.request.mode == MartRefreshMode.INCREMENTAL
    assert plan.build_plan.request.full_refresh is False
    assert plan.build_plan.snapshot_name == "ops-20260331-010000"


def test_validation_report_only_fails_on_error() -> None:
    report = MartValidationReport()
    report.add_issue("warning", "row count changed")

    assert report.is_valid is True

    report.add_issue("error", "missing required summary table")

    assert report.is_valid is False


def test_refresh_coordinator_discovers_partition_files_and_maps_backfill_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_a = Path("parquet") / "OPS_TABLE_2026_03.parquet"
    file_b = Path("parquet") / "OPS_TABLE_2026_03.part00001.parquet"

    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(Path, "glob", lambda self, pattern: iter([file_a, file_b]))
    monkeypatch.setattr(Path, "is_file", lambda self: True)

    layout = MartSnapshotLayout(root_dir=Path("mart-root"))
    planner = MartRefreshPlanner(DuckDBMartBuilder(layout))
    coordinator = MartRefreshCoordinator(
        planner=planner,
        parquet_root=Path("parquet-root"),
        pipeline_datasets={"ops_pipe": "ops_dataset"},
    )
    context = StageContext(
        pipeline_name="ops_pipe",
        execution_date=date(2026, 3, 1),
        table_config=PipelineConfig(
            name="ops_pipe",
            table="OPS_TABLE",
            partition_column="LOG_DATE",
            strategy="full",
            schedule="0 2 * * *",
        ),
        run_id="run-001",
        chunk_size=10000,
        trigger_type="backfill",
    )

    plan = coordinator.plan_refresh(context)

    assert plan is not None
    assert plan.request.dataset_name == "ops_dataset"
    assert plan.request.mode == MartRefreshMode.BACKFILL
    assert plan.request.source_paths == (file_a, file_b)
    assert plan.build_plan.snapshot_name == "ops_dataset-20260301-run-001"


def test_refresh_coordinator_skips_when_partition_has_no_parquet_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)

    layout = MartSnapshotLayout(root_dir=Path("mart-root"))
    planner = MartRefreshPlanner(DuckDBMartBuilder(layout))
    coordinator = MartRefreshCoordinator(planner=planner, parquet_root=Path("parquet-root"))
    context = StageContext(
        pipeline_name="ops_pipe",
        execution_date=date(2026, 3, 1),
        table_config=PipelineConfig(
            name="ops_pipe",
            table="OPS_TABLE",
            partition_column="LOG_DATE",
            strategy="incremental",
            schedule="0 2 * * *",
            incremental_key="UPDATED_AT",
        ),
        run_id="run-001",
        chunk_size=10000,
    )

    assert coordinator.plan_refresh(context) is None
