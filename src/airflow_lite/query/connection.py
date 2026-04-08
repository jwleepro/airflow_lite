from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path


class DuckDBConnectionManager:
    """DuckDB 커넥션 생명주기 관리."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    @contextmanager
    def connect(self, *, read_only: bool = True):
        import duckdb

        connection = duckdb.connect(str(self.database_path), read_only=read_only)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def execute_batches(self, sql: str, params: list, *, rows_per_batch: int):
        """Export용 record batch reader를 context manager로 반환."""
        with self.connect(read_only=True) as connection:
            yield connection.execute(sql, params).fetch_record_batch(
                rows_per_batch=rows_per_batch
            )

    def exists(self) -> bool:
        return self.database_path.exists()
