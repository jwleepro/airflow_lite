# Repository Codex Layout

## Purpose

This document explains how this repository organizes its local Codex files.

## Directory Layout

```text
.codex/
├── config.toml
├── agents/
└── skills/

reference/
└── codex/
    ├── README.md
    ├── index.json
    └── *.md
```

## Key Decisions

### 1. Agents

- Agent role registration lives in `.codex/config.toml`.
- Each role has its own TOML file under `.codex/agents/`.
- The repository keeps only repository-specific custom roles locally. General planning, indexing, review, testing, docs, and domain roles are expected to come from the Codex built-in agent catalog.

### 2. Skills

- Skills live under `.codex/skills/`.
- Because this is not the default global skill path, each local skill is registered explicitly in `.codex/config.toml` using `[[skills.config]]`.
- Reusable repository policy workflows, including PR readiness automation, should be packaged as local skills when they combine design rules with repeatable implementation steps.

### 3. References

- Shared Codex research lives under `reference/codex/`.
- Machine-readable lookup uses `reference/codex/index.json`.
- Human-readable details live in topic-specific Markdown files.

## Maintenance Rule

Whenever `.codex/` structure changes materially:

1. update the relevant file under `reference/codex/`
2. update `reference/codex/index.json` if a document is added or renamed
3. update any skill or workflow doc that routes users to those references

Official reference:

- `https://developers.openai.com/codex/config-reference/#configtoml`
- `https://developers.openai.com/codex/skills/`
