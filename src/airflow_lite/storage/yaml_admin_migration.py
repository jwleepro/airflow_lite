import os
from typing import Any

import ruamel.yaml

from airflow_lite.storage._helpers import decode_password, normalize_columns
from airflow_lite.storage.connection_repository import ConnectionRepository
from airflow_lite.storage.database import Database
from airflow_lite.storage.models import (
    ConnectionModel,
    PipelineModel,
    PoolModel,
    VariableModel,
)
from airflow_lite.storage.pipeline_repository import PipelineRepository
from airflow_lite.storage.pool_repository import PoolRepository
from airflow_lite.storage.variable_repository import VariableRepository


def _as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _build_connection_model(item: dict[str, Any]) -> ConnectionModel | None:
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
        password=decode_password(item.get("password")),
        extra=item.get("extra"),
        description=item.get("description"),
    )


def _build_variable_model(item: dict[str, Any]) -> VariableModel | None:
    key = item.get("key")
    if not key:
        return None
    return VariableModel(
        key=str(key),
        val=item.get("val"),
        description=item.get("description"),
    )


def _build_pool_model(item: dict[str, Any]) -> PoolModel | None:
    pool_name = item.get("pool_name")
    if not pool_name:
        return None
    slots_raw = item.get("slots")
    try:
        slots = int(slots_raw) if slots_raw is not None else 1
    except (TypeError, ValueError):
        slots = 1
    return PoolModel(
        pool_name=str(pool_name),
        slots=slots,
        description=item.get("description"),
    )


def _build_pipeline_model(item: dict[str, Any]) -> PipelineModel | None:
    name = item.get("name")
    table = item.get("table")
    partition_column = item.get("partition_column")
    if not name or not table or not partition_column:
        return None

    chunk_raw = item.get("chunk_size")
    try:
        chunk_size = int(chunk_raw) if chunk_raw is not None else None
    except (TypeError, ValueError):
        chunk_size = None

    return PipelineModel(
        name=str(name),
        table=str(table),
        partition_column=str(partition_column),
        strategy=str(item.get("strategy", "full")),
        schedule=str(item.get("schedule", "0 2 * * *")),
        chunk_size=chunk_size,
        columns=normalize_columns(item.get("columns")),
        incremental_key=item.get("incremental_key"),
    )


def _table_is_empty(db: Database, table_name: str) -> bool:
    with db.connection() as conn:
        count = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {table_name}"
        ).fetchone()["cnt"]
    return count == 0


def migrate_yaml_to_sqlite(
    database: Database,
    config_path: str,
    *,
    connections: ConnectionRepository,
    variables: VariableRepository,
    pools: PoolRepository,
    pipelines: PipelineRepository,
) -> None:
    """서버 기동 시 YAML 관리 데이터(legacy)를 SQLite로 1회 import."""
    if not config_path or not os.path.exists(config_path):
        return

    yaml = ruamel.yaml.YAML()
    with open(config_path, "r", encoding="utf-8") as file:
        data = yaml.load(file)

    if not isinstance(data, dict):
        return

    connections_empty = _table_is_empty(database, "connections")
    variables_empty = _table_is_empty(database, "variables")
    pools_empty = _table_is_empty(database, "pools")
    pipelines_empty = _table_is_empty(database, "pipeline_configs")

    migrated = False

    oracle_data = data.get("oracle")
    if isinstance(oracle_data, dict) and connections.get("oracle") is None:
        connections.create(
            ConnectionModel(
                conn_id="oracle",
                conn_type="oracle",
                host=oracle_data.get("host"),
                port=oracle_data.get("port"),
                schema=oracle_data.get("service_name"),
                login=oracle_data.get("user"),
                password=decode_password(oracle_data.get("password")),
                description="Oracle Source Database",
            )
        )
        migrated = True

    if connections_empty:
        for item in _as_list(data.get("connections")):
            model = _build_connection_model(item)
            if model and connections.get(model.conn_id) is None:
                connections.create(model)
                migrated = True

    if variables_empty:
        for item in _as_list(data.get("variables")):
            model = _build_variable_model(item)
            if model and variables.get(model.key) is None:
                variables.create(model)
                migrated = True

    if pools_empty:
        for item in _as_list(data.get("pools")):
            model = _build_pool_model(item)
            if model and pools.get(model.pool_name) is None:
                pools.create(model)
                migrated = True

    if pipelines_empty:
        for item in _as_list(data.get("pipelines")):
            model = _build_pipeline_model(item)
            if model and pipelines.get(model.name) is None:
                pipelines.create(model)
                migrated = True

    if not migrated:
        return

    for key in ("oracle", "connections", "variables", "pools", "pipelines"):
        if key in data:
            del data[key]

    with open(config_path, "w", encoding="utf-8") as file:
        yaml.dump(data, file)
