import os
from typing import List, Optional
from airflow_lite.storage.database import Database
from airflow_lite.storage.models import ConnectionModel, VariableModel, PoolModel
from airflow_lite.storage.crypto import Crypto
from airflow_lite.config.settings import Settings
import ruamel.yaml

class AdminRepository:
    """Admin UI에서 관리하는 Connections, Variables, Pools의 데이터 접근(CRUD) 구현체."""

    def __init__(self, database: Database, config_path: str = ""):
        self.db = database
        self.config_path = config_path
        self._load_from_yaml()

    def _load_from_yaml(self):
        """서버 기동 시 YAML 설정 파일의 내용을 SQLite로 불러옵니다."""
        if not self.config_path or not os.path.exists(self.config_path):
            return
            
        yaml = ruamel.yaml.YAML()
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
            
        if not data:
            return

        # Load oracle connection
        oracle_data = data.get("oracle")
        if oracle_data:
            existing = self.get_connection("oracle")
            # 복호화 시도 (암호화된 문자열인지 확인)
            raw_pwd = oracle_data.get("password", "")
            decrypted = Crypto.decrypt(raw_pwd)
            if decrypted == "---DECRYPTION_FAILED---":
                # 암호화되지 않은 평문이라면
                pwd = raw_pwd
            else:
                pwd = decrypted

            conn = ConnectionModel(
                conn_id="oracle",
                conn_type="oracle",
                host=oracle_data.get("host"),
                port=oracle_data.get("port"),
                schema=oracle_data.get("service_name"),
                login=oracle_data.get("user"),
                password=pwd,
                description="Oracle Source Database"
            )
            if existing:
                self.update_connection(conn)
            else:
                self.create_connection(conn)

    def _sync_to_yaml(self):
        """SQLite에 저장된 최신 상태를 config_path YAML 파일에 덮어쓴다 (주석 보존)."""
        if not self.config_path or not os.path.exists(self.config_path):
            return

        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
            
        if data is None:
            data = {}

        # Oracle connection sync (backward compatibility for legacy pipelines.yaml)
        oracle_conn = self.get_connection("oracle")
        if oracle_conn:
            if "oracle" not in data:
                data.insert(0, "oracle", {})
            if oracle_conn.host is not None:
                data["oracle"]["host"] = oracle_conn.host
            if oracle_conn.port is not None:
                data["oracle"]["port"] = oracle_conn.port
            if oracle_conn.schema is not None:
                data["oracle"]["service_name"] = oracle_conn.schema
            if oracle_conn.login is not None:
                data["oracle"]["user"] = oracle_conn.login
            if oracle_conn.password is not None:
                # Store the encrypted password in YAML
                data["oracle"]["password"] = Crypto.encrypt(oracle_conn.password)
        elif "oracle" in data:
            del data["oracle"]

        # 1. oracle 설정 바로 뒤(또는 최상단)에 위치를 잡는다.
        keys = list(data.keys())
        oracle_pos = keys.index("oracle") if "oracle" in keys else -1
        insert_pos = oracle_pos + 1 if oracle_pos >= 0 else 0

        # Sync other connections
        conns = []
        for c in self.list_connections():
            if c.conn_id == "oracle":
                continue
            conns.append({
                "conn_id": c.conn_id,
                "conn_type": c.conn_type,
                "host": c.host,
                "port": c.port,
                "schema": c.schema,
                "login": c.login,
                "password": Crypto.encrypt(c.password) if c.password else None,
                "extra": c.extra,
                "description": c.description
            })
            
        if conns:
            if "connections" not in data:
                data.insert(insert_pos, "connections", conns)
                insert_pos += 1
            else:
                data["connections"] = conns
                insert_pos = list(data.keys()).index("connections") + 1
        elif "connections" in data:
            del data["connections"]

        # Sync variables
        vars_list = []
        for v in self.list_variables():
            vars_list.append({"key": v.key, "val": v.val, "description": v.description})
            
        if vars_list:
            if "variables" not in data:
                data.insert(insert_pos, "variables", vars_list)
                insert_pos += 1
            else:
                data["variables"] = vars_list
                insert_pos = list(data.keys()).index("variables") + 1
        elif "variables" in data:
            del data["variables"]

        # Sync pools
        pools_list = []
        for p in self.list_pools():
            pools_list.append({"pool_name": p.pool_name, "slots": p.slots, "description": p.description})
            
        if pools_list:
            if "pools" not in data:
                data.insert(insert_pos, "pools", pools_list)
            else:
                data["pools"] = pools_list
        elif "pools" in data:
            del data["pools"]

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)

    # --- Connections ---
    def get_connection(self, conn_id: str) -> Optional[ConnectionModel]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM connections WHERE conn_id = ?",
                (conn_id,)
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
                password=Crypto.decrypt(row["password"]),
                extra=row["extra"],
                description=row["description"]
            )

    def list_connections(self) -> List[ConnectionModel]:
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
                    password=Crypto.decrypt(row["password"]),
                    extra=row["extra"],
                    description=row["description"]
                )
                for row in rows
            ]

    def create_connection(self, conn_model: ConnectionModel):
        encrypted_password = Crypto.encrypt(conn_model.password)
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO connections
                (conn_id, conn_type, host, port, schema, login, password, extra, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (conn_model.conn_id, conn_model.conn_type, conn_model.host, conn_model.port, conn_model.schema,
                 conn_model.login, encrypted_password, conn_model.extra, conn_model.description)
            )
            conn.commit()
        self._sync_to_yaml()

    def update_connection(self, conn_model: ConnectionModel):
        encrypted_password = Crypto.encrypt(conn_model.password)
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE connections
                SET conn_type = ?, host = ?, port = ?, schema = ?, login = ?,
                    password = ?, extra = ?, description = ?
                WHERE conn_id = ?
                """,
                (conn_model.conn_type, conn_model.host, conn_model.port, conn_model.schema, conn_model.login,
                 encrypted_password, conn_model.extra, conn_model.description, conn_model.conn_id)
            )
            conn.commit()
        self._sync_to_yaml()

    def delete_connection(self, conn_id: str):
        with self.db.connection() as conn:
            conn.execute("DELETE FROM connections WHERE conn_id = ?", (conn_id,))
            conn.commit()
        self._sync_to_yaml()

    # --- Variables ---
    def get_variable(self, key: str) -> Optional[VariableModel]:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM variables WHERE key = ?", (key,)).fetchone()
            if not row:
                return None
            return VariableModel(key=row["key"], val=row["val"], description=row["description"])

    def list_variables(self) -> List[VariableModel]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM variables ORDER BY key").fetchall()
            return [
                VariableModel(key=row["key"], val=row["val"], description=row["description"])
                for row in rows
            ]

    def create_variable(self, var: VariableModel):
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO variables (key, val, description) VALUES (?, ?, ?)",
                (var.key, var.val, var.description)
            )
            conn.commit()
        self._sync_to_yaml()

    def update_variable(self, var: VariableModel):
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE variables SET val = ?, description = ? WHERE key = ?",
                (var.val, var.description, var.key)
            )
            conn.commit()
        self._sync_to_yaml()

    def delete_variable(self, key: str):
        with self.db.connection() as conn:
            conn.execute("DELETE FROM variables WHERE key = ?", (key,))
            conn.commit()
        self._sync_to_yaml()

    # --- Pools ---
    def get_pool(self, pool_name: str) -> Optional[PoolModel]:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM pools WHERE pool_name = ?", (pool_name,)).fetchone()
            if not row:
                return None
            return PoolModel(pool_name=row["pool_name"], slots=row["slots"], description=row["description"])

    def list_pools(self) -> List[PoolModel]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM pools ORDER BY pool_name").fetchall()
            return [
                PoolModel(pool_name=row["pool_name"], slots=row["slots"], description=row["description"])
                for row in rows
            ]

    def create_pool(self, pool: PoolModel):
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO pools (pool_name, slots, description) VALUES (?, ?, ?)",
                (pool.pool_name, pool.slots, pool.description)
            )
            conn.commit()
        self._sync_to_yaml()

    def update_pool(self, pool: PoolModel):
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE pools SET slots = ?, description = ? WHERE pool_name = ?",
                (pool.slots, pool.description, pool.pool_name)
            )
            conn.commit()
        self._sync_to_yaml()

    def delete_pool(self, pool_name: str):
        with self.db.connection() as conn:
            conn.execute("DELETE FROM pools WHERE pool_name = ?", (pool_name,))
            conn.commit()
        self._sync_to_yaml()
