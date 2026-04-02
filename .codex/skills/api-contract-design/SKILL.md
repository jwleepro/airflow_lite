---
name: api-contract-design
description: Design summary, chart, detail, admin, and export API contracts for the analytics system. Use when defining request or response shapes, filtering rules, pagination, or endpoint boundaries.
---

# API Contract Design

Design APIs around front-end needs and operational safety, not around raw SQL freedom.

## Workflow

1. Separate summary, chart, detail, export, and admin responsibilities.
2. Define filters, sort, and pagination on the server side.
3. Keep response payloads narrow and stable.
4. Ensure exports have their own job lifecycle instead of piggybacking on UI detail endpoints.

## Focus Areas

- filter metadata endpoints
- chart-friendly series payloads
- page-safe detail results
- async export creation and retrieval
- admin visibility for refresh and validation state

## Do Not Use

Do not use for physical storage layout or OS-level deployment tasks.
