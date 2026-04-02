from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from airflow_lite.mart.builder import DuckDBMartBuilder, MartBuildPlan, MartBuildRequest


class MartRefreshMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    BACKFILL = "backfill"


@dataclass(frozen=True)
class MartRefreshRequest:
    dataset_name: str
    source_paths: tuple[Path, ...]
    build_id: str
    mode: MartRefreshMode = MartRefreshMode.FULL


@dataclass(frozen=True)
class MartRefreshPlan:
    request: MartRefreshRequest
    build_plan: MartBuildPlan
    should_promote: bool = True


class MartRefreshPlanner:
    def __init__(self, builder: DuckDBMartBuilder):
        self.builder = builder

    def plan_refresh(self, request: MartRefreshRequest) -> MartRefreshPlan:
        build_request = MartBuildRequest(
            dataset_name=request.dataset_name,
            source_paths=request.source_paths,
            build_id=request.build_id,
            full_refresh=request.mode == MartRefreshMode.FULL,
        )
        build_plan = self.builder.plan_build(build_request)
        return MartRefreshPlan(
            request=request,
            build_plan=build_plan,
            should_promote=True,
        )
