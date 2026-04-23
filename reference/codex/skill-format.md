# Skill Package Format

## Purpose

This document records the skill format used in this repository.

## Required Structure

A skill is a directory containing a required `SKILL.md` file and optional helper files.

```text
skill-name/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
├── references/
└── assets/
```

## SKILL.md Rules

`SKILL.md` must contain YAML frontmatter with:

- `name`
- `description`

The frontmatter should not include extra fields unless there is a clear need and support for them.

The body should:

- say what the skill is for
- describe the workflow
- say when not to use it
- point to scripts or references when present

## agents/openai.yaml

`agents/openai.yaml` is optional but recommended for UI metadata.

Common fields used here:

- `interface.display_name`
- `interface.short_description`
- `interface.default_prompt`

## Repository Convention

- Keep `SKILL.md` concise.
- Put deterministic helpers in `scripts/`.
- Put reusable research docs in `references/`.
- Use `reference/codex/` for shared repository-level Codex research, not per-skill details.

## When To Update

Update this document when:

- skill folder layout changes
- the repository starts using bundled references or scripts differently
- skill metadata conventions change

## Source Notes

This format was aligned to Codex skills documentation and local installed skill examples.

Official reference:

- `https://developers.openai.com/codex/skills/`
- `https://developers.openai.com/cookbook/examples/skills_in_api/`
