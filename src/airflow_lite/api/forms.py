"""Shared helpers for parsing form-encoded POST payloads."""

from __future__ import annotations


def first_value(
    values: dict[str, list[str]], key: str, default: str | None = None
) -> str | None:
    items = values.get(key)
    if not items:
        return default
    return items[0]
