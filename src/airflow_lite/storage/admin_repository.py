from typing import Optional

from airflow_lite.storage.connection_repository import ConnectionRepository
from airflow_lite.storage.crypto import Crypto
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
from airflow_lite.storage.yaml_admin_migration import migrate_yaml_to_sqlite


class AdminRepository:
    """Admin UI 리소스 CRUD 파사드.

    내부적으로 리소스별 Repository에 위임한다. 기존 호출부 호환용.
    """

    def __init__(
        self,
        database: Database,
        config_path: str = "",
        crypto: Crypto | None = None,
    ):
        self.db = database
        self.config_path = config_path
        self.crypto = crypto or Crypto.from_env()
        self.connections = ConnectionRepository(database, self.crypto)
        self.variables = VariableRepository(database)
        self.pools = PoolRepository(database)
        self.pipelines = PipelineRepository(database)
        migrate_yaml_to_sqlite(
            database,
            config_path,
            connections=self.connections,
            variables=self.variables,
            pools=self.pools,
            pipelines=self.pipelines,
            crypto=self.crypto,
        )

    # --- Connections ---
    def get_connection(self, conn_id: str) -> Optional[ConnectionModel]:
        return self.connections.get(conn_id)

    def list_connections(self) -> list[ConnectionModel]:
        return self.connections.list()

    def create_connection(self, model: ConnectionModel) -> None:
        self.connections.create(model)

    def update_connection(self, model: ConnectionModel) -> None:
        self.connections.update(model)

    def delete_connection(self, conn_id: str) -> None:
        self.connections.delete(conn_id)

    # --- Variables ---
    def get_variable(self, key: str) -> Optional[VariableModel]:
        return self.variables.get(key)

    def list_variables(self) -> list[VariableModel]:
        return self.variables.list()

    def create_variable(self, model: VariableModel) -> None:
        self.variables.create(model)

    def update_variable(self, model: VariableModel) -> None:
        self.variables.update(model)

    def delete_variable(self, key: str) -> None:
        self.variables.delete(key)

    # --- Pools ---
    def get_pool(self, pool_name: str) -> Optional[PoolModel]:
        return self.pools.get(pool_name)

    def list_pools(self) -> list[PoolModel]:
        return self.pools.list()

    def create_pool(self, model: PoolModel) -> None:
        self.pools.create(model)

    def update_pool(self, model: PoolModel) -> None:
        self.pools.update(model)

    def delete_pool(self, pool_name: str) -> None:
        self.pools.delete(pool_name)

    # --- Pipelines ---
    def get_pipeline(self, name: str) -> Optional[PipelineModel]:
        return self.pipelines.get(name)

    def list_pipelines(self) -> list[PipelineModel]:
        return self.pipelines.list()

    def create_pipeline(self, model: PipelineModel) -> None:
        self.pipelines.create(model)

    def update_pipeline(self, model: PipelineModel) -> None:
        self.pipelines.update(model)

    def delete_pipeline(self, name: str) -> None:
        self.pipelines.delete(name)
