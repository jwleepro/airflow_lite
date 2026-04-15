from typing import Optional

from airflow_lite.storage._helpers import normalize_columns
from airflow_lite.storage.database import Database
from airflow_lite.storage.models import PipelineModel

_SELECT_COLUMNS = """
    name,
    source_table,
    partition_column,
    strategy,
    schedule,
    chunk_size,
    columns,
    incremental_key
"""


def _row_to_model(row) -> PipelineModel:
    return PipelineModel(
        name=row["name"],
        table=row["source_table"],
        partition_column=row["partition_column"],
        strategy=row["strategy"],
        schedule=row["schedule"],
        chunk_size=row["chunk_size"],
        columns=row["columns"],
        incremental_key=row["incremental_key"],
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
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_configs
                (name, source_table, partition_column, strategy, schedule,
                 chunk_size, columns, incremental_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.name,
                    model.table,
                    model.partition_column,
                    model.strategy,
                    model.schedule,
                    model.chunk_size,
                    normalize_columns(model.columns),
                    model.incremental_key,
                ),
            )
            conn.commit()

    def update(self, model: PipelineModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_configs
                SET source_table = ?,
                    partition_column = ?,
                    strategy = ?,
                    schedule = ?,
                    chunk_size = ?,
                    columns = ?,
                    incremental_key = ?
                WHERE name = ?
                """,
                (
                    model.table,
                    model.partition_column,
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
