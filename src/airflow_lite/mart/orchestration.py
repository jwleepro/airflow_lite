from __future__ import annotations

import logging
import re
from pathlib import Path

from airflow_lite.engine.stage import StageContext
from airflow_lite.mart.refresh import (
    MartRefreshMode,
    MartRefreshPlan,
    MartRefreshPlanner,
    MartRefreshRequest,
)

logger = logging.getLogger("airflow_lite.mart.orchestration")


class MartRefreshCoordinator:
    """Translate successful raw pipeline runs into mart refresh plans."""

    def __init__(
        self,
        planner: MartRefreshPlanner,
        parquet_root: Path,
        pipeline_datasets: dict[str, str] | None = None,
    ):
        self.planner = planner
        self.parquet_root = parquet_root
        self.pipeline_datasets = pipeline_datasets or {}

    def plan_refresh(self, context: StageContext) -> MartRefreshPlan | None:
        if context.table_config is None:
            return None

        source_paths = self._discover_source_paths(context)
        if not source_paths:
            logger.info(
                "Mart refresh skipped because no parquet files were found: pipeline=%s execution_date=%s",
                context.pipeline_name,
                context.execution_date.isoformat(),
            )
            return None

        request = MartRefreshRequest(
            dataset_name=self._resolve_dataset_name(context),
            source_paths=source_paths,
            build_id=self._build_id(context),
            mode=self._resolve_mode(context),
        )
        return self.planner.plan_refresh(request)

    def _resolve_dataset_name(self, context: StageContext) -> str:
        return self.pipeline_datasets.get(context.pipeline_name, context.pipeline_name)

    def _discover_source_paths(self, context: StageContext) -> tuple[Path, ...]:
        table_name = context.table_config.table
        partition_dir = (
            self.parquet_root
            / table_name
            / f"year={context.execution_date.year:04d}"
            / f"month={context.execution_date.month:02d}"
        )
        if not partition_dir.exists():
            return ()
        return tuple(sorted(path for path in partition_dir.glob("*.parquet") if path.is_file()))

    def _build_id(self, context: StageContext) -> str:
        safe_run_id = re.sub(r"[^0-9A-Za-z-]+", "-", context.run_id).strip("-") or "run"
        return f"{context.execution_date:%Y%m%d}-{safe_run_id}"

    def _resolve_mode(self, context: StageContext) -> MartRefreshMode:
        if context.trigger_type == "backfill":
            return MartRefreshMode.BACKFILL

        strategy = getattr(context.table_config, "strategy", "").lower()
        if strategy == "incremental":
            return MartRefreshMode.INCREMENTAL
        return MartRefreshMode.FULL
