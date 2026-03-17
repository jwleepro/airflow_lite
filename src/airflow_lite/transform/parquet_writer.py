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

    def _get_paths(self, table_name: str, year: int, month: int) -> tuple[Path, Path]:
        output_dir = (
            self.base_path / table_name / f"year={year:04d}" / f"month={month:02d}"
        )
        output_file = output_dir / f"{table_name}_{year:04d}_{month:02d}.parquet"
        return output_dir, output_file

    def write_chunk(
        self,
        table: pa.Table,
        table_name: str,
        year: int,
        month: int,
        append: bool = False,
    ) -> Path:
        """PyArrow Table을 Parquet 파일로 저장.

        - 디렉터리 자동 생성
        - append=True: 기존 파일에 row group 추가 (읽고 병합 후 재저장)
        - append=False: 새 파일 생성 (기존 파일 덮어쓰기)
        """
        output_dir, output_file = self._get_paths(table_name, year, month)
        output_dir.mkdir(parents=True, exist_ok=True)

        if append and output_file.exists():
            # ParquetFile로 직접 읽어 Hive 파티션 경로에서 컬럼이 자동 추가되는 것을 방지
            existing = pq.ParquetFile(str(output_file)).read()
            merged = pa.concat_tables([existing, table])
            pq.write_table(merged, str(output_file), compression=self.compression)
        else:
            pq.write_table(table, str(output_file), compression=self.compression)

        return output_file

    def backup_existing(self, table_name: str, year: int, month: int) -> bool:
        """기존 Parquet 파일을 .bak으로 이동. 파일이 없으면 False 반환."""
        _, output_file = self._get_paths(table_name, year, month)
        if output_file.exists():
            bak_file = output_file.with_suffix(".bak")
            output_file.rename(bak_file)
            logger.info("기존 파일 백업: %s -> %s", output_file, bak_file)
            return True
        return False

    def count_rows(self, table_name: str, year: int, month: int) -> int:
        """Parquet 파일의 행 수 반환. 파일이 없으면 0."""
        _, output_file = self._get_paths(table_name, year, month)
        if not output_file.exists():
            return 0
        metadata = pq.read_metadata(str(output_file))
        return metadata.num_rows
