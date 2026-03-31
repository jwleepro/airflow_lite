# PROGRESS.md

## Current State Summary

- Repository now has a canonical `AGENT.md` operating guide aligned with `.codex` conventions, separate from `CLAUDE.md`.
- Repository now has a local `.codex` layout for agent, command, and skill driven work.
- Repository now has reusable Codex references under `reference/codex/`.
- Shared execution-state documents now exist at the repository root.

## Recently Completed

- `2026-03-31` Updated `AGENT.md` so completed work now defaults to creating a draft PR through the GitHub publish workflow unless the user or environment blocks it.
- `2026-03-31` Added `.codex/config.toml` with repository-local agent roles and explicit skill registration.
- `2026-03-31` Added `.codex/commands/` command set for bootstrap, planning, progress tracking, handoff, team split, and reference reading.
- `2026-03-31` Added baseline `.codex/skills/` packages for bootstrap, progress discipline, indexing, task slicing, Oracle ETL, DuckDB mart design, query tuning, API contract design, export policy, Windows ops, failure bundling, and reference reading.
- `2026-03-31` Added `reference/codex/` with Markdown reference docs and `index.json`.
- `2026-03-31` Added `reference-reader` lookup script and tests.
- `2026-03-31` Added root `PLAN.md` and `PROGRESS.md` and aligned them to the repository's multi-agent workflow.
- `2026-03-31` Added `src/airflow_lite/mart/` skeleton with build, refresh, snapshot, and validation interfaces plus focused tests.
- `2026-03-31` Added root `AGENT.md` and aligned planning docs to the current task state without changing the Claude Code specific workflow file.
- `2026-03-31` Completed `T-011` with `mart` refresh design docs, optional mart settings, and a success-hook mart refresh planner integration in the Windows service runtime.
- `2026-03-31` Completed `T-012` with summary/chart/filter API contract docs plus Pydantic contract models for later FastAPI implementation.

## In Progress

- `2026-03-31` Publishing the default draft PR workflow update on branch `codex/default-draft-pr-workflow`.
  Scope: `AGENT.md`, `PROGRESS.md`

## Pending Next Work

- `T-014` Execute staged DuckDB mart builds from the refresh plan.
- `T-015` Add read-only analytics query services and summary/chart endpoints.

## Blockers and Risks

- `T-014` still needs real DuckDB build execution, validation SQL, and snapshot promotion; the current mart hook only plans refreshes.
- `T-015` still needs runtime routes and query services; only the contract models and design documents exist today.
- The local environment blocks `pytest` temp-directory fixtures under the default temp root, so verification had to avoid `tmp_path`-dependent cases.

## Validation Notes

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
- Recommended next owner: `duckdb-mart-agent`
- Recommended write scope:
  - `src/airflow_lite/mart/`
  - `src/airflow_lite/service/` only if refresh execution wiring needs a small extension
  - `tests/` for staged build and validator coverage
