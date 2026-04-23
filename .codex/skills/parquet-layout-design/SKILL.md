---
name: parquet-layout-design
description: Design Parquet raw-zone layout, partitioning, file sizing, and replay strategy for analytics pipelines. Use when organizing extracted data for efficient DuckDB builds and backfills.
---

# Parquet Layout Design

Treat raw Parquet as the reproducible source layer for rebuilding marts.

## Workflow

1. Choose partition keys that match operational backfill and typical time filters.
2. Avoid tiny files and uncontrolled file counts.
3. Separate raw ingestion layout from downstream mart layout.
4. Define replay, replacement, and late-arriving data behavior.

## Focus Areas

- year/month/day partitioning
- plant or line partitioning only when it materially helps
- stable file naming
- staging then promote patterns
- retention and backup expectations

## Do Not Use

Do not use for query-layer tuning or export-format decisions.
