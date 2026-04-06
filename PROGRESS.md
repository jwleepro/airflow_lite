# PROGRESS.md

## Current State Summary

- Repository now has a canonical `AGENT.md` operating guide aligned with `.codex` conventions.
- Repository now has a local `.codex` layout for agent and skill driven work.
- Repository now has reusable Codex references under `reference/codex/`.
- Shared execution-state documents now exist at the repository root.

## Recently Completed

- `2026-04-06` Completed `T-015` by adding a DuckDB-backed analytics query service, FastAPI summary/chart/filter routes, and route-level tests around the promoted mart database.
- `2026-04-06` Completed `T-014` by adding staged DuckDB mart execution, source-table rebuilds, mart validation, snapshot/current promotion, and service success-hook execution wiring.
- `2026-04-02` Removed unsupported repository-local `.codex/commands/` files and cleaned command references from `AGENT.md`, planning logs, and `reference/codex/`.
- `2026-04-02` Addressed actionable code-review findings by switching backfill requests to a safe non-force default, strengthening incremental parquet verification against actual partition row growth, and making SQLite schema scripts execute statement-by-statement inside an explicit transaction.
- `2026-03-31` Opened draft PR `#1` for the default draft PR workflow update on branch `codex/default-draft-pr-workflow`.
- `2026-03-31` Updated `AGENT.md` so completed work now defaults to creating a draft PR through the GitHub publish workflow unless the user or environment blocks it.
- `2026-03-31` Added `.codex/config.toml` with repository-local agent roles and explicit skill registration.
- `2026-03-31` Added baseline `.codex/skills/` packages for bootstrap, progress discipline, indexing, task slicing, Oracle ETL, DuckDB mart design, query tuning, API contract design, export policy, Windows ops, failure bundling, and reference reading.
- `2026-03-31` Added `reference/codex/` with Markdown reference docs and `index.json`.
- `2026-03-31` Added `reference-reader` lookup script and tests.
- `2026-03-31` Added root `PLAN.md` and `PROGRESS.md` and aligned them to the repository's multi-agent workflow.
- `2026-03-31` Added `src/airflow_lite/mart/` skeleton with build, refresh, snapshot, and validation interfaces plus focused tests.
- `2026-03-31` Added root `AGENT.md` and aligned planning docs to the current task state without changing the Claude Code specific workflow file.
- `2026-03-31` Completed `T-011` with `mart` refresh design docs, optional mart settings, and a success-hook mart refresh planner integration in the Windows service runtime.
- `2026-03-31` Completed `T-012` with summary/chart/filter API contract docs plus Pydantic contract models for later FastAPI implementation.

## In Progress

- No active task is currently marked in progress.

## Pending Next Work

- `M4` still needs dashboard and visualization layer planning plus implementation tasks.

## Blockers and Risks

- The analytics layer currently serves mart metadata summaries and charts; dataset-specific KPI logic, detail queries, and export workflows are still follow-up work.
- The local environment blocks `pytest` temp-directory fixtures under the default temp root, so verification had to avoid `tmp_path`-dependent cases.

## Validation Notes

