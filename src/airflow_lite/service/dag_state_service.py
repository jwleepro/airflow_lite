"""Runtime DAG state management (pause/unpause)."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class DagStateService:
    """Manages runtime DAG states in a JSON file."""

    def __init__(self, state_file: Path | str):
        self._path = Path(state_file)
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def is_paused(self, dag_id: str) -> bool | None:
        """Return paused state. None if not explicitly set."""
        data = self._load()
        return data.get(dag_id, {}).get("paused")

    def set_paused(self, dag_id: str, paused: bool) -> None:
        with self._lock:
            data = self._load()
            if dag_id not in data:
                data[dag_id] = {}
            data[dag_id]["paused"] = paused
            self._save(data)

    def get_effective_paused(self, dag_id: str, config_paused: bool) -> bool:
        """Return effective paused state (runtime overrides config)."""
        runtime_paused = self.is_paused(dag_id)
        if runtime_paused is not None:
            return runtime_paused
        return config_paused
