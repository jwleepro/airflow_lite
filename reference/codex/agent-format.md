# Agent Config Format

## Purpose

This document records the role-based agent format used by this repository's local Codex configuration.

## Format Summary

The repository-level config lives in `.codex/config.toml`.

Relevant keys:

- `[agents]`
- `agents.max_threads`
- `agents.max_depth`
- `agents.job_max_runtime_seconds`
- `[agents.<name>]`
- `agents.<name>.description`
- `agents.<name>.config_file`
- `agents.<name>.nickname_candidates`

Each role points to a per-role TOML file, for example:

```toml
[agents.github-automation-agent]
description = "GitHub Actions, PR gate, and review-state automation role"
config_file = "./agents/github-automation-agent.toml"
nickname_candidates = ["GitHub Auto", "PR Gate"]
```

Per-role files currently use standard Codex config keys such as:

- `personality`
- `model_reasoning_effort`
- `model_verbosity`
- `sandbox_mode`
- `project_doc_fallback_filenames`

## Repository Convention

- Keep repository-local roles only when they express repository-specific ownership that should not be left to the generic Codex built-in catalog.
- Keep role descriptions explicit about ownership.
- Use a dedicated GitHub workflow automation role when PR gates, CI checks, or review-state transitions need explicit ownership distinct from Windows ops or Codex meta maintenance.
- Prefer `read-only` for exploration and review roles.
- Prefer `workspace-write` for implementation roles.
- Keep nickname candidates short and human-readable.
- As of `2026-04-23`, this repository keeps `codex-meta-agent`, `github-automation-agent`, and `github-issue-cycle-agent` as repository-local custom roles. Planning, indexing, review, testing, and most domain implementation use Codex built-in agents instead of duplicate local registrations.

## When To Update

Update this document when:

- a new agent role is added
- supported role-level config keys change
- ownership boundaries between roles change

## Source Notes

This format was aligned to Codex documentation for `config.toml` and local role configuration, then applied to the repository's `.codex/config.toml`.

Official reference:

- `https://developers.openai.com/codex/config-reference/#configtoml`
