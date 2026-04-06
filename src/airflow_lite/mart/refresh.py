from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from airflow_lite.mart.builder import DuckDBMartBuilder, MartBuildPlan, MartBuildRequest
from airflow_lite.mart.execution import DuckDBMartExecutor, MartBuildResult
from airflow_lite.mart.snapshot import MartSnapshotPromoter
from airflow_lite.mart.validator import DuckDBMartValidator, MartValidationReport


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


@dataclass(frozen=True)
class MartRefreshResult:
    plan: MartRefreshPlan
    build_result: MartBuildResult
    validation_report: MartValidationReport
    promoted: bool = False


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


class MartRefreshExecutor:
    def __init__(
        self,
        builder: DuckDBMartBuilder,
        executor: DuckDBMartExecutor | None = None,
        validator: DuckDBMartValidator | None = None,
        promoter: MartSnapshotPromoter | None = None,
    ):
        self.builder = builder
        self.executor = executor or DuckDBMartExecutor()
        self.validator = validator or DuckDBMartValidator()
        self.promoter = promoter or MartSnapshotPromoter()

    def execute_refresh(self, plan: MartRefreshPlan) -> MartRefreshResult:
        self.builder.layout.ensure_directories(plan.build_plan.paths)
        build_result = self.executor.execute_build(plan.build_plan)
        validation_report = self.validator.validate_build(build_result)

        promoted = False
        if validation_report.is_valid and plan.should_promote:
            self.promoter.promote(plan.build_plan.paths)
            promoted = True

        return MartRefreshResult(
            plan=plan,
            build_result=build_result,
            validation_report=validation_report,
            promoted=promoted,
        )
