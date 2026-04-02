---
name: failure-bundling
description: Turn a failing pipeline, test, export, or refresh into a compact diagnostic bundle with reproduction steps, logs, changed files, and likely ownership. Use when handing failures to another agent or when preparing a focused fix.
---

# Failure Bundling

Reduce time-to-fix by collecting only the evidence needed to reproduce and assign the issue.

## Workflow

1. Capture the failing command, input, and timestamp.
2. Capture the minimal relevant logs and error text.
3. Note recent changed files and affected subsystem.
4. State the likely owner role and the next diagnostic step.

## Output

Produce a compact bundle with the failing step, symptoms, reproduction, likely scope, and recommended owner.

## Do Not Use

Do not use for routine progress updates when nothing failed.
