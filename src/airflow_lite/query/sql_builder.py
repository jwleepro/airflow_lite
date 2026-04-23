from __future__ import annotations

from datetime import date

from airflow_lite.query.contracts import (
    DetailColumnDefinition,
    DetailColumnType,
    DetailSortField,
    ExportFormat,
    SortDirection,
)


class AnalyticsQueryError(ValueError):
    pass


class AnalyticsSQLBuilder:
    """Analytics 쿼리용 SQL 조건절/정렬/검증 빌더.

    DuckDB 쿼리 서비스에서 SQL 조립 로직만 분리하여 단독 테스트 가능하게 한다.
    """

    SUPPORTED_FILTERS = frozenset({"source", "partition_month"})
    SUPPORTED_DETAILS = frozenset({"source-files"})

    DETAIL_COLUMN_SPECS: dict[str, list[tuple[str, DetailColumnType, str]]] = {
        "source-files": [
            ("source_name", DetailColumnType.STRING, "analytics.detail.column.source_name"),
            ("partition_month", DetailColumnType.DATE, "analytics.detail.column.partition_month"),
            ("file_path", DetailColumnType.STRING, "analytics.detail.column.file_path"),
            ("row_count", DetailColumnType.INTEGER, "analytics.detail.column.row_count"),
            ("last_build_id", DetailColumnType.STRING, "analytics.detail.column.last_build_id"),
        ]
    }

    DETAIL_SORT_FIELDS: dict[str, dict[str, str]] = {
        "source-files": {
            "source_name": "source_name",
            "partition_month": "partition_start",
            "file_path": "file_path",
            "row_count": "row_count",
            "last_build_id": "last_build_id",
        }
    }

    DEFAULT_DETAIL_SORT: dict[str, list[DetailSortField]] = {
        "source-files": [
            DetailSortField(field="partition_month", direction=SortDirection.DESC),
            DetailSortField(field="source_name", direction=SortDirection.ASC),
            DetailSortField(field="file_path", direction=SortDirection.ASC),
        ]
    }

    EXPORT_ACTIONS: dict[str, ExportFormat] = {
        "xlsx_export": ExportFormat.XLSX,
        "csv_zip_export": ExportFormat.CSV_ZIP,
        "parquet_export": ExportFormat.PARQUET,
    }

    def ensure_supported_filters(self, filters: dict[str, list[str]]) -> None:
        unsupported = sorted(set(filters) - self.SUPPORTED_FILTERS)
        if unsupported:
            raise AnalyticsQueryError(f"unsupported filters: {', '.join(unsupported)}")

    def build_file_filters(
        self,
        dataset: str,
        filters: dict[str, list[str]],
        start: date | None,
        end: date | None,
    ) -> tuple[str, list]:
        conditions = ["dataset_name = ?"]
        params: list = [dataset]

        if start is not None:
            conditions.append("partition_start >= ?")
            params.append(date(start.year, start.month, 1))
        if end is not None:
            conditions.append("partition_start <= ?")
            params.append(date(end.year, end.month, 1))
        if filters.get("source"):
            placeholders = ", ".join("?" for _ in filters["source"])
            conditions.append(f"source_name IN ({placeholders})")
            params.extend(filters["source"])
        if filters.get("partition_month"):
            month_values = [self.parse_partition_month(value) for value in filters["partition_month"]]
            placeholders = ", ".join("?" for _ in month_values)
            conditions.append(f"partition_start IN ({placeholders})")
            params.extend(month_values)

        return " AND ".join(conditions), params

    def build_detail_select_sql(self, detail_key: str) -> str:
        if detail_key not in self.SUPPORTED_DETAILS:
            raise AnalyticsQueryError(f"unsupported detail_key: {detail_key}")
        return """
            SELECT
                source_name,
                partition_start AS partition_month,
                file_path,
                row_count,
                last_build_id
            FROM mart_dataset_files
        """

    def build_detail_sort_sql(self, detail_key: str, sort_fields: list[DetailSortField]) -> str:
        allowed_fields = self.DETAIL_SORT_FIELDS.get(detail_key)
        if allowed_fields is None:
            raise AnalyticsQueryError(f"unsupported detail_key: {detail_key}")

        order_terms: list[str] = []
        for sort_field in sort_fields:
            column_name = allowed_fields.get(sort_field.field)
            if column_name is None:
                raise AnalyticsQueryError(
                    f"unsupported sort field for {detail_key}: {sort_field.field}"
                )
            direction = "DESC" if sort_field.direction is SortDirection.DESC else "ASC"
            order_terms.append(f"{column_name} {direction}")

        return ", ".join(order_terms)

    def build_detail_columns(
        self, detail_key: str, translate_fn
    ) -> list[DetailColumnDefinition]:
        return [
            DetailColumnDefinition(
                key=key,
                label=translate_fn(label_key),
                type=column_type,
            )
            for key, column_type, label_key in self.DETAIL_COLUMN_SPECS[detail_key]
        ]

    @staticmethod
    def parse_partition_month(value: str) -> date:
        try:
            year_text, month_text = value.split("-", maxsplit=1)
            return date(int(year_text), int(month_text), 1)
        except ValueError as exc:
            raise AnalyticsQueryError(f"invalid partition_month filter value: {value}") from exc
