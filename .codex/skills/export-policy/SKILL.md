---
name: export-policy
description: Define and implement export rules for xlsx, csv.zip, and parquet outputs, including size thresholds, file naming, async jobs, and user-facing limits. Use when adding download features to this repository.
---

# Export Policy

Treat downloads as a separate workload with explicit size and format policy.

## Workflow

1. Match format to intent: xlsx for human-readable small reports, csv.zip for large tabular extracts, and parquet for machine reuse.
2. Keep heavy exports asynchronous.
3. Define row, file, and timeout thresholds.
4. Record export jobs and output locations predictably.

## Focus Areas

- Excel row-limit awareness
- file naming conventions
- chunked or multi-file delivery
- retention and cleanup
- separation from screen queries

## Do Not Use

Do not use for dashboard chart design or Oracle extraction tuning.
