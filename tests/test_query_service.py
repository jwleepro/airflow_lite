from datetime import datetime

import duckdb

from airflow_lite.api.analytics_contracts import ChartGranularity, ChartQueryRequest, DateRangeFilterValue, SummaryQueryRequest
from airflow_lite.query import (
    AnalyticsDashboardNotFoundError,
    AnalyticsQueryError,
    DuckDBAnalyticsQueryService,
)


def _build_test_mart(database_path):
    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
            """
            CREATE TABLE mart_datasets (
                dataset_name VARCHAR,
                source_count BIGINT,
                total_rows BIGINT,
                total_files BIGINT,
                min_partition_start DATE,
                max_partition_start DATE,
                last_refreshed_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE mart_dataset_sources (
                dataset_name VARCHAR,
                source_name VARCHAR,
                raw_table_name VARCHAR,
                source_root VARCHAR,
                row_count BIGINT,
                file_count BIGINT,
                min_partition_start DATE,
                max_partition_start DATE,
                last_build_id VARCHAR,
                refresh_mode VARCHAR,
                last_refreshed_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE mart_dataset_files (
                dataset_name VARCHAR,
                source_name VARCHAR,
                partition_start DATE,
                file_path VARCHAR,
                row_count BIGINT,
                last_build_id VARCHAR
            )
            """
        )
        connection.executemany(
            "INSERT INTO mart_dataset_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                [
                    "mes_ops",
                    "OPS_TABLE",
                    "raw__mes_ops__ops_table",
                    "D:/data/parquet/OPS_TABLE",
                    15,
                    2,
                    "2026-03-01",
                    "2026-04-01",
                    "build-001",
                    "full",
                    datetime(2026, 4, 6, 9, 0, 0),
                ],
                [
                    "mes_ops",
                    "EQUIPMENT_STATUS",
                    "raw__mes_ops__equipment_status",
                    "D:/data/parquet/EQUIPMENT_STATUS",
                    5,
                    1,
                    "2026-04-01",
                    "2026-04-01",
                    "build-002",
                    "incremental",
                    datetime(2026, 4, 6, 10, 0, 0),
                ],
            ],
        )
        connection.executemany(
            "INSERT INTO mart_dataset_files VALUES (?, ?, ?, ?, ?, ?)",
            [
                ["mes_ops", "OPS_TABLE", "2026-03-01", "march.parquet", 10, "build-001"],
                ["mes_ops", "OPS_TABLE", "2026-04-01", "april.parquet", 5, "build-001"],
                ["mes_ops", "EQUIPMENT_STATUS", "2026-04-01", "equipment.parquet", 5, "build-002"],
            ],
        )
        connection.execute(
            "INSERT INTO mart_datasets VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "mes_ops",
                2,
                20,
                3,
                "2026-03-01",
                "2026-04-01",
                datetime(2026, 4, 6, 10, 0, 0),
            ],
        )
    finally:
        connection.close()


def test_query_summary_aggregates_filtered_rows(tmp_path):
    database_path = tmp_path / "analytics.duckdb"
    _build_test_mart(database_path)
    service = DuckDBAnalyticsQueryService(database_path)

    response = service.query_summary(
        SummaryQueryRequest(
            dataset="mes_ops",
            window=DateRangeFilterValue(start="2026-04-01", end="2026-04-30"),
            filters={"source": ["OPS_TABLE"]},
        )
    )

    metrics = {metric.key: metric.value for metric in response.metrics}
    assert metrics["rows_loaded"] == 5
    assert metrics["source_files"] == 1
    assert metrics["source_tables"] == 1


def test_query_chart_rows_by_month_returns_bucketed_series(tmp_path):
    database_path = tmp_path / "analytics.duckdb"
    _build_test_mart(database_path)
    service = DuckDBAnalyticsQueryService(database_path)

    response = service.query_chart(
        ChartQueryRequest(
            dataset="mes_ops",
            chart_id="rows_by_month",
            granularity=ChartGranularity.MONTH,
            limit=12,
            filters={},
        )
    )

    assert response.title == "Rows by Month"
    assert [point.value for point in response.series[0].points] == [10, 10]


def test_query_filters_returns_source_and_partition_options(tmp_path):
    database_path = tmp_path / "analytics.duckdb"
    _build_test_mart(database_path)
    service = DuckDBAnalyticsQueryService(database_path)

    response = service.get_filter_metadata("mes_ops")

    filter_map = {item.key: item for item in response.filters}
    assert [option.value for option in filter_map["source"].options] == [
        "EQUIPMENT_STATUS",
        "OPS_TABLE",
    ]
    assert [option.value for option in filter_map["partition_month"].options] == [
        "2026-04",
        "2026-03",
    ]


def test_get_dashboard_definition_returns_dashboard_metadata(tmp_path):
    database_path = tmp_path / "analytics.duckdb"
    _build_test_mart(database_path)
    service = DuckDBAnalyticsQueryService(database_path)

    response = service.get_dashboard_definition("operations_overview", "mes_ops")

    assert response.contract_version == "dashboard.v1"
    assert response.dashboard_id == "operations_overview"
    assert response.dataset == "mes_ops"
    assert response.last_refreshed_at == datetime(2026, 4, 6, 10, 0, 0)
    assert [card.metric_key for card in response.cards] == [
        "rows_loaded",
        "source_files",
        "source_tables",
        "covered_months",
    ]
    assert [chart.chart_id for chart in response.charts] == [
        "rows_by_month",
        "files_by_source",
    ]
    assert response.cards[0].request_method.value == "POST"
    assert response.cards[0].filter_keys == ["source", "partition_month"]
    assert response.drilldown_actions[0].scope.value == "chart"
    assert response.drilldown_actions[0].target_key == "files_by_source"
    assert response.drilldown_actions[0].endpoint == "/api/v1/analytics/details/source-files/query"
    assert response.export_actions[0].status.value == "planned"
    assert response.export_actions[0].endpoint == "/api/v1/analytics/exports"
    assert response.export_actions[0].status_reason


def test_get_dashboard_definition_rejects_unknown_dashboard(tmp_path):
    database_path = tmp_path / "analytics.duckdb"
    _build_test_mart(database_path)
    service = DuckDBAnalyticsQueryService(database_path)

    try:
        service.get_dashboard_definition("unknown", "mes_ops")
    except AnalyticsDashboardNotFoundError as exc:
        assert "dashboard not found" in str(exc)
    else:
        raise AssertionError("AnalyticsDashboardNotFoundError was not raised")


def test_query_summary_rejects_unsupported_filters(tmp_path):
    database_path = tmp_path / "analytics.duckdb"
    _build_test_mart(database_path)
    service = DuckDBAnalyticsQueryService(database_path)

    try:
        service.query_summary(
            SummaryQueryRequest(dataset="mes_ops", filters={"plant": ["P1"]})
        )
    except AnalyticsQueryError as exc:
        assert "unsupported filters" in str(exc)
    else:
        raise AssertionError("AnalyticsQueryError was not raised")
