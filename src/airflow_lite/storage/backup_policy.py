"""파일 .bak 백업/복구/정리 공통 로직.

ParquetWriter 와 BackfillManager 에서 중복하던 .bak 백업 로직을
단일 모듈로 통합한다.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileBackupPolicy:
    """단일 파일에 대한 .bak 백업/복구/정리."""

    @staticmethod
    def backup(path: Path) -> Path | None:
        """파일을 .bak으로 이동. 파일이 없으면 None."""
        if not path.exists():
            return None
        bak_path = path.with_suffix(path.suffix + ".bak")
        if bak_path.exists():
            bak_path.unlink()
        path.replace(bak_path)
        logger.info("기존 파일 백업: %s -> %s", path, bak_path)
        return bak_path

    @staticmethod
    def restore(backup_path: Path) -> None:
        """.bak를 원본 경로로 복원."""
        if not backup_path.exists():
            return
        original_path = backup_path.with_suffix("")
        if original_path.exists():
            original_path.unlink()
        backup_path.replace(original_path)
        logger.info("백업 파일 복원: %s -> %s", backup_path, original_path)

    @staticmethod
    def remove(backup_path: Path | None) -> None:
        """백업 파일을 삭제. None/미존재는 무시."""
        if not backup_path:
            return
        try:
            path = Path(backup_path)
            if path.exists():
                path.unlink()
        except OSError:
            pass


class PartitionBackupPolicy:
    """파티션 디렉토리 내 파일 배치 백업/복구/정리."""

    @staticmethod
    def backup_all(directory: Path) -> list[Path]:
        """디렉토리 내 .parquet 파일을 .bak으로 이동. 이미 백업된 파일은 건너뜀."""
        backed_up: list[Path] = []
        for parquet_file in sorted(directory.glob("*.parquet")):
            bak_file = parquet_file.with_suffix(".bak")
            if bak_file.exists():
                continue
            parquet_file.rename(bak_file)
            logger.info("기존 파일 백업: %s -> %s", parquet_file, bak_file)
            backed_up.append(bak_file)
        return backed_up

    @staticmethod
    def restore_all(directory: Path, backed_up: list[Path]) -> list[Path]:
        """.bak 파일을 .parquet로 복원."""
        restored: list[Path] = []
        for bak_file in backed_up:
            if not bak_file.exists():
                continue
            parquet_file = bak_file.with_suffix(".parquet")
            if parquet_file.exists():
                parquet_file.unlink()
            bak_file.rename(parquet_file)
            logger.info("백업 파일 복원: %s -> %s", bak_file, parquet_file)
            restored.append(parquet_file)
        return restored

    @staticmethod
    def remove_all(directory: Path) -> int:
        """디렉토리 내 .parquet 파일 모두 삭제."""
        removed = 0
        for parquet_file in sorted(directory.glob("*.parquet")):
            parquet_file.unlink()
            removed += 1
            logger.info("파티션 파일 삭제: %s", parquet_file)
        return removed

    @staticmethod
    def remove_backups(directory: Path) -> int:
        """디렉토리 내 .bak 파일 모두 삭제."""
        removed = 0
        for bak_file in sorted(directory.glob("*.bak")):
            bak_file.unlink()
            removed += 1
            logger.info("백업 파일 삭제: %s", bak_file)
        return removed
