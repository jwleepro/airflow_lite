# Reference Workflow

## Purpose

This document defines how to use `reference/codex/` during Codex meta work.

## Workflow

1. Read `AGENT.md`.
2. Read `PLAN.md`.
3. Read `PROGRESS.md`.
4. If the task touches `.codex/` or Codex workflow docs:
   - read `reference/codex/index.json`
   - select only the relevant documents
   - read the selected Markdown files

## Lookup Options

- Manual: open `reference/codex/index.json` and then the referenced file paths
- Scripted: run the reference reader script from the `reference-reader` skill
- Guided: use the `reference-reader` skill workflow

## Update Rule

If a Codex-related decision or structure changes:

1. update the relevant `.md` file
2. keep the summary and keywords in `index.json` aligned
3. mention the change in `PROGRESS.md` when it matters for follow-up work

## Scope Boundary

Use `reference/codex/` for repository-level Codex conventions.

Do not put application architecture, API specs, or domain requirements here. Those belong in the normal `reference/` and `docs/` areas.
