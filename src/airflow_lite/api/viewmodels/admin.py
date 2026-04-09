"""View models for the Admin page.

These mirror the shape of `airflow_lite.storage.models` entities but live
in the API layer so renderers can consume a stable presentation contract
without importing storage types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class ConnectionVM:
    conn_id: str
    conn_type: str = "oracle"
    host: str | None = None
    port: int | None = None
    schema: str | None = None
    login: str | None = None
    description: str | None = None

    @classmethod
    def from_model(cls, model) -> "ConnectionVM":
        return cls(
            conn_id=model.conn_id,
            conn_type=model.conn_type,
            host=model.host,
            port=model.port,
            schema=model.schema,
            login=model.login,
            description=model.description,
        )


@dataclass
class VariableVM:
    key: str
    val: str | None = None
    description: str | None = None

    @classmethod
    def from_model(cls, model) -> "VariableVM":
        return cls(key=model.key, val=model.val, description=model.description)


@dataclass
class PoolVM:
    pool_name: str
    slots: int = 1
    description: str | None = None

    @classmethod
    def from_model(cls, model) -> "PoolVM":
        return cls(
            pool_name=model.pool_name,
            slots=model.slots,
            description=model.description,
        )


@dataclass
class PipelineVM:
    name: str
    table: str
    partition_column: str
    strategy: str = "full"
    schedule: str = "0 2 * * *"
    chunk_size: int | None = None
    columns: str | None = None
    incremental_key: str | None = None

    @classmethod
    def from_model(cls, model) -> "PipelineVM":
        return cls(
            name=model.name,
            table=model.table,
            partition_column=model.partition_column,
            strategy=model.strategy,
            schedule=model.schedule,
            chunk_size=model.chunk_size,
            columns=model.columns,
            incremental_key=model.incremental_key,
        )


@dataclass
class AdminPageViewData:
    connections: list[ConnectionVM] = field(default_factory=list)
    variables: list[VariableVM] = field(default_factory=list)
    pools: list[PoolVM] = field(default_factory=list)
    pipelines: list[PipelineVM] = field(default_factory=list)

    @classmethod
    def from_repo_payload(
        cls,
        *,
        connections: Iterable,
        variables: Iterable,
        pools: Iterable,
        pipelines: Iterable,
    ) -> "AdminPageViewData":
        return cls(
            connections=[ConnectionVM.from_model(c) for c in connections],
            variables=[VariableVM.from_model(v) for v in variables],
            pools=[PoolVM.from_model(p) for p in pools],
            pipelines=[PipelineVM.from_model(p) for p in pipelines],
        )
