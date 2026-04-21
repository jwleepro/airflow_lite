"""View models for the Admin page.

These mirror the shape of `airflow_lite.storage.models` entities but live
in the API layer so renderers can consume a stable presentation contract
without importing storage types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from airflow_lite.api.viewmodels._base import ModelMappingMixin


@dataclass
class ConnectionVM(ModelMappingMixin):
    conn_id: str
    conn_type: str = "oracle"
    host: str | None = None
    port: int | None = None
    schema: str | None = None
    login: str | None = None
    description: str | None = None


@dataclass
class VariableVM(ModelMappingMixin):
    key: str
    val: str | None = None
    description: str | None = None


@dataclass
class PoolVM(ModelMappingMixin):
    pool_name: str
    slots: int = 1
    description: str | None = None


@dataclass
class AdminPageViewData:
    connections: list[ConnectionVM] = field(default_factory=list)
    variables: list[VariableVM] = field(default_factory=list)
    pools: list[PoolVM] = field(default_factory=list)

    @classmethod
    def from_repo_payload(
        cls,
        *,
        connections: Iterable,
        variables: Iterable,
        pools: Iterable,
    ) -> "AdminPageViewData":
        return cls(
            connections=[ConnectionVM.from_model(c) for c in connections],
            variables=[VariableVM.from_model(v) for v in variables],
            pools=[PoolVM.from_model(p) for p in pools],
        )
