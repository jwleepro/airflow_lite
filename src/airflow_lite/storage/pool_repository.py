from typing import Optional

from airflow_lite.storage.database import Database
from airflow_lite.storage.models import PoolModel


def _row_to_model(row) -> PoolModel:
    return PoolModel(
        pool_name=row["pool_name"],
        slots=row["slots"],
        description=row["description"],
    )


class PoolRepository:
    def __init__(self, database: Database):
        self.db = database

    def get(self, pool_name: str) -> Optional[PoolModel]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM pools WHERE pool_name = ?", (pool_name,)
            ).fetchone()
            return _row_to_model(row) if row else None

    def list(self) -> list[PoolModel]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM pools ORDER BY pool_name").fetchall()
            return [_row_to_model(row) for row in rows]

    def create(self, model: PoolModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO pools (pool_name, slots, description) VALUES (?, ?, ?)",
                (model.pool_name, model.slots, model.description),
            )
            conn.commit()

    def update(self, model: PoolModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE pools SET slots = ?, description = ? WHERE pool_name = ?",
                (model.slots, model.description, model.pool_name),
            )
            conn.commit()

    def delete(self, pool_name: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM pools WHERE pool_name = ?", (pool_name,))
            conn.commit()
