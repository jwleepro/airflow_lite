---
name: project-bootstrap
description: Bootstrap work in this repository by reading AGENTS.md first, then summarizing active scope, blockers, and the safest next task from the current request and repository state. Use when starting a new Codex thread or when handing the repository to another agent.
---

# Project Bootstrap

Read `AGENTS.md` before opening unrelated files. Use the current request and repository state to infer the active task.

## Workflow

1. Extract the current milestone and hard constraints from `AGENTS.md`.
2. Infer the active task, nearby blockers, and likely write scope from the current user request, repository status, and the nearest task-specific docs.
3. If the task touches `.codex/` or Codex workflow files, read `reference/codex/index.json` and only the relevant reference documents.
4. Produce a short working summary with the active task, fallback task, blockers, and expected write scope.

## Output

Return a compact start-state summary another engineer could act on immediately.

## Do Not Use

Do not use for deep implementation or review. Switch to a narrower skill once the current task is identified.
