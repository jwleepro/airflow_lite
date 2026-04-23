from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from airflow_lite.query.contracts import SummaryMetricCard, SummaryPrecision
from airflow_lite.i18n import DEFAULT_LANGUAGE, translate


@dataclass(frozen=True)
class DatasetSummaryStats:
    total_rows: int
    total_files: int
    source_tables: int
    min_partition_start: date | None
    max_partition_start: date | None


def build_dataset_summary_metrics(
    dataset: str,
    stats: DatasetSummaryStats,
    *,
    language: str = DEFAULT_LANGUAGE,
) -> list[SummaryMetricCard]:
    covered_months = _count_inclusive_months(stats.min_partition_start, stats.max_partition_start)
    average_rows = round(stats.total_rows / stats.total_files, 2) if stats.total_files else 0.0

    return [
        SummaryMetricCard(
            key="rows_loaded",
            label=translate("analytics.metric.rows_loaded.label", language),
            value=stats.total_rows,
            precision=SummaryPrecision.INTEGER,
            unit=translate("analytics.metric.rows_loaded.unit", language),
        ),
        SummaryMetricCard(
            key="source_files",
            label=translate("analytics.metric.source_files.label", language),
            value=stats.total_files,
            precision=SummaryPrecision.INTEGER,
            unit=translate("analytics.metric.source_files.unit", language),
        ),
        SummaryMetricCard(
            key="source_tables",
            label=translate("analytics.metric.source_tables.label", language),
            value=stats.source_tables,
            precision=SummaryPrecision.INTEGER,
            unit=translate("analytics.metric.source_tables.unit", language),
        ),
        SummaryMetricCard(
            key="avg_rows_per_file",
            label=translate("analytics.metric.avg_rows_per_file.label", language),
            value=average_rows,
            precision=SummaryPrecision.DECIMAL,
            unit=translate("analytics.metric.avg_rows_per_file.unit", language),
        ),
        SummaryMetricCard(
            key="covered_months",
            label=translate("analytics.metric.covered_months.label", language),
            value=covered_months,
            precision=SummaryPrecision.INTEGER,
            unit=translate("analytics.metric.covered_months.unit", language),
        ),
    ]


def _count_inclusive_months(start: date | None, end: date | None) -> int:
    if start is None or end is None:
        return 0
    return ((end.year - start.year) * 12) + (end.month - start.month) + 1
