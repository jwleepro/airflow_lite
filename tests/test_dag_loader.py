from pathlib import Path

from airflow_lite.config.dag_loader import (
    load_dag_pipelines,
    migrate_sqlite_pipelines_to_dag_file_if_needed,
    resolve_dags_dir,
)
from airflow_lite.storage.database import Database


def test_load_dag_pipelines_reads_public_python_files(tmp_path):
    dags_dir = tmp_path / "dags"
    dags_dir.mkdir(parents=True, exist_ok=True)
    (dags_dir / "default.py").write_text(
        """\
from airflow_lite.dag_api import Pipeline

pipelines = [
    Pipeline(
        id="orders_sync",
        table="ORDERS",
        source_where_template="COL >= :data_interval_start",
        strategy="full",
        schedule="0 2 * * *",
        chunk_size=2000,
        columns=["ID", "COL"],
    ),
]
""",
        encoding="utf-8",
    )

    pipelines = load_dag_pipelines(dags_dir)

    assert len(pipelines) == 1
    assert pipelines[0].name == "orders_sync"
    assert pipelines[0].table == "ORDERS"
    assert pipelines[0].chunk_size == 2000
    assert pipelines[0].columns == ["ID", "COL"]


def test_load_dag_pipelines_skips_private_python_files(tmp_path):
    dags_dir = tmp_path / "dags"
    dags_dir.mkdir(parents=True, exist_ok=True)
    (dags_dir / "_private.py").write_text(
        """\
from airflow_lite.dag_api import Pipeline
pipelines = [Pipeline(id="private", table="PRIVATE_TABLE")]
""",
        encoding="utf-8",
    )

    pipelines = load_dag_pipelines(dags_dir)

    assert pipelines == []


def test_load_dag_pipelines_ignores_import_error_files(tmp_path):
    dags_dir = tmp_path / "dags"
    dags_dir.mkdir(parents=True, exist_ok=True)
    (dags_dir / "broken.py").write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    (dags_dir / "ok.py").write_text(
        """\
from airflow_lite.dag_api import Pipeline
pipelines = [Pipeline(id="ok", table="OK_TABLE")]
""",
        encoding="utf-8",
    )

    pipelines = load_dag_pipelines(dags_dir)

    assert len(pipelines) == 1
    assert pipelines[0].name == "ok"


def test_migrate_sqlite_pipelines_to_dag_file_if_needed(tmp_path):
    db_path = tmp_path / "legacy.db"
    database = Database(str(db_path))
    database.initialize()
    with database.connection() as conn:
        conn.execute(
            """
            CREATE TABLE pipeline_configs (
                name TEXT PRIMARY KEY,
                source_table TEXT NOT NULL,
                source_where_template TEXT,
                source_bind_params TEXT,
                strategy TEXT NOT NULL,
                schedule TEXT NOT NULL,
                chunk_size INTEGER,
                columns TEXT,
                incremental_key TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO pipeline_configs
            (name, source_table, source_where_template, source_bind_params, strategy, schedule, chunk_size, columns, incremental_key)
            VALUES
            ('production_log', 'PRODUCTION_LOG', 'LOG_DATE >= :data_interval_start', NULL, 'full', '0 2 * * *', 5000, 'LOG_ID,LOG_DATE', NULL)
            """
        )
        conn.commit()

    dags_dir = tmp_path / "dags"
    generated = migrate_sqlite_pipelines_to_dag_file_if_needed(str(db_path), dags_dir)

    assert generated == dags_dir / "_migrated.py"
    assert generated is not None
    assert generated.exists()

    loaded = load_dag_pipelines(dags_dir)
    assert len(loaded) == 1
    assert loaded[0].name == "production_log"
    assert loaded[0].table == "PRODUCTION_LOG"


def test_resolve_dags_dir_uses_project_root_when_config_dir_name_matches(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "pipelines.yaml"
    config_path.write_text("storage:\n  parquet_base_path: x\n  sqlite_path: y\n  log_path: z\n", encoding="utf-8")

    dags_dir = resolve_dags_dir(str(config_path))

    assert dags_dir == tmp_path / "dags"


def test_resolve_dags_dir_returns_disabled_path_when_config_file_missing(tmp_path):
    dags_dir = resolve_dags_dir(str(tmp_path / "missing.yaml"))

    assert dags_dir == tmp_path / "_dags_disabled"
