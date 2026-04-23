from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path

from airflow_lite.dag_api import Pipeline

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


