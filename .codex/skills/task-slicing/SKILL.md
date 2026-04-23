---
name: task-slicing
description: Break a large request into self-contained tasks with owners, dependencies, write scopes, and done conditions. Use when planning multi-step or multi-agent work in this repository.
---

# Task Slicing

Split work so each task can be finished, validated, and handed off cleanly.

## Workflow

1. Identify the end state and the minimum milestones needed to reach it.
2. Break the work into tasks with purpose, inputs, outputs, write scope, owner role, and done condition.
3. Order tasks by dependency and user value.
4. Put stable sequencing into `PLAN.md`.

## Rules

- Prefer 1-3 hour tasks over vague epics.
- Prefer disjoint write scopes when parallelizing.
- Name blockers explicitly instead of burying them in notes.

## Do Not Use

Do not use for small fixes that can be completed in one pass without coordination.
