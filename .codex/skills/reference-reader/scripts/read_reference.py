from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
INDEX_PATH = REPO_ROOT / "reference" / "codex" / "index.json"


def load_index() -> dict:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"reference index not found: {INDEX_PATH}") from exc


def matches_topic(entry: dict, topic: str) -> bool:
    needle = topic.lower()
    haystacks = [
        entry.get("id", ""),
        entry.get("title", ""),
        entry.get("summary", ""),
        " ".join(entry.get("keywords", [])),
        " ".join(entry.get("use_when", [])),
    ]
    return any(needle in value.lower() for value in haystacks)


def print_entry(entry: dict) -> None:
    print(f"id: {entry['id']}")
    print(f"title: {entry['title']}")
    print(f"path: {entry['path']}")
    print(f"summary: {entry['summary']}")
    print("keywords: " + ", ".join(entry.get("keywords", [])))
    print("use_when:")
    for item in entry.get("use_when", []):
        print(f"  - {item}")


def resolve_doc_path(entry: dict) -> Path:
    return REPO_ROOT / entry["path"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Read indexed Codex reference documents.")
    parser.add_argument("--list", action="store_true", help="List all indexed documents.")
    parser.add_argument("--topic", help="Filter documents by topic keyword.")
    parser.add_argument("--doc", help="Show one indexed document by id.")
    parser.add_argument(
        "--show-content",
        action="store_true",
        help="Print the full Markdown content for --doc.",
    )
    args = parser.parse_args()

    index = load_index()
    docs = index.get("docs", [])

    if args.doc:
        entry = next((doc for doc in docs if doc.get("id") == args.doc), None)
        if entry is None:
            print(f"unknown doc id: {args.doc}", file=sys.stderr)
            return 1
        print_entry(entry)
        if args.show_content:
            path = resolve_doc_path(entry)
            print("\n--- content ---")
            print(path.read_text(encoding="utf-8"))
        return 0

    if args.topic:
        filtered = [doc for doc in docs if matches_topic(doc, args.topic)]
    else:
        filtered = docs

    if not filtered:
        print("no matching reference documents found", file=sys.stderr)
        return 1

    print(f"reference index: {INDEX_PATH}")
    print(f"document count: {len(filtered)}")
    for entry in filtered:
        print("")
        print_entry(entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
