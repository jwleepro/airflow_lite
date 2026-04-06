# Query API Contract

## Goal

Define a stable dashboard-consumption contract for the DuckDB-backed analytics layer and pin down the follow-on detail and export API boundaries before UI work starts.

## Endpoint Boundaries

- `GET /api/v1/analytics/dashboards/{dashboard_id}`
  Returns dashboard-ready metadata describing the widget layout, filter bindings, and planned follow-on actions the UI should render.
- `POST /api/v1/analytics/summary`
  Returns KPI cards only. No row-level detail.
- `POST /api/v1/analytics/charts/{chart_id}/query`
  Returns chart-ready series payloads only.
- `GET /api/v1/analytics/filters`
  Returns filter metadata and allowed options for the selected dataset.
- Future `POST /api/v1/analytics/details/source-files/query`
  Returns paginated detail rows for drilldown screens.
- Future `POST /api/v1/analytics/exports`
  Creates an asynchronous export job for large downloads.
- Future `GET /api/v1/analytics/exports/{job_id}`
  Returns export job status and output metadata.
- Future `GET /api/v1/analytics/exports/{job_id}/download`
  Streams the completed artifact.

Summary, chart, detail, export, and admin responsibilities stay separate. Detail rows and heavy exports must not piggyback on dashboard summary requests.

## Dashboard Definition Contract

```json
{
  "contract_version": "dashboard.v1",
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
      "request_method": "POST",
      "filter_keys": ["source", "partition_month"],
      "span": "small"
    }
  ],
  "charts": [
    {
      "chart_id": "files_by_source",
      "title": "Files by Source",
      "chart_type": "bar",
      "default_granularity": "month",
      "query_endpoint": "/api/v1/analytics/charts/files_by_source/query",
      "request_method": "POST",
      "filter_keys": ["source", "partition_month"],
      "limit": 20,
      "span": "medium"
    }
  ],
  "drilldown_actions": [
    {
      "key": "source_file_detail",
      "label": "Source File Detail",
      "type": "drilldown",
      "status": "planned",
      "scope": "chart",
      "target_key": "files_by_source",
      "endpoint": "/api/v1/analytics/details/source-files/query",
      "request_method": "POST",
      "filter_keys": ["source", "partition_month"],
      "status_reason": "Requires the paginated detail API and chart-to-filter drilldown wiring."
    }
  ],
  "export_actions": [
    {
      "key": "csv_zip_export",
      "label": "CSV Zip Export",
      "type": "export",
      "status": "planned",
      "scope": "dashboard",
      "endpoint": "/api/v1/analytics/exports",
      "request_method": "POST",
      "filter_keys": ["source", "partition_month"],
      "format": "csv.zip",
      "status_reason": "Requires asynchronous export job creation, polling, and download endpoints."
    }
  ],
  "warnings": [
    "Planned drilldown and export actions advertise their future endpoints, but the backing APIs are not implemented yet."
  ]
}
```

## Frontend Consumption Rules

1. The UI fetches `GET /api/v1/analytics/dashboards/{dashboard_id}?dataset=...` once to build the screen skeleton for a dashboard.
2. `contract_version` gates compatibility. A frontend that does not understand `dashboard.v1` must fail closed rather than guessing field semantics.
3. The filter bar is driven entirely by the ordered `filters` array. The UI must not invent extra query parameters or free-form SQL fragments.
4. Each card uses its own `metric_key` to select one metric from the shared `POST /api/v1/analytics/summary` response. The UI sends only the filter keys listed in `card.filter_keys`.
5. Each chart uses `chart_id`, `default_granularity`, `limit`, `query_endpoint`, and `request_method` exactly as returned. The UI sends only the filter keys listed in `chart.filter_keys`.
6. Chart click interactions must be translated into supported filter values before calling detail or export APIs. UI code should not invent chart-specific ad-hoc parameters.
7. Actions render according to `scope` and `target_key`.
   `scope=dashboard` attaches to the page-level toolbar.
   `scope=chart` attaches to the matching chart identified by `target_key`.
   `scope=card` attaches to the matching card identified by `target_key`.
