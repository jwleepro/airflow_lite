import os
from typing import Any, Optional

import ruamel.yaml

from airflow_lite.storage.crypto import Crypto
from airflow_lite.storage.database import Database
from airflow_lite.storage.models import (
    ConnectionModel,
    PipelineModel,
    PoolModel,
    VariableModel,
)


class AdminRepository:
    """Admin UI에서 관리하는 리소스 CRUD 및 YAML->SQLite 1회 마이그레이션."""

    _DECRYPT_FAILED = "---DECRYPTION_FAILED---"

    def __init__(self, database: Database, config_path: str = ""):
        self.db = database
        self.config_path = config_path
        self._migrate_from_yaml()

    # --- Migration ---
    def _migrate_from_yaml(self) -> None:
        """서버 기동 시 YAML 관리 데이터(legacy)를 SQLite로 1회 import."""
        if not self.config_path or not os.path.exists(self.config_path):
            return

        yaml = ruamel.yaml.YAML()
        with open(self.config_path, "r", encoding="utf-8") as file:
            data = yaml.load(file)

        if not isinstance(data, dict):
            return

        connections_empty = self._table_is_empty("connections")
        variables_empty = self._table_is_empty("variables")
        pools_empty = self._table_is_empty("pools")
        pipelines_empty = self._table_is_empty("pipeline_configs")

        migrated = False

        oracle_data = data.get("oracle")
        if isinstance(oracle_data, dict) and self.get_connection("oracle") is None:
            self.create_connection(
                ConnectionModel(
                    conn_id="oracle",
                    conn_type="oracle",
                    host=oracle_data.get("host"),
                    port=oracle_data.get("port"),
                    schema=oracle_data.get("service_name"),
                    login=oracle_data.get("user"),
                    password=self._decode_yaml_password(oracle_data.get("password")),
                    description="Oracle Source Database",
                )
            )
            migrated = True

        if connections_empty:
            for connection_item in self._as_list(data.get("connections")):
                connection = self._build_connection_model(connection_item)
                if connection and self.get_connection(connection.conn_id) is None:
                    self.create_connection(connection)
                    migrated = True

        if variables_empty:
            for variable_item in self._as_list(data.get("variables")):
                variable = self._build_variable_model(variable_item)
                if variable and self.get_variable(variable.key) is None:
                    self.create_variable(variable)
                    migrated = True

        if pools_empty:
            for pool_item in self._as_list(data.get("pools")):
                pool = self._build_pool_model(pool_item)
                if pool and self.get_pool(pool.pool_name) is None:
                    self.create_pool(pool)
                    migrated = True

        if pipelines_empty:
            for pipeline_item in self._as_list(data.get("pipelines")):
                pipeline = self._build_pipeline_model(pipeline_item)
                if pipeline and self.get_pipeline(pipeline.name) is None:
                    self.create_pipeline(pipeline)
                    migrated = True

        if not migrated:
            return

        for key in ("oracle", "connections", "variables", "pools", "pipelines"):
            if key in data:
                del data[key]

        with open(self.config_path, "w", encoding="utf-8") as file:
            yaml.dump(data, file)

    def _table_is_empty(self, table_name: str) -> bool:
        with self.db.connection() as conn:
            count = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table_name}").fetchone()["cnt"]
        return count == 0

    @staticmethod
    def _as_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _decode_yaml_password(raw_password: str | None) -> str | None:
        if raw_password is None:
            return None
        decrypted = Crypto.decrypt(raw_password)
        if decrypted == AdminRepository._DECRYPT_FAILED:
            return raw_password
        return decrypted

    def _build_connection_model(self, item: dict[str, Any]) -> ConnectionModel | None:
        conn_id = item.get("conn_id")
        if not conn_id:
            return None
        return ConnectionModel(
            conn_id=str(conn_id),
            conn_type=str(item.get("conn_type", "oracle")),
            host=item.get("host"),
            port=item.get("port"),
            schema=item.get("schema"),
            login=item.get("login"),
            password=self._decode_yaml_password(item.get("password")),
            extra=item.get("extra"),
            description=item.get("description"),
        )

    @staticmethod
    def _build_variable_model(item: dict[str, Any]) -> VariableModel | None:
        key = item.get("key")
        if not key:
            return None
        return VariableModel(
            key=str(key),
            val=item.get("val"),
            description=item.get("description"),
        )

    @staticmethod
    def _build_pool_model(item: dict[str, Any]) -> PoolModel | None:
        pool_name = item.get("pool_name")
        if not pool_name:
            return None
        slots = item.get("slots")
        try:
            slots_value = int(slots) if slots is not None else 1
        except (TypeError, ValueError):
            slots_value = 1
        return PoolModel(
            pool_name=str(pool_name),
            slots=slots_value,
            description=item.get("description"),
        )

    @staticmethod
    def _normalize_columns(columns: str | list[str] | None) -> str | None:
        if columns is None:
            return None
        if isinstance(columns, str):
            normalized = ",".join(
                part.strip()
                for part in columns.split(",")
                if part and part.strip()
            )
            return normalized or None
        if isinstance(columns, list):
            normalized = ",".join(
                str(part).strip()
                for part in columns
                if str(part).strip()
            )
            return normalized or None
        return None

    def _build_pipeline_model(self, item: dict[str, Any]) -> PipelineModel | None:
        name = item.get("name")
        table = item.get("table")
        partition_column = item.get("partition_column")
        if not name or not table or not partition_column:
            return None

        chunk_size_raw = item.get("chunk_size")
        try:
            chunk_size = int(chunk_size_raw) if chunk_size_raw is not None else None
        except (TypeError, ValueError):
            chunk_size = None

        return PipelineModel(
            name=str(name),
            table=str(table),
            partition_column=str(partition_column),
            strategy=str(item.get("strategy", "full")),
            schedule=str(item.get("schedule", "0 2 * * *")),
            chunk_size=chunk_size,
            columns=self._normalize_columns(item.get("columns")),
            incremental_key=item.get("incremental_key"),
        )

    # --- Connections ---
    @staticmethod
    def _decode_db_password(raw_password: str | None) -> str | None:
        if raw_password is None:
            return None
        decrypted = Crypto.decrypt(raw_password)
        if decrypted == AdminRepository._DECRYPT_FAILED:
            return raw_password
        return decrypted

    def get_connection(self, conn_id: str) -> Optional[ConnectionModel]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM connections WHERE conn_id = ?",
                (conn_id,),
            ).fetchone()
            if not row:
                return None
            return ConnectionModel(
                conn_id=row["conn_id"],
                conn_type=row["conn_type"],
                host=row["host"],
                port=row["port"],
                schema=row["schema"],
                login=row["login"],
                password=self._decode_db_password(row["password"]),
                extra=row["extra"],
                description=row["description"],
            )

    def list_connections(self) -> list[ConnectionModel]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM connections ORDER BY conn_id").fetchall()
            return [
                ConnectionModel(
                    conn_id=row["conn_id"],
                    conn_type=row["conn_type"],
                    host=row["host"],
                    port=row["port"],
                    schema=row["schema"],
                    login=row["login"],
                    password=self._decode_db_password(row["password"]),
                    extra=row["extra"],
                    description=row["description"],
                )
                for row in rows
            ]

    def create_connection(self, conn_model: ConnectionModel) -> None:
        encrypted_password = Crypto.encrypt(conn_model.password)
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO connections
                (conn_id, conn_type, host, port, schema, login, password, extra, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conn_model.conn_id,
                    conn_model.conn_type,
                    conn_model.host,
                    conn_model.port,
                    conn_model.schema,
                    conn_model.login,
                    encrypted_password,
                    conn_model.extra,
                    conn_model.description,
                ),
            )
            conn.commit()

    def update_connection(self, conn_model: ConnectionModel) -> None:
        encrypted_password = Crypto.encrypt(conn_model.password)
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE connections
                SET conn_type = ?, host = ?, port = ?, schema = ?, login = ?,
                    password = ?, extra = ?, description = ?
                WHERE conn_id = ?
                """,
                (
                    conn_model.conn_type,
                    conn_model.host,
                    conn_model.port,
                    conn_model.schema,
                    conn_model.login,
                    encrypted_password,
                    conn_model.extra,
                    conn_model.description,
                    conn_model.conn_id,
                ),
            )
            conn.commit()

    def delete_connection(self, conn_id: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM connections WHERE conn_id = ?", (conn_id,))
            conn.commit()

    # --- Variables ---
    def get_variable(self, key: str) -> Optional[VariableModel]:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM variables WHERE key = ?", (key,)).fetchone()
            if not row:
                return None
            return VariableModel(key=row["key"], val=row["val"], description=row["description"])

    def list_variables(self) -> list[VariableModel]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM variables ORDER BY key").fetchall()
            return [
                VariableModel(key=row["key"], val=row["val"], description=row["description"])
                for row in rows
            ]

    def create_variable(self, var: VariableModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO variables (key, val, description) VALUES (?, ?, ?)",
                (var.key, var.val, var.description),
            )
            conn.commit()

    def update_variable(self, var: VariableModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE variables SET val = ?, description = ? WHERE key = ?",
                (var.val, var.description, var.key),
            )
            conn.commit()

    def delete_variable(self, key: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM variables WHERE key = ?", (key,))
            conn.commit()

    # --- Pools ---
    def get_pool(self, pool_name: str) -> Optional[PoolModel]:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM pools WHERE pool_name = ?", (pool_name,)).fetchone()
            if not row:
                return None
            return PoolModel(pool_name=row["pool_name"], slots=row["slots"], description=row["description"])

    def list_pools(self) -> list[PoolModel]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM pools ORDER BY pool_name").fetchall()
            return [
                PoolModel(pool_name=row["pool_name"], slots=row["slots"], description=row["description"])
                for row in rows
            ]

    def create_pool(self, pool: PoolModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO pools (pool_name, slots, description) VALUES (?, ?, ?)",
                (pool.pool_name, pool.slots, pool.description),
            )
            conn.commit()

    def update_pool(self, pool: PoolModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE pools SET slots = ?, description = ? WHERE pool_name = ?",
                (pool.slots, pool.description, pool.pool_name),
            )
            conn.commit()

    def delete_pool(self, pool_name: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM pools WHERE pool_name = ?", (pool_name,))
            conn.commit()

    # --- Pipelines ---
    def get_pipeline(self, name: str) -> Optional[PipelineModel]:
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    name,
                    source_table,
                    partition_column,
                    strategy,
                    schedule,
                    chunk_size,
                    columns,
                    incremental_key
                FROM pipeline_configs
                WHERE name = ?
                """,
                (name,),
            ).fetchone()
            if not row:
                return None
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

    def list_pipelines(self) -> list[PipelineModel]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    name,
                    source_table,
                    partition_column,
                    strategy,
                    schedule,
                    chunk_size,
                    columns,
                    incremental_key
                FROM pipeline_configs
                ORDER BY name
                """
            ).fetchall()
            return [
                PipelineModel(
                    name=row["name"],
                    table=row["source_table"],
                    partition_column=row["partition_column"],
                    strategy=row["strategy"],
                    schedule=row["schedule"],
                    chunk_size=row["chunk_size"],
                    columns=row["columns"],
                    incremental_key=row["incremental_key"],
                )
                for row in rows
            ]

    def create_pipeline(self, pipeline: PipelineModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_configs
                (
                    name,
                    source_table,
                    partition_column,
                    strategy,
                    schedule,
                    chunk_size,
                    columns,
                    incremental_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pipeline.name,
                    pipeline.table,
                    pipeline.partition_column,
                    pipeline.strategy,
                    pipeline.schedule,
                    pipeline.chunk_size,
                    self._normalize_columns(pipeline.columns),
                    pipeline.incremental_key,
                ),
            )
            conn.commit()

    def update_pipeline(self, pipeline: PipelineModel) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_configs
                SET
                    source_table = ?,
                    partition_column = ?,
                    strategy = ?,
                    schedule = ?,
                    chunk_size = ?,
                    columns = ?,
                    incremental_key = ?
                WHERE name = ?
                """,
                (
                    pipeline.table,
                    pipeline.partition_column,
                    pipeline.strategy,
                    pipeline.schedule,
                    pipeline.chunk_size,
                    self._normalize_columns(pipeline.columns),
                    pipeline.incremental_key,
                    pipeline.name,
                ),
            )
            conn.commit()

    def delete_pipeline(self, name: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM pipeline_configs WHERE name = ?", (name,))
            conn.commit()
