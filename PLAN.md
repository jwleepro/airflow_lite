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
- `T-017` Resolve actionable review blockers for draft PR `#1`.
  Done condition: the three actionable review comments on PR `#1` are either implemented in code/tests or explicitly answered by repository evidence, and validation is recorded in `PROGRESS.md`.
- `T-019` Reduce repository-local agent registry to Codex-only exceptions.
  Done condition: `.codex/config.toml` keeps only repository-specific agent roles, and the operating documents distinguish those from Codex built-in agents.
- `T-011` Add Parquet -> DuckDB refresh step design.
  Done condition: refresh orchestration flow is documented and the existing pipeline has a narrow mart planning hook.
- `T-012` Design summary and chart API contracts.
  Done condition: summary/chart/filter contracts exist in docs and code-backed schema models.
- `T-020` Remove repository-local draft-to-ready promotion automation.
  Done condition: current repository docs, skill registration, and CI workflow no longer advertise or execute automatic draft PR promotion.
- `T-021` Define and add structured GitHub issue intake forms.
  Done condition: repository has structured issue form YAML files plus chooser configuration that preserve the current label policy and leave status/automation labels under maintainer or workflow control.
- `T-022` Add issue-triage automation for structured GitHub issue forms.
  Done condition: issues opened from the new forms can be normalized to the documented label policy without exposing status or automation labels to contributors.
- `T-023` Refine the GitHub AI automation playbook around the implemented issue-intake baseline.
  Done condition: the playbook clearly separates implemented issue intake files from future workflow candidates and no longer conflates issue forms with GitHub Actions workflows.
- `T-024` Declare and sync the GitHub label catalog from the repository.
  Done condition: playbook labels are declared in-repo and a repository-managed sync path keeps GitHub label state aligned.

### Current

### Next

- `T-014` Execute staged DuckDB mart builds from the refresh plan.
  Owner: Codex built-in `duckdb-mart-agent`
  Status: pending
  Scope: DuckDB staging build execution, validation SQL, and snapshot promotion
  Done condition: a validated staging database can be promoted into `data/mart/current/`.
- `T-015` Add read-only analytics query services and summary/chart endpoints.
  Owner: Codex built-in `query-api-agent`
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
