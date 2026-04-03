# PROGRESS.md

## Current State Summary

- Repository now has a canonical `AGENT.md` operating guide aligned with `.codex` conventions.
- Repository now has a local `.codex` layout for agent and skill driven work.
- Repository now has reusable Codex references under `reference/codex/`.
- Shared execution-state documents now exist at the repository root.

## Recently Completed

- `2026-04-02` Completed `T-017` for draft PR `#1` by documenting the SQLite transaction rationale in code, adding a `trigger_type` propagation test, and confirming the existing mart wiring and review-fix changes that answer the three actionable review comments.
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

- `T-014` Execute staged DuckDB mart builds from the refresh plan.
- `T-015` Add read-only analytics query services and summary/chart endpoints.

## Blockers and Risks

- `T-014` still needs real DuckDB build execution, validation SQL, and snapshot promotion; the current mart hook only plans refreshes.
- `T-015` still needs runtime routes and query services; only the contract models and design documents exist today.
- The local environment blocks `pytest` temp-directory fixtures under the default temp root, so verification had to avoid `tmp_path`-dependent cases.

## Validation Notes

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

- The repository is ready for the next agent to start `T-014`.
- Recommended next owner: Codex built-in `duckdb-mart-agent`
- Recommended write scope:
  - `src/airflow_lite/mart/`
  - `src/airflow_lite/service/` only if refresh execution wiring needs a small extension
  - `tests/` for staged build and validator coverage
