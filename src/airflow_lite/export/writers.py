from __future__ import annotations

import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as papq

from airflow_lite.query.contracts import ExportFormat

ZIP_COMPRESSION_MAP: dict[str, int] = {
    "deflated": zipfile.ZIP_DEFLATED,
    "stored": zipfile.ZIP_STORED,
}


def resolve_zip_compression(zip_compression: str) -> int:
    try:
        return ZIP_COMPRESSION_MAP[zip_compression.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported zip compression: {zip_compression}") from exc


class ExportWriter(ABC):
    @abstractmethod
    def write(self, artifact_path: Path, reader: Iterable) -> int:
        ...


class ParquetExportWriter(ExportWriter):
    def __init__(self, compression: str = "snappy"):
        self.compression = compression

    def write(self, artifact_path: Path, reader) -> int:
        row_count = 0
        with papq.ParquetWriter(
            str(artifact_path), reader.schema, compression=self.compression
        ) as writer:
            for batch in reader:
                writer.write_batch(batch)
                row_count += batch.num_rows
        return row_count


class CsvZipExportWriter(ExportWriter):
    def __init__(self, zip_compression: str = "deflated"):
        self._zip_compression = resolve_zip_compression(zip_compression)

    def write(self, artifact_path: Path, reader) -> int:
        row_count = 0
        csv_name = f"{artifact_path.stem}.csv"
        csv_path = artifact_path.with_suffix(".csv")
        with pa.OSFile(str(csv_path), "wb") as sink:
            with pacsv.CSVWriter(sink, reader.schema) as writer:
                for batch in reader:
                    writer.write_batch(batch)
                    row_count += batch.num_rows

        with zipfile.ZipFile(
            artifact_path, "w", compression=self._zip_compression
        ) as archive:
            archive.write(csv_path, arcname=csv_name)

        csv_path.unlink()
        return row_count


def build_export_writers(
    *, parquet_compression: str, zip_compression: str
) -> dict[ExportFormat, ExportWriter]:
    return {
        ExportFormat.PARQUET: ParquetExportWriter(compression=parquet_compression),
        ExportFormat.CSV_ZIP: CsvZipExportWriter(zip_compression=zip_compression),
    }
