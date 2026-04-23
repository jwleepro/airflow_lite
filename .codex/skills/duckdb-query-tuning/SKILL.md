---
name: duckdb-query-tuning
description: Tune DuckDB analytical queries for filters, joins, aggregations, and sort-heavy workloads. Use when summary, chart, detail, or export queries are too slow on large datasets.
---

# DuckDB Query Tuning

Optimize for the repository's real access patterns instead of generic SQL style.

## Workflow

1. Identify the target query shape and its filter or selectivity pattern.
2. Check whether the query should hit raw fact or a prepared summary.
3. Align table layout and sort order with common predicates.
4. Reduce unnecessary scans, wide projections, and repeated expensive joins.

## Focus Areas

- summary-first dashboards
- selective detail queries
- large joins against dimensions
- stable pagination patterns
- export queries that should bypass UI-oriented limits

## Do Not Use

Do not use when the main issue is extraction latency or Windows service setup.
