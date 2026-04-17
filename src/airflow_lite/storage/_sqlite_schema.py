"""SQLite schema introspection and ALTER helpers shared by migrations/loaders."""

from __future__ import annotations

import sqlite3


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {row["name"] for row in rows}


def ensure_columns(
    conn: sqlite3.Connection,
    table_name: str,
    specs: list[tuple[str, str]],
) -> set[str]:
    """(column_name, column_ddl) 목록을 받아 누락분만 ALTER TABLE 로 추가.

    반환값은 ALTER 실행 이후 전체 컬럼 집합. SQL 재파싱 없이 specs 로부터 확장된다.
    """
    existing = table_columns(conn, table_name)
    for name, ddl in specs:
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}")
        existing.add(name)
    return existing
