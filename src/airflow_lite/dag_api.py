from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Pipeline:
    id: str
    table: str
    source_where_template: str | None = None
    source_bind_params: dict[str, Any] | None = None
    strategy: str = "full"
    schedule: str = "0 2 * * *"
    chunk_size: int | None = None
    columns: list[str] | None = None
    incremental_key: str | None = None

    def to_pipeline_config(self) -> "PipelineConfig":
        from airflow_lite.config.settings import PipelineConfig

        return PipelineConfig(
            name=self.id,
            table=self.table,
            source_where_template=self.source_where_template,
            source_bind_params=self.source_bind_params or {},
            strategy=self.strategy,
            schedule=self.schedule,
            chunk_size=self.chunk_size,
            columns=self.columns,
            incremental_key=self.incremental_key,
        )
