---
name: oracle-batch-etl
description: Design or implement Oracle 11g batch extraction with python-oracledb thick mode, incremental windows, chunking, and Parquet raw ingestion. Use when working on source extraction reliability or performance in this repository.
---

# Oracle Batch ETL

Optimize for safe, repeatable extraction from Oracle 11g with minimal source load.

## Workflow

1. Prefer thick-mode compatible access patterns.
2. Use incremental extraction by time column or monotonic key.
3. Chunk extraction to avoid memory spikes.
4. Persist raw results in reproducible Parquet layout.
5. Record checkpoints and failure boundaries clearly.

## Focus Areas

- arraysize and prefetch tuning
- date or key range extraction
- retry boundaries
- raw-zone file naming
- restartable backfill behavior

## Do Not Use

Do not use for DuckDB serving, API design, or front-end work.
