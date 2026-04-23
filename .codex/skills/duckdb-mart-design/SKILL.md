---
name: duckdb-mart-design
description: Design or implement DuckDB marts for read-heavy analytics, including facts, dimensions, summaries, refresh flow, snapshot promotion, and validation. Use when building the repository's analysis-serving layer.
---

# DuckDB Mart Design

Use DuckDB as a batch-built analytics engine, not as a multi-writer OLTP database.

## Workflow

1. Define fact, dimension, and summary tables around the target UI queries.
2. Build marts from Parquet raw inputs in staging.
3. Validate row counts, key integrity, and summary consistency.
4. Promote validated snapshots into the current serving location.

## Focus Areas

- snapshot build and promotion
- summary tables for dashboards
- validation SQL
- reproducible rebuilds
- rollback-safe current and snapshot directories

## Do Not Use

Do not use for source Oracle tuning or front-end presentation work.
