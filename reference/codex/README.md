# Codex Reference

This directory stores reusable research notes about the local Codex setup used in this repository.

## Purpose

Keep Codex-specific rules, structure notes, and format decisions in one place so future agents do not need to re-discover them from scratch.

## Format

- `index.json`: machine-readable index for lookup scripts and references
- `*.md`: human-readable reference documents

## Reading Order

1. Read `index.json`.
2. Select only the documents relevant to the current task.
3. Read the chosen Markdown files.
4. Update the relevant document when the repo's `.codex` structure changes.

## Current Topics

- agent role config format
- skill package format
- repository-specific `.codex` layout
- workflow for using these references
- PR ready-for-review automation policy, including the implemented `PR Checks` workflow, stable check names, and current GitHub event constraints
