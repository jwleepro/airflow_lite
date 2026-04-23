from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SnapshotPaths:
    current_db_path: Path
    staging_db_path: Path
    snapshot_db_path: Path


@dataclass(frozen=True)
class MartSnapshotLayout:
    root_dir: Path
    database_filename: str = "analytics.duckdb"
    current_dirname: str = "current"
    staging_dirname: str = "staging"
    snapshots_dirname: str = "snapshots"

    @property
    def current_dir(self) -> Path:
        return self.root_dir / self.current_dirname

    @property
    def staging_dir(self) -> Path:
        return self.root_dir / self.staging_dirname

    @property
    def snapshots_dir(self) -> Path:
        return self.root_dir / self.snapshots_dirname

    def plan_paths(self, build_id: str, snapshot_name: str) -> SnapshotPaths:
        if not build_id.strip():
            raise ValueError("build_id must not be blank")
        if not snapshot_name.strip():
            raise ValueError("snapshot_name must not be blank")

        return SnapshotPaths(
            current_db_path=self.current_dir / self.database_filename,
            staging_db_path=self.staging_dir / build_id / self.database_filename,
            snapshot_db_path=self.snapshots_dir / snapshot_name / self.database_filename,
        )

    def ensure_directories(self, paths: SnapshotPaths) -> None:
        paths.current_db_path.parent.mkdir(parents=True, exist_ok=True)
        paths.staging_db_path.parent.mkdir(parents=True, exist_ok=True)
        paths.snapshot_db_path.parent.mkdir(parents=True, exist_ok=True)


class MartSnapshotPromoter:
    """Promote a validated staging DuckDB file into both snapshot and current locations."""

    def promote(self, paths: SnapshotPaths) -> None:
        if not paths.staging_db_path.exists():
            raise FileNotFoundError(paths.staging_db_path)

        paths.current_db_path.parent.mkdir(parents=True, exist_ok=True)
        paths.snapshot_db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(paths.staging_db_path, paths.snapshot_db_path)
        shutil.copy2(paths.staging_db_path, paths.current_db_path)
