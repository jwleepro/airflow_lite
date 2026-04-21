from __future__ import annotations

import importlib.util
import logging
import os
import sqlite3
from pathlib import Path

from airflow_lite.dag_api import Pipeline
from airflow_lite.pipeline_config_validation import coerce_source_query_from_mapping
from airflow_lite.storage._sqlite_schema import table_columns, table_exists

if False:  # pragma: no cover
    from airflow_lite.config.settings import PipelineConfig

logger = logging.getLogger("airflow_lite.config.dag_loader")


def resolve_dags_dir(config_path: str) -> Path:
    env_value = os.environ.get("AIRFLOW_LITE_DAGS_DIR")
    if env_value:
        return Path(env_value).expanduser()

    config_file = Path(config_path).resolve()
    if not config_file.exists():
        return config_file.parent / "_dags_disabled"
    if config_file.parent.name.lower() == "config":
        return config_file.parent.parent / "dags"
    return config_file.parent / "dags"


def load_dag_pipelines(dags_dir: Path) -> list["PipelineConfig"]:
    from airflow_lite.config.settings import PipelineConfig

    if not dags_dir.exists():
        return []

    pipelines: list[PipelineConfig] = []
    dag_files = sorted(
        dags_dir.glob("*.py"),
        key=lambda path: (path.name == "_migrated.py", path.name),
    )
    for dag_file in dag_files:
        if dag_file.name.startswith("_") and dag_file.name != "_migrated.py":
            continue
        module_name = f"airflow_lite_dag_{dag_file.stem}_{abs(hash(str(dag_file)))}"
        module = _import_module_from_path(module_name, dag_file)
        if module is None:
            continue

        raw = getattr(module, "pipelines", None)
        if raw is None:
            continue
        if not isinstance(raw, (list, tuple)):
            logger.warning("Skipping %s: pipelines must be list/tuple.", dag_file)
            continue

        for item in raw:
            if isinstance(item, Pipeline):
                pipelines.append(item.to_pipeline_config())
            elif isinstance(item, PipelineConfig):
                pipelines.append(item)
            else:
                logger.warning(
                    "Skipping unsupported pipeline object in %s: %s",
                    dag_file,
                    type(item).__name__,
                )
    return pipelines


def migrate_sqlite_pipelines_to_dag_file_if_needed(sqlite_path: str, dags_dir: Path) -> Path | None:
    existing_user_dags = [path for path in dags_dir.glob("*.py") if not path.name.startswith("_")]
    allow_migration_with_default_only = (
        len(existing_user_dags) == 1 and existing_user_dags[0].name == "default.py"
    )
    if existing_user_dags and not allow_migration_with_default_only:
        return None

    db_path = Path(sqlite_path)
    if not db_path.exists():
        return None

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        if not table_exists(connection, "pipeline_configs"):
            return None

        columns = table_columns(connection, "pipeline_configs")
        required = ["name", "source_table", "strategy", "schedule", "chunk_size", "columns", "incremental_key"]
        if any(col not in columns for col in required):
            return None

        optional_columns = [
            col for col in ("source_where_template", "source_bind_params", "partition_column") if col in columns
        ]
        select_columns = required[:2] + optional_columns + required[2:]
        rows = connection.execute(
            f"SELECT {', '.join(select_columns)} FROM pipeline_configs ORDER BY name"
        ).fetchall()
        if not rows:
            return None
    finally:
        connection.close()

    dags_dir.mkdir(parents=True, exist_ok=True)
    migrated_path = dags_dir / "_migrated.py"
    with migrated_path.open("w", encoding="utf-8") as file:
        file.write("from airflow_lite.dag_api import Pipeline\n\n")
        file.write("pipelines = [\n")
        for row in rows:
            row_dict = dict(row)
            source_where_template, source_bind_params = coerce_source_query_from_mapping(
                row_dict, strategy=row_dict["strategy"]
            )
            file.write("    Pipeline(\n")
            file.write(f"        id={row_dict['name']!r},\n")
            file.write(f"        table={row_dict['source_table']!r},\n")
            if source_where_template is not None:
                file.write(f"        source_where_template={source_where_template!r},\n")
            if source_bind_params:
                file.write(f"        source_bind_params={source_bind_params!r},\n")
            file.write(f"        strategy={row_dict['strategy']!r},\n")
            file.write(f"        schedule={row_dict['schedule']!r},\n")
            if row_dict["chunk_size"] is not None:
                file.write(f"        chunk_size={int(row_dict['chunk_size'])!r},\n")
            columns_list = _columns_from_text(row_dict.get("columns"))
            if columns_list:
                file.write(f"        columns={columns_list!r},\n")
            if row_dict.get("incremental_key"):
                file.write(f"        incremental_key={row_dict['incremental_key']!r},\n")
            file.write("    ),\n")
        file.write("]\n")

    logger.warning(
        "pipeline_configs -> %s migration completed. Pipeline definitions now come from DAG files.",
        migrated_path,
    )
    return migrated_path


def _import_module_from_path(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        logger.warning("Failed to load DAG module spec: %s", module_path)
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        logger.exception("Failed to import DAG file: %s", module_path)
        return None
    return module


def _columns_from_text(value: str | None) -> list[str] | None:
    if not value:
        return None
    columns = [col.strip() for col in str(value).split(",") if col.strip()]
    return columns or None
