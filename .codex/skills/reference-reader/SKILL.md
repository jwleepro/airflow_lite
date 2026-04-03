---
name: reference-reader
description: Read and filter the repository's indexed Codex reference documents from reference/codex. Use when a task touches .codex, local Codex agents, commands, skills, or Codex workflow conventions and you need the smallest relevant set of reference documents.
---

# Reference Reader

Use the indexed reference set instead of manually scanning the repository.

## Workflow

1. Read `reference/codex/index.json`.
2. Use the bundled script to list or filter available documents.
3. Read only the selected Markdown files.
4. If the task changes a Codex convention, update both the relevant document and the index.

## Script

Use:

```powershell
python .codex/skills/reference-reader/scripts/read_reference.py --list
python .codex/skills/reference-reader/scripts/read_reference.py --topic skill
python .codex/skills/reference-reader/scripts/read_reference.py --doc skill-format
python .codex/skills/reference-reader/scripts/read_reference.py --doc skill-format --show-content
```

## Rules

- Use this skill before editing `.codex/` files.
- Prefer indexed lookup over broad filesystem search.
- Keep `reference/codex/index.json` aligned with the actual documents.

## Do Not Use

Do not use for application-domain requirements, Oracle behavior, or DuckDB design unless those topics are explicitly documented under `reference/codex/`.
