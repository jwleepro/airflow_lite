from typing import Optional

from airflow_lite.storage._helpers import decode_password
from airflow_lite.storage.crypto import Crypto
from airflow_lite.storage.database import Database
from airflow_lite.storage.models import ConnectionModel


def _row_to_model(row, crypto: Crypto) -> ConnectionModel:
    return ConnectionModel(
        conn_id=row["conn_id"],
        conn_type=row["conn_type"],
        host=row["host"],
        port=row["port"],
        schema=row["schema"],
        login=row["login"],
        password=decode_password(row["password"], crypto),
        extra=row["extra"],
        description=row["description"],
    )


class ConnectionRepository:
    def __init__(self, database: Database, crypto: Crypto):
        self.db = database
        self.crypto = crypto

    def get(self, conn_id: str) -> Optional[ConnectionModel]:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM connections WHERE conn_id = ?",
                (conn_id,),
            ).fetchone()
            return _row_to_model(row, self.crypto) if row else None

    def list(self) -> list[ConnectionModel]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM connections ORDER BY conn_id"
            ).fetchall()
            return [_row_to_model(row, self.crypto) for row in rows]

    def create(self, model: ConnectionModel) -> None:
        encrypted_password = self.crypto.encrypt(model.password)
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO connections
                (conn_id, conn_type, host, port, schema, login, password, extra, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.conn_id,
                    model.conn_type,
                    model.host,
                    model.port,
                    model.schema,
                    model.login,
                    encrypted_password,
                    model.extra,
                    model.description,
                ),
            )
            conn.commit()

    def update(self, model: ConnectionModel) -> None:
        encrypted_password = self.crypto.encrypt(model.password)
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE connections
                SET conn_type = ?, host = ?, port = ?, schema = ?, login = ?,
                    password = ?, extra = ?, description = ?
                WHERE conn_id = ?
                """,
                (
                    model.conn_type,
                    model.host,
                    model.port,
                    model.schema,
                    model.login,
                    encrypted_password,
                    model.extra,
                    model.description,
                    model.conn_id,
                ),
            )
            conn.commit()

    def delete(self, conn_id: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM connections WHERE conn_id = ?", (conn_id,))
            conn.commit()
