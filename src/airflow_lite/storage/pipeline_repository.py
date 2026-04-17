from typing import Optional

from airflow_lite.pipeline_config_validation import coerce_source_query_for_storage
from airflow_lite.storage._helpers import normalize_columns
from airflow_lite.storage.database import Database
from airflow_lite.storage.models import PipelineModel

_SELECT_COLUMNS = """
    name,
    source_table,
    source_where_template,
    source_bind_params,
    strategy,
    schedule,
    chunk_size,
    columns,
    incremental_key
"""


def _row_to_model(row) -> PipelineModel:
    source_where_template, source_bind_params = coerce_source_query_for_storage(
        row["source_where_template"],
        row["source_bind_params"],
        strategy=row["strategy"],
    )
    return PipelineModel(
        name=row["name"],
        table=row["source_table"],
        source_where_template=source_where_template,
        source_bind_params=source_bind_params,
        strategy=row["strategy"],
        schedule=row["schedule"],
        chunk_size=row["chunk_size"],
        columns=row["columns"],
        incremental_key=row["incremental_key"],
    )


def _validated_source_query_fields(model: PipelineModel) -> tuple[str | None, str | None]:
    return coerce_source_query_for_storage(
        model.source_where_template,
        model.source_bind_params,
        strategy=model.strategy,
    )


class PipelineRepository:
    def __init__(self, database: Database):
        self.db = database

    def get(self, name: str) -> Optional[PipelineModel]:
        with self.db.connection() as conn:
            row = conn.execute(
                f"SELECT {_SELECT_COLUMNS} FROM pipeline_configs WHERE name = ?",
                (name,),
            ).fetchone()
            return _row_to_model(row) if row else None

    def list(self) -> list[PipelineModel]:
        with self.db.connection() as conn:
            rows = conn.execute(
                f"SELECT {_SELECT_COLUMNS} FROM pipeline_configs ORDER BY name"
            ).fetchall()
            return [_row_to_model(row) for row in rows]

    def create(self, model: PipelineModel) -> None:
        source_where_template, source_bind_params = _validated_source_query_fields(model)
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_configs
                (
                    name,
                    source_table,
                    source_where_template,
                    source_bind_params,
                    strategy,
                    schedule,
                    chunk_size,
                    columns,
                    incremental_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.name,
                    model.table,
                    source_where_template,
                    source_bind_params,
                    model.strategy,
                    model.schedule,
                    model.chunk_size,
                    normalize_columns(model.columns),
                    model.incremental_key,
                ),
            )
            conn.commit()

    def update(self, model: PipelineModel) -> None:
        source_where_template, source_bind_params = _validated_source_query_fields(model)
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_configs
                SET source_table = ?,
                    source_where_template = ?,
                    source_bind_params = ?,
                    strategy = ?,
                    schedule = ?,
                    chunk_size = ?,
                    columns = ?,
                    incremental_key = ?
                WHERE name = ?
                """,
                (
                    model.table,
                    source_where_template,
                    source_bind_params,
                    model.strategy,
                    model.schedule,
                    model.chunk_size,
                    normalize_columns(model.columns),
                    model.incremental_key,
                    model.name,
                ),
            )
            conn.commit()

    def delete(self, name: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM pipeline_configs WHERE name = ?", (name,))
            conn.commit()
