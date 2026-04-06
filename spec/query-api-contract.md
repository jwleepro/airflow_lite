# Query API Contract

## Goal

Define stable summary and chart contracts for the DuckDB-backed analytics layer before endpoint implementation starts.

## Endpoint Boundaries

- `GET /api/v1/analytics/dashboards/{dashboard_id}`
  Returns dashboard-ready metadata describing which summary, chart, filter, drilldown, and export affordances the UI should render.
- `POST /api/v1/analytics/summary`
  Returns KPI cards only. No row-level detail.
- `POST /api/v1/analytics/charts/{chart_id}/query`
  Returns chart-ready series payloads only.
- `GET /api/v1/analytics/filters`
  Returns filter metadata and allowed options for the selected dataset.

Detail rows, export jobs, and admin refresh visibility stay out of this document.

## Dashboard Definition Contract

```json
{
  "dashboard_id": "operations_overview",
  "title": "MES Operations Overview",
  "dataset": "mes_ops",
  "last_refreshed_at": "2026-04-06T10:00:00",
  "filters": [
    {
      "key": "source",
      "label": "Source Table",
      "type": "multi_select",
      "supports_multiple": true,
      "options": [
        {"value": "OPS_TABLE", "label": "OPS_TABLE"}
      ]
    }
  ],
  "cards": [
    {
      "key": "rows_loaded",
      "label": "Rows Loaded",
      "metric_key": "rows_loaded",
      "summary_endpoint": "/api/v1/analytics/summary",
      "span": "small"
    }
  ],
  "charts": [
    {
      "chart_id": "rows_by_month",
      "title": "Rows by Month",
      "chart_type": "line",
      "default_granularity": "month",
      "query_endpoint": "/api/v1/analytics/charts/rows_by_month/query",
      "limit": 12,
      "span": "large"
    }
  ],
  "drilldown_actions": [
    {
      "key": "source_file_detail",
      "label": "Source File Detail",
      "type": "drilldown",
      "status": "planned"
    }
  ],
  "export_actions": [
    {
      "key": "csv_zip_export",
      "label": "CSV Zip Export",
      "type": "export",
      "status": "planned",
      "format": "csv.zip"
    }
  ],
  "warnings": [
    "Detail drilldown and export jobs are planned follow-up work and are not executable yet."
  ]
}
```

## Common Request Rules

- Every request targets one logical `dataset`.
- Date windows use `{start, end}`.
- Filter values are server-validated keys and values, not free-form SQL snippets.
- Multi-select filters are arrays of strings.
- Pagination is not part of summary and chart contracts.

## Summary Request

```json
{
  "dataset": "mes_ops",
  "window": {
    "start": "2026-03-01",
    "end": "2026-03-31"
  },
  "filters": {
    "plant": ["P1"],
    "line": ["L1", "L2"]
  }
}
```

## Summary Response

```json
{
  "dataset": "mes_ops",
  "generated_at": "2026-03-31T09:00:00",
  "filters_applied": {
    "plant": ["P1"],
    "line": ["L1", "L2"]
  },
  "metrics": [
    {
      "key": "throughput",
      "label": "Throughput",
      "value": 1280,
      "precision": "integer",
      "unit": "ea",
      "delta": 4.2,
      "comparison_label": "vs previous period"
    }
  ],
  "warnings": []
}
```

## Chart Request

```json
{
  "dataset": "mes_ops",
  "chart_id": "daily_throughput",
  "granularity": "day",
  "limit": 31,
  "window": {
    "start": "2026-03-01",
    "end": "2026-03-31"
  },
  "filters": {
    "plant": ["P1"],
    "line": ["L1"]
  }
}
```

## Chart Response

```json
{
  "dataset": "mes_ops",
  "chart_id": "daily_throughput",
  "title": "Daily Throughput",
  "granularity": "day",
  "filters_applied": {
    "plant": ["P1"],
    "line": ["L1"]
  },
  "series": [
    {
      "key": "actual",
      "label": "Actual",
      "points": [
        {"bucket": "2026-03-01", "value": 100},
        {"bucket": "2026-03-02", "value": 110}
      ]
    }
  ],
  "warnings": []
}
```

## Filter Metadata Contract

```json
{
  "dataset": "mes_ops",
  "filters": [
    {
      "key": "plant",
      "label": "Plant",
      "type": "select",
      "required": false,
      "supports_multiple": false,
      "options": [
        {"value": "P1", "label": "Plant 1"}
      ]
    }
  ]
}
```

## Design Constraints

- Summary payloads must stay small enough for one dashboard refresh.
- Chart payloads must be directly renderable without client-side regrouping.
- Free-form sorting, projection, and SQL are out of scope.
- Exports must use separate endpoints and job lifecycle handling.

## Code Mapping

- `src/airflow_lite/api/analytics_contracts.py`
  Owns the Pydantic request and response models for this draft.
- Future `T-015`
  Should implement routes and query services against the DuckDB mart using these contracts.
