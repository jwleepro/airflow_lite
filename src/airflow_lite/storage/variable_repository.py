from typing import Optional

from airflow_lite.storage.database import Database
from airflow_lite.storage.models import VariableModel


def _row_to_model(row) -> VariableModel:
    return VariableModel(
        key=row["key"],
        val=row["val"],
        description=row["description"],
    )


class VariableRepository:
    def __init__(self, database: Database):
        self.db = database

    def get(self, key: str) -> Optional[VariableModel]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM variables WHERE key = ?", (key,)
            ).fetchone()
            return _row_to_model(row) if row else None

    def list(self) -> list[VariableModel]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM variables ORDER BY key").fetchall()
            return [_row_to_model(row) for row in rows]

    def create(self, model: VariableModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO variables (key, val, description) VALUES (?, ?, ?)",
                (model.key, model.val, model.description),
            )
            conn.commit()

    def update(self, model: VariableModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE variables SET val = ?, description = ? WHERE key = ?",
                (model.val, model.description, model.key),
            )
            conn.commit()

    def delete(self, key: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM variables WHERE key = ?", (key,))
            conn.commit()
