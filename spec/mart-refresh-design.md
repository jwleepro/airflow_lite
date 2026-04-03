# Mart Refresh Design

## Goal

Define the narrow handoff from the existing Oracle -> Parquet batch pipeline into the future DuckDB mart build so later implementation can stay incremental and rollback-safe.

## Scope

- Trigger mart refresh planning only after a successful raw Parquet pipeline run.
- Keep mart build execution out of the current pipeline transaction path.
- Preserve the existing Oracle -> Parquet runtime and SQLite execution history behavior.

## Integration Point

The current runtime already exposes one safe hook:

- `PipelineRunner.run()` calls `on_run_success(context)` only after all stages succeed.

This design uses that hook to translate a successful raw run into a `MartRefreshPlan`.

## Planned Flow

```text
Oracle -> ETL stages -> Parquet verify success
       -> on_run_success(context)
       -> MartRefreshCoordinator.plan_refresh(context)
       -> staged DuckDB build executor (future T-014)
       -> validator
       -> snapshot promotion
```

## Ownership

- `src/airflow_lite/service/win_service.py`
  Owns runtime wiring and decides whether mart planning is enabled from settings.
- `src/airflow_lite/mart/orchestration.py`
  Owns translation from a successful pipeline context to a `MartRefreshRequest`.
- `src/airflow_lite/mart/refresh.py`
  Owns the refresh request and plan types.
- `src/airflow_lite/mart/builder.py`
  Owns staging and snapshot path planning.
- Future `T-014`
  Will own actual DuckDB build execution, validation SQL, and promotion.

## Request Derivation Rules

- `dataset_name`
  Derived from `settings.mart.pipeline_datasets[pipeline_name]` when configured, otherwise defaults to `pipeline_name`.
- `source_paths`
  Resolved from the raw Parquet partition written by the successful run:
  `{parquet_base_path}/{table}/year={YYYY}/month={MM}/*.parquet`
- `mode`
  `backfill` trigger becomes `MartRefreshMode.BACKFILL`.
  Incremental raw pipelines become `MartRefreshMode.INCREMENTAL`.
  Everything else defaults to `MartRefreshMode.FULL`.
- `build_id`
  Derived from `execution_date + run_id` so the staging path is deterministic and traceable to the raw run.

## Runtime Behavior

- Default state is disabled.
- When `mart.enabled` and `mart.refresh_on_success` are both true, the service plans a mart refresh after a successful raw run.
- Planning failures are logged but do not rewrite the already successful raw pipeline result.
- If a raw run produces no `.parquet` files for the resolved partition, mart planning is skipped and logged as a no-op.

## Config Surface

```yaml
mart:
  enabled: true
  root_path: "D:/data/mart"
  database_filename: "analytics.duckdb"
  refresh_on_success: true
  pipeline_datasets:
    production_log: "mes_ops"
    equipment_status: "mes_ops"
```

## Non-Goals In This Task

- Running DuckDB SQL
- Promoting `staging/` to `current/`
- Managing export jobs
- Exposing mart status through admin APIs

## Next Step

`T-014` should consume `MartRefreshPlan`, build a staging DuckDB database, validate required mart tables, and promote the snapshot only after validation passes.
