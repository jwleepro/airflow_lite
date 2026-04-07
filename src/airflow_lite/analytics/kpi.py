from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from airflow_lite.api.analytics_contracts import SummaryMetricCard, SummaryPrecision


@dataclass(frozen=True)
class DatasetSummaryStats:
    total_rows: int
    total_files: int
    source_tables: int
    min_partition_start: date | None
    max_partition_start: date | None


def build_dataset_summary_metrics(dataset: str, stats: DatasetSummaryStats) -> list[SummaryMetricCard]:
    covered_months = _count_inclusive_months(stats.min_partition_start, stats.max_partition_start)
    average_rows = round(stats.total_rows / stats.total_files, 2) if stats.total_files else 0.0

    return [
        SummaryMetricCard(
            key="rows_loaded",
            label="Rows Loaded",
            value=stats.total_rows,
            precision=SummaryPrecision.INTEGER,
            unit="rows",
        ),
        SummaryMetricCard(
            key="source_files",
            label="Source Files",
            value=stats.total_files,
            precision=SummaryPrecision.INTEGER,
            unit="files",
        ),
        SummaryMetricCard(
            key="source_tables",
            label="Source Tables",
            value=stats.source_tables,
            precision=SummaryPrecision.INTEGER,
            unit="tables",
        ),
        SummaryMetricCard(
            key="avg_rows_per_file",
            label="Avg Rows per File",
            value=average_rows,
            precision=SummaryPrecision.DECIMAL,
            unit="rows",
        ),
        SummaryMetricCard(
            key="covered_months",
            label="Covered Months",
            value=covered_months,
            precision=SummaryPrecision.INTEGER,
            unit="months",
        ),
    ]


def _count_inclusive_months(start: date | None, end: date | None) -> int:
    if start is None or end is None:
        return 0
    return ((end.year - start.year) * 12) + (end.month - start.month) + 1
