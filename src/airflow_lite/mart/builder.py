from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from airflow_lite.mart.snapshot import MartSnapshotLayout, SnapshotPaths


@dataclass(frozen=True)
class MartBuildRequest:
    dataset_name: str
    source_paths: tuple[Path, ...]
    build_id: str
    full_refresh: bool = True


@dataclass(frozen=True)
class MartBuildPlan:
    request: MartBuildRequest
    snapshot_name: str
    paths: SnapshotPaths


class DuckDBMartBuilder:
    """Prepare deterministic filesystem plans for a future DuckDB mart build."""

    def __init__(self, layout: MartSnapshotLayout):
        self.layout = layout

    def plan_build(self, request: MartBuildRequest) -> MartBuildPlan:
        if not request.dataset_name.strip():
            raise ValueError("dataset_name must not be blank")
        if not request.source_paths:
            raise ValueError("source_paths must not be empty")

        snapshot_name = f"{request.dataset_name}-{request.build_id}"
        paths = self.layout.plan_paths(
            build_id=request.build_id,
            snapshot_name=snapshot_name,
        )
        return MartBuildPlan(
            request=request,
            snapshot_name=snapshot_name,
            paths=paths,
        )

    def prepare_build(self, request: MartBuildRequest) -> MartBuildPlan:
        plan = self.plan_build(request)
        self.layout.ensure_directories(plan.paths)
        return plan
