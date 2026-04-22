
from airflow_lite.config.dag_loader import load_dag_pipelines, resolve_dags_dir


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