- `2026-04-06` Manual inline Python validation under `C:\Users\170731\.codex\memories` confirmed staged mart refresh builds aggregate source parquet files into DuckDB, validate successfully, promote to both `current/` and `snapshots/`, and preserve unrelated existing source tables during rebuilds.
- `2026-04-06` Manual inline Python validation under `C:\Users\170731\.codex\memories` confirmed `DuckDBAnalyticsQueryService` returns summary metrics, month-bucket chart data, and filter metadata from a promoted mart database.
- `2026-04-06` Manual inline Python validation with `fastapi.testclient.TestClient` confirmed `/api/v1/analytics/summary`, `/api/v1/analytics/charts/{chart_id}/query`, and `/api/v1/analytics/filters` respond successfully against a sample DuckDB mart.
- `2026-04-06` `python -m compileall src/airflow_lite/mart src/airflow_lite/query src/airflow_lite/analytics src/airflow_lite/api tests/test_mart.py tests/test_query_service.py tests/test_api.py tests/test_service.py` succeeded.
- `2026-04-06` `pytest tests/test_mart.py tests/test_query_service.py tests/test_api.py tests/test_service.py -q --basetemp ... -p no:cacheprovider` reached execution but this sandbox still failed during pytest temp-directory cleanup with `PermissionError` while iterating the chosen base temp directory.
- `2026-04-04` `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`, `python -m pytest tests/test_issue_triage.py tests/test_label_sync.py -q --basetemp .tmp_pytest -p no:cacheprovider` succeeded with `8 passed`.
- `2026-04-04` `python .github\scripts\sync_labels.py --repo jwleepro/airflow_lite --labels-path .github\labels.json --dry-run` reported `create=[]`, `update=[]`, `unchanged_count=31`.
- `2026-04-04` `python .github\scripts\sync_labels.py --repo jwleepro/airflow_lite --labels-path .github\labels.json` completed as a no-op with `create=[]`, `update=[]`, `unchanged_count=31`.
- `2026-04-04` `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`, `python -B -m pytest tests/test_issue_triage.py -q -p no:cacheprovider` succeeded with `5 passed` after adding explicit `needs-human` signal handling to the issue forms and triage script.
- `2026-04-03` `python .codex\skills\reference-reader\scripts\read_reference.py --list` succeeded after the cleanup and now reports `document count: 4`.
- `2026-04-03` Manual validation confirmed every path still listed in `reference/codex/index.json` now exists under `reference/codex/`.
- `2026-04-02` `pytest tests/test_api.py tests/test_backfill.py tests/test_extract.py tests/test_service.py tests/test_settings.py tests/test_storage.py tests/test_mart.py tests/test_reference_reader.py -q -p no:cacheprovider` ran to collection and execution but failed in this environment because pytest could not access `C:\Users\170731\AppData\Local\Temp\pytest-of-170731` for `tmp_path` setup.
- `2026-04-02` `python -m compileall src/airflow_lite/storage/database.py tests/test_engine.py` succeeded after adding the SQLite transaction rationale comment and the `trigger_type` propagation regression test.
- `2026-04-02` Inline Python validation under a workspace-local temp directory confirmed `PipelineRunner.run(trigger_type="backfill")` propagates `trigger_type` into both stage execution and the `on_run_success` callback, and `_execute_script_atomically()` still rolls back earlier statements when a later statement fails.
- `2026-04-02` `pytest tests/test_engine.py tests/test_storage.py tests/test_service.py tests/test_settings.py tests/test_extract.py tests/test_backfill.py -q -p no:cacheprovider` could not complete in this environment because pytest temp-directory setup/cleanup still hit Windows permission errors even with explicit `--basetemp`.
- `2026-04-02` Manual validation confirmed `.codex/commands/` no longer exists and `reference/codex/command-format.md` was removed from both the filesystem and `reference/codex/index.json`.
- `2026-04-02` Manual validation confirmed `AGENT.md`, `PLAN.md`, `PROGRESS.md`, and `reference/codex/*.md` no longer instruct users to use repository-local slash commands.
- `2026-04-02` Inline Python verification confirmed `BackfillRequest.force` now defaults to `False`, `BackfillManager.run_backfill()` forwards `force_rerun=False` by default, and `IncrementalMigrationStrategy.verify()` now rejects partition row counts that do not match expected growth.
- `2026-04-02` Inline Python verification confirmed `_execute_script_atomically()` rolls back partial SQL sequences after an expected `OperationalError`, and `Database.initialize()` still creates `pipeline_runs` and `step_runs` with the new executor.
- `2026-04-02` `python -m compileall src/airflow_lite/api/schemas.py src/airflow_lite/engine/backfill.py src/airflow_lite/engine/strategy.py tests/test_api.py tests/test_backfill.py tests/test_extract.py tests/test_storage.py` succeeded.
- `2026-04-02` `pytest tests/test_api.py tests/test_backfill.py tests/test_extract.py tests/test_storage.py -q -p no:cacheprovider` could not complete in this environment because pytest temp-directory setup/cleanup hit Windows permission errors under both the default temp root and a repository-local `--basetemp`.
- `2026-03-31` Pushed branch `codex/default-draft-pr-workflow` and created draft PR `#1`: `https://github.com/jwleepro/airflow_lite/pull/1`
- `2026-03-31` Re-read `AGENT.md`, `PLAN.md`, and `PROGRESS.md` before documenting the new default PR creation workflow.
- `2026-03-31` `python .codex\skills\reference-reader\scripts\read_reference.py --list` succeeded.
- `2026-03-31` `pytest tests\test_reference_reader.py -q` succeeded with `2 passed`.
- `2026-03-31` `pytest tests\test_mart.py -q` succeeded with `5 passed`.
- `2026-03-31` Re-read `AGENT.md`, `PLAN.md`, and `PROGRESS.md` after the documentation alignment update.
- `2026-03-31` `pytest tests\test_mart.py -q -p no:cacheprovider` succeeded with `7 passed`.
- `2026-03-31` `pytest tests\test_settings.py -q -k mart_config -p no:cacheprovider` succeeded with `1 passed`.
- `2026-03-31` `pytest tests\test_api.py -q -k "summary_contract or chart_contract" -p no:cacheprovider` succeeded with `2 passed`.
- `2026-03-31` Inline Python validation confirmed `AirflowLiteService._create_runner_factory()` calls the mart refresh planner hook when `mart.enabled=true`.
- `2026-03-31` `python -m compileall src/airflow_lite` succeeded.

## Handoff

- The repository is ready for `M4` dashboard planning on top of the promoted DuckDB mart and analytics endpoints.
- Recommended next owner: Codex built-in `planner-agent` or frontend-oriented implementation agent
- Recommended write scope:
  - `src/airflow_lite/api/`
  - `src/airflow_lite/query/`
  - `src/airflow_lite/analytics/`
  - dashboard/UI files once they are introduced
