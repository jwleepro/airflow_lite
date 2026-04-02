import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        """schema.sql을 실행하여 테이블 생성."""
        schema_path = Path(__file__).parent / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = self.get_connection()
        try:
            self._execute_script_atomically(conn, schema_sql)
            self._migrate_pipeline_runs_unique_constraint(conn)
            self._drop_pipeline_runs_success_unique_index(conn)
        finally:
            conn.close()

    def _execute_script_atomically(self, conn: sqlite3.Connection, script: str) -> None:
        # `executescript()` manages its own transaction boundaries and is too opaque for
        # mixed DDL/DML migrations where we must guarantee an all-or-nothing rollback.
        statements = list(self._split_sql_statements(script))
        conn.execute("BEGIN")
        try:
            for statement in statements:
                conn.execute(statement)
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

    @staticmethod
    def _split_sql_statements(script: str):
        buffer: list[str] = []
        for line in script.splitlines():
            buffer.append(line)
            candidate = "\n".join(buffer).strip()
            if candidate and sqlite3.complete_statement(candidate):
                if Database._has_executable_sql(candidate):
                    yield candidate
                buffer = []

        trailing = "\n".join(buffer).strip()
        if trailing and Database._has_executable_sql(trailing):
            raise sqlite3.OperationalError("Incomplete SQL statement.")

    @staticmethod
    def _has_executable_sql(statement: str) -> bool:
        return any(
            stripped and not stripped.startswith("--")
            for stripped in (line.strip() for line in statement.splitlines())
        )

    def _migrate_pipeline_runs_unique_constraint(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'pipeline_runs'
            """
        ).fetchone()
        table_sql = row["sql"] if row else None
        if not table_sql or "UNIQUE(pipeline_name, execution_date, trigger_type)" not in table_sql:
            return

        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            self._execute_script_atomically(
                conn,
                """
                ALTER TABLE step_runs RENAME TO step_runs_old;
                ALTER TABLE pipeline_runs RENAME TO pipeline_runs_old;

                CREATE TABLE pipeline_runs (
                    id              TEXT PRIMARY KEY,
                    pipeline_name   TEXT NOT NULL,
                    execution_date  TEXT NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'pending',
                    started_at      TEXT,
                    finished_at     TEXT,
                    trigger_type    TEXT NOT NULL DEFAULT 'scheduled',
                    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE step_runs (
                    id                TEXT PRIMARY KEY,
                    pipeline_run_id   TEXT NOT NULL REFERENCES pipeline_runs(id),
                    step_name         TEXT NOT NULL,
                    status            TEXT NOT NULL DEFAULT 'pending',
                    started_at        TEXT,
                    finished_at       TEXT,
                    records_processed INTEGER DEFAULT 0,
                    error_message     TEXT,
                    retry_count       INTEGER DEFAULT 0,
                    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
                );

                INSERT INTO pipeline_runs (
                    id, pipeline_name, execution_date, status,
                    started_at, finished_at, trigger_type, created_at
                )
                SELECT
                    id, pipeline_name, execution_date, status,
                    started_at, finished_at, trigger_type, created_at
                FROM pipeline_runs_old;

                INSERT INTO step_runs (
                    id, pipeline_run_id, step_name, status, started_at,
                    finished_at, records_processed, error_message, retry_count, created_at
                )
                SELECT
                    id, pipeline_run_id, step_name, status, started_at,
                    finished_at, records_processed, error_message, retry_count, created_at
                FROM step_runs_old;

                DROP TABLE step_runs_old;
                DROP TABLE pipeline_runs_old;

                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_exec_date
                    ON pipeline_runs(execution_date);
                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
                    ON pipeline_runs(status);
                CREATE INDEX IF NOT EXISTS idx_step_runs_pipeline_run
                    ON step_runs(pipeline_run_id);
                """,
            )
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

    def _drop_pipeline_runs_success_unique_index(self, conn: sqlite3.Connection) -> None:
        self._execute_script_atomically(
            conn, "DROP INDEX IF EXISTS idx_pipeline_runs_success_unique;"
        )
