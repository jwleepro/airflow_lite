---
name: repo-indexing
description: Rapidly map repository structure, entry points, config files, tests, and likely write scopes before making changes. Use when first orienting in this project or when scoping the impact of a change.
---

# Repo Indexing

Build a small, task-relevant map instead of reading the whole repository.

## Workflow

1. Identify package roots, service entry points, config files, and tests.
2. Trace the change path from requested behavior to owning modules.
3. List likely touched files and adjacent regression areas.
4. For `.codex/` work, map the relevant `reference/codex/` documents alongside the code paths.
5. Note existing tests and missing verification coverage.

## Output

Return the relevant directories, likely edit set, likely test set, and any open questions.

## Do Not Use

Do not use when the task is already fully localized to one or two known files.
