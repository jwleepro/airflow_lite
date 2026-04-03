---
name: project-bootstrap
description: Bootstrap work in this repository by reading AGENT.md, PLAN.md, and PROGRESS.md first, then summarizing active scope, blockers, and the safest next task. Use when starting a new Codex thread or when handing the repository to another agent.
---

# Project Bootstrap

Read `AGENT.md`, then `PLAN.md`, then `PROGRESS.md` before opening unrelated files.

## Workflow

1. Extract the current milestone and hard constraints from `AGENT.md`.
2. Extract the active and upcoming tasks from `PLAN.md`.
3. Extract recent completions, active work, blockers, and handoff notes from `PROGRESS.md`.
4. If the task touches `.codex/` or Codex workflow files, read `reference/codex/index.json` and only the relevant reference documents.
5. Produce a short working summary with the active task, fallback task, blockers, and expected write scope.

## Output

Return a compact start-state summary another engineer could act on immediately.

## Do Not Use

Do not use for deep implementation or review. Switch to a narrower skill once the current task is identified.
