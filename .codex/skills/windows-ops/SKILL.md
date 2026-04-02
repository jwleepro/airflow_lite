---
name: windows-ops
description: Plan and implement Windows Server 2019 operational workflows for this repository, including service execution, scheduler behavior, environment verification, logging, and backup or restore steps. Use when working on deployment or runbook tasks.
---

# Windows Ops

Keep operations compatible with a single Windows Server deployment and limited-network environments.

## Workflow

1. Prefer native Windows-compatible tooling and paths.
2. Keep service startup, scheduled jobs, logs, and temp files explicit.
3. Verify environment prerequisites before enabling automation.
4. Document backup, restore, and rollback steps with exact paths.

## Focus Areas

- service wrapper behavior
- scheduled batch execution
- path and permission assumptions
- log and temp directory usage
- operator runbooks

## Do Not Use

Do not use for query semantics or front-end UX work.
