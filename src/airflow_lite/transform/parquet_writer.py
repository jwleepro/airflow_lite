import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger("airflow_lite.transform.parquet_writer")


class ParquetWriter:
    """Parquet 파일 직렬화 (Snappy 압축).

    파티셔닝 구조:
        {base_path}/{TABLE_NAME}/year={YYYY}/month={MM}/
            {TABLE_NAME}_{YYYY}_{MM}.parquet

    row group 단위로 append하여 메모리 사용 최소화.
    """

    def __init__(self, base_path: str, compression: str = "snappy"):
        self.base_path = Path(base_path)
        self.compression = compression
        self._active_writers: dict[tuple[str, int, int], pq.ParquetWriter] = {}

    def _partition_key(self, table_name: str, year: int, month: int) -> tuple[str, int, int]:
        return table_name, year, month

    def _get_paths(self, table_name: str, year: int, month: int) -> tuple[Path, Path]:
        output_dir = (
            self.base_path / table_name / f"year={year:04d}" / f"month={month:02d}"
        )
        output_file = output_dir / f"{table_name}_{year:04d}_{month:02d}.parquet"
        return output_dir, output_file

    def _list_partition_files(
        self, table_name: str, year: int, month: int, *, suffix: str
    ) -> list[Path]:
        output_dir, output_file = self._get_paths(table_name, year, month)
        if not output_dir.exists():
            return []
        return sorted(
            path
            for path in output_dir.glob(f"{output_file.stem}*{suffix}")
            if path.suffix == suffix
        )

    def _list_parquet_files(self, table_name: str, year: int, month: int) -> list[Path]:
        return self._list_partition_files(table_name, year, month, suffix=".parquet")

    def _list_backup_files(self, table_name: str, year: int, month: int) -> list[Path]:
        return self._list_partition_files(table_name, year, month, suffix=".bak")

    def finalize_partition(self, table_name: str, year: int, month: int) -> None:
        key = self._partition_key(table_name, year, month)
        writer = self._active_writers.pop(key, None)
        if writer is not None:
            writer.close()

    def _next_chunk_file(self, table_name: str, year: int, month: int) -> Path:
        output_dir, output_file = self._get_paths(table_name, year, month)
        part_index = len(self._list_parquet_files(table_name, year, month))
        return output_dir / f"{output_file.stem}.part{part_index:05d}.parquet"

    def write_chunk(
        self,
        table: pa.Table,
        table_name: str,
        year: int,
        month: int,
        append: bool = False,
        append_mode: str = "sidecar",
    ) -> Path:
        """PyArrow Table을 Parquet 파일로 저장.

        - 디렉터리 자동 생성
        - append_mode="single_file": 같은 parquet 파일에 row group 추가
        - append_mode="sidecar": append 시 part parquet 파일 추가 생성
        - append=False: 새 파일 생성 (기존 파일 덮어쓰기)
        """
        output_dir, output_file = self._get_paths(table_name, year, month)
        output_dir.mkdir(parents=True, exist_ok=True)

        if append_mode == "single_file":
            key = self._partition_key(table_name, year, month)
            if not append:
                self.finalize_partition(table_name, year, month)
                writer = pq.ParquetWriter(
                    str(output_file),
                    table.schema,
                    compression=self.compression,
                )
                self._active_writers[key] = writer
                writer.write_table(table)
                return output_file

            writer = self._active_writers.get(key)
            if writer is None:
                raise RuntimeError(
                    "single_file append requires an active writer; "
                    "write the first chunk with append=False."
                )
            writer.write_table(table)
            return output_file

        if append and self._list_parquet_files(table_name, year, month):
            chunk_file = self._next_chunk_file(table_name, year, month)
            pq.write_table(table, str(chunk_file), compression=self.compression)
            return chunk_file

        self.finalize_partition(table_name, year, month)
        pq.write_table(table, str(output_file), compression=self.compression)

        return output_file

    def backup_existing(self, table_name: str, year: int, month: int) -> bool:
        """기존 Parquet 파일을 .bak으로 이동. 파일이 없으면 False 반환."""
        self.finalize_partition(table_name, year, month)
        parquet_files = self._list_parquet_files(table_name, year, month)
        if not parquet_files:
            return False

        for parquet_file in parquet_files:
            bak_file = parquet_file.with_suffix(".bak")
            parquet_file.rename(bak_file)
            logger.info("기존 파일 백업: %s -> %s", parquet_file, bak_file)
        return True

    def remove_partition_files(self, table_name: str, year: int, month: int) -> int:
        """현재 파티션의 parquet 파일을 모두 삭제한다."""
        self.finalize_partition(table_name, year, month)
        removed = 0
        for parquet_file in self._list_parquet_files(table_name, year, month):
            parquet_file.unlink()
            removed += 1
            logger.info("파티션 파일 삭제: %s", parquet_file)
        return removed

    def remove_backups(self, table_name: str, year: int, month: int) -> int:
        """성공 후 남아 있는 .bak 파일을 정리한다."""
        removed = 0
        for bak_file in self._list_backup_files(table_name, year, month):
            bak_file.unlink()
            removed += 1
            logger.info("백업 파일 삭제: %s", bak_file)
        return removed

    def restore_backups(self, table_name: str, year: int, month: int) -> int:
        """실패 시 현재 출력물을 제거하고 .bak 파일을 원래 parquet 이름으로 복원한다."""
        self.finalize_partition(table_name, year, month)
        self.remove_partition_files(table_name, year, month)

        restored = 0
        for bak_file in self._list_backup_files(table_name, year, month):
            parquet_file = bak_file.with_suffix(".parquet")
            bak_file.rename(parquet_file)
            restored += 1
            logger.info("백업 파일 복원: %s -> %s", bak_file, parquet_file)
        return restored

    def count_rows(self, table_name: str, year: int, month: int) -> int:
        """Parquet 파일의 행 수 반환. 파일이 없으면 0."""
        self.finalize_partition(table_name, year, month)
        total_rows = 0
        for parquet_file in self._list_parquet_files(table_name, year, month):
            metadata = pq.read_metadata(str(parquet_file))
            total_rows += metadata.num_rows
        return total_rows
