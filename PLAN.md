# PLAN.md

## Goal

Build this repository into a Windows Server 2019 compatible MES analytics system based on:

- Oracle 11g batch extraction
- Parquet raw storage
- DuckDB analytics mart
- FastAPI query and export APIs
- dashboard and large-result download support

## Current Milestone

`M2. DuckDB mart skeleton`

This milestone covers:

- staged DuckDB build execution from raw Parquet inputs
- mart validation rules and snapshot promotion
- runtime-safe refresh orchestration

## Milestone Status

- `M0. Existing Oracle -> Parquet pipeline baseline`: available
- `M1. Collaboration and analytics foundation`: completed
- `M2. DuckDB mart skeleton`: in progress
- `M3. Query and export API expansion`: pending
- `M4. Dashboard and visualization layer`: pending

## Task List

### Completed

- `T-001` Create and maintain `AGENT.md` as the repository operating guide.
  Done condition: repository constraints, target architecture, directory structure, and workflow rules documented.
- `T-002` Create local `.codex` configuration for agents and skills.
  Done condition: `.codex/config.toml`, role configs, and baseline skills added.
- `T-003` Create reusable Codex research references.
  Done condition: `reference/codex/` documents, index, lookup script, and integration points added.
- `T-004` Establish repository execution state documents.
  Done condition: `PLAN.md` and `PROGRESS.md` exist, reflect current repository state, and can be used by future agents immediately.
- `T-010` Create DuckDB mart module skeleton under `src/airflow_lite/mart/`.
  Done condition: package and initial tests exist without breaking current pipeline.
- `T-013` Align repository operating documents and Codex workflow usage guidance.
  Done condition: `AGENT.md`, `PLAN.md`, and `PROGRESS.md` are consistent with the local Codex workflow, and the repository documents how to choose agents and skills without relying on `CLAUDE.md`.
- `T-016` Add local Codex support for GitHub PR ready-state automation.
  Done condition: repository-local agent and skill exist for defining and checking automatic draft-to-ready promotion rules, and the operating guide references them.
- `T-017` Resolve actionable review blockers for draft PR `#1`.
  Done condition: the three actionable review comments on PR `#1` are either implemented in code/tests or explicitly answered by repository evidence, and validation is recorded in `PROGRESS.md`.
- `T-018` Implement GitHub Actions PR checks and automatic draft-to-ready promotion.
  Done condition: the repository has a runnable PR workflow with stable `smoke` and `unit-core` checks plus an automatic draft-to-ready gate tied to explicit labels and documented operating rules.
- `T-011` Add Parquet -> DuckDB refresh step design.
  Done condition: refresh orchestration flow is documented and the existing pipeline has a narrow mart planning hook.
- `T-012` Design summary and chart API contracts.
  Done condition: summary/chart/filter contracts exist in docs and code-backed schema models.

### Current

### Next

- `T-014` Execute staged DuckDB mart builds from the refresh plan.
  Owner: `duckdb-mart-agent`
  Status: pending
  Scope: DuckDB staging build execution, validation SQL, and snapshot promotion
  Done condition: a validated staging database can be promoted into `data/mart/current/`.
- `T-015` Add read-only analytics query services and summary/chart endpoints.
  Owner: `query-api-agent`
  Status: pending
  Scope: DuckDB-backed query service, FastAPI analytics routes, and filter metadata endpoints
  Done condition: the documented summary/chart contracts are served by read-only endpoints without exposing ad-hoc SQL.

## Dependencies

- `T-004` must complete before the planning workflow is fully operational.
- `T-010` should start before `T-011` and `T-012`.
- `T-012` depends on at least a provisional mart shape from `T-010`.
- `T-014` depends on `T-011`.
- `T-015` depends on `T-012` and a runnable mart produced by `T-014`.

## Priority Order

1. `T-014` Execute staged mart builds.
2. `T-015` Serve analytics queries.

## Done Definition

A planned task is considered done when:

- the target files exist or are updated correctly
- the scope is narrow enough for the next agent to pick up safely
- validation status is recorded in `PROGRESS.md`
- any follow-up work is explicitly listed

## Next Recommended Task

Start `T-014` by consuming the new `MartRefreshPlan`, building a staging DuckDB database, and validating it before promotion.
