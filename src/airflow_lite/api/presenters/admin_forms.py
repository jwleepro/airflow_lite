"""Parse admin POST form payloads and persist via AdminRepository.

Routes call these functions so that storage model construction never
leaks into HTTP handlers.
"""

from __future__ import annotations

from airflow_lite.api.forms import first_value as _first_value
from airflow_lite.storage.models import (
    ConnectionModel,
    PipelineModel,
    PoolModel,
    VariableModel,
)


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def create_connection(admin_repo, form_data: dict[str, list[str]]) -> None:
    port_str = _first_value(form_data, "port")
    conn = ConnectionModel(
        conn_id=_first_value(form_data, "conn_id", "") or "",
        conn_type=_first_value(form_data, "conn_type", "oracle") or "oracle",
        host=_first_value(form_data, "host"),
        port=int(port_str) if port_str and port_str.isdigit() else None,
        schema=_first_value(form_data, "schema"),
        login=_first_value(form_data, "login"),
        password=_first_value(form_data, "password"),
        description=_first_value(form_data, "description"),
    )
    if conn.conn_id:
        admin_repo.create_connection(conn)


def delete_connection(admin_repo, form_data: dict[str, list[str]]) -> None:
    conn_id = _first_value(form_data, "conn_id")
    if conn_id:
        admin_repo.delete_connection(conn_id)


def create_variable(admin_repo, form_data: dict[str, list[str]]) -> None:
    var = VariableModel(
        key=_first_value(form_data, "key", "") or "",
        val=_first_value(form_data, "val", "") or "",
        description=_first_value(form_data, "description"),
    )
    if var.key:
        admin_repo.create_variable(var)


def delete_variable(admin_repo, form_data: dict[str, list[str]]) -> None:
    key = _first_value(form_data, "key")
    if key:
        admin_repo.delete_variable(key)


def create_pool(admin_repo, form_data: dict[str, list[str]]) -> None:
    try:
        slots = int(_first_value(form_data, "slots", "1") or "1")
    except ValueError:
        slots = 1
    pool = PoolModel(
        pool_name=_first_value(form_data, "pool_name", "") or "",
        slots=slots,
        description=_first_value(form_data, "description"),
    )
    if pool.pool_name:
        admin_repo.create_pool(pool)


def delete_pool(admin_repo, form_data: dict[str, list[str]]) -> None:
    pool_name = _first_value(form_data, "pool_name")
    if pool_name:
        admin_repo.delete_pool(pool_name)


def _pipeline_model_from_form(form_data: dict[str, list[str]]) -> PipelineModel | None:
    name = _first_value(form_data, "name", "") or ""
    table = _first_value(form_data, "table", "") or ""
    partition_column = _first_value(form_data, "partition_column", "") or ""
    strategy = _first_value(form_data, "strategy", "full") or "full"
    schedule = _first_value(form_data, "schedule", "0 2 * * *") or "0 2 * * *"
    incremental_key = _first_value(form_data, "incremental_key")
    if strategy != "incremental":
        incremental_key = None

    if not (name and table and partition_column):
        return None

    return PipelineModel(
        name=name,
        table=table,
        partition_column=partition_column,
        strategy=strategy,
        schedule=schedule,
        chunk_size=_parse_optional_int(_first_value(form_data, "chunk_size")),
        columns=_first_value(form_data, "columns"),
        incremental_key=incremental_key,
    )


def create_pipeline(admin_repo, form_data: dict[str, list[str]]) -> None:
    model = _pipeline_model_from_form(form_data)
    if model is not None:
        admin_repo.create_pipeline(model)


def update_pipeline(admin_repo, form_data: dict[str, list[str]]) -> None:
    model = _pipeline_model_from_form(form_data)
    if model is not None:
        admin_repo.update_pipeline(model)


def delete_pipeline(admin_repo, form_data: dict[str, list[str]]) -> None:
    name = _first_value(form_data, "name")
    if name:
        admin_repo.delete_pipeline(name)