8. `status=planned` actions may be shown as disabled affordances. `status_reason` is the user-facing explanation until the backing API exists.
9. `operations_overview` v1 exposes only server-provided filter metadata. A free-form date picker is out of scope until a date filter is returned as metadata.

## Common Request Rules

- Every request targets one logical `dataset`.
- Filter values are server-validated keys and values, not free-form SQL snippets.
- Multi-select filters are arrays of strings.
- Dashboard cards and charts stay summary-first. Pagination belongs only to detail responses.

## Summary Request

```json
{
  "dataset": "mes_ops",
  "filters": {
    "source": ["OPS_TABLE"],
    "partition_month": ["2026-03"]
  }
}
```

## Summary Response

```json
{
  "dataset": "mes_ops",
  "generated_at": "2026-03-31T09:00:00",
  "filters_applied": {
    "source": ["OPS_TABLE"],
    "partition_month": ["2026-03"]
  },
  "metrics": [
    {
      "key": "rows_loaded",
      "label": "Rows Loaded",
      "value": 1280,
      "precision": "integer",
      "unit": "rows"
    }
  ],
  "warnings": []
}
```

## Chart Request

```json
{
  "dataset": "mes_ops",
  "chart_id": "files_by_source",
  "granularity": "month",
  "limit": 20,
  "filters": {
    "source": ["OPS_TABLE"],
    "partition_month": ["2026-03"]
  }
}
```

## Chart Response

```json
{
  "dataset": "mes_ops",
  "chart_id": "files_by_source",
  "title": "Files by Source",
  "granularity": "month",
  "filters_applied": {
    "source": ["OPS_TABLE"],
    "partition_month": ["2026-03"]
  },
  "series": [
    {
      "key": "files",
      "label": "Files",
      "points": [
        {"bucket": "OPS_TABLE", "value": 12, "label": "OPS_TABLE"}
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
      "key": "source",
      "label": "Source Table",
      "type": "multi_select",
      "required": false,
      "supports_multiple": true,
      "options": [
        {"value": "OPS_TABLE", "label": "OPS_TABLE"}
      ]
    }
  ]
}
```

## Follow-on API Scope

### Detail API

- `POST /api/v1/analytics/details/source-files/query`
- Purpose: show page-safe row detail behind the `source_file_detail` drilldown action.
- Request fields:
  - `dataset`
  - `filters`
  - `page`
  - `page_size`
  - `sort`
- Response fields:
  - `dataset`
  - `detail_key`
  - `columns`
  - `rows`
  - `page`
  - `page_size`
  - `total`
  - `warnings`
- Rules:
  - Server-side pagination and sort only.
  - Drilldown from a chart click becomes additional supported filter values before the request is sent.
  - The detail API returns rows only and does not create downloads.

### Export API

- `POST /api/v1/analytics/exports`
- Purpose: create a long-running export job from the current dashboard filter state.
- Request fields:
  - `dataset`
  - `action_key`
  - `format`
  - `filters`
- Response fields:
  - `job_id`
  - `status`
  - `format`
  - `created_at`
- Rules:
  - `csv.zip` and `parquet` are asynchronous only.
  - Export job polling and download stay separate from dashboard refresh calls.
  - `xlsx` is reserved for future small human-readable extracts and is not part of `operations_overview` v1.

## Design Constraints

- Summary payloads must stay small enough for one dashboard refresh.
- Chart payloads must be directly renderable without client-side regrouping.
- Free-form sorting, projection, and SQL are out of scope.
- Detail APIs own pagination and sort.
- Exports use separate endpoints and job lifecycle handling.

## Code Mapping

- `src/airflow_lite/api/analytics_contracts.py`
  Owns the Pydantic request and response models for the current dashboard contract.
- `src/airflow_lite/analytics/catalog.py`
  Owns `operations_overview` widget metadata, action placement, and planned follow-on endpoint references.
- Future `T-027+`
  Should implement the detail and export routes against the DuckDB mart using these boundaries.
