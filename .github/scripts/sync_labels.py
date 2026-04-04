from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


@dataclass(frozen=True)
class LabelDefinition:
    name: str
    color: str
    description: str


def resolve_gh_executable() -> str:
    detected = shutil.which("gh")
    if detected:
        return detected

    windows_default = Path("C:/Program Files/GitHub CLI/gh.exe")
    if windows_default.exists():
        return str(windows_default)

    raise FileNotFoundError("gh CLI executable was not found on PATH or at the default Windows install path")


def normalize_color(value: str) -> str:
    return value.strip().lstrip("#").lower()


def load_label_catalog(path: Path) -> list[LabelDefinition]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("labels", [])
    if not isinstance(entries, list):
        raise ValueError("labels.json must define a top-level 'labels' list")

    labels: list[LabelDefinition] = []
    seen_names: set[str] = set()
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError("each label entry must be a mapping")

        name = str(raw.get("name", "")).strip()
        color = normalize_color(str(raw.get("color", "")))
        description = str(raw.get("description", "")).strip()

        if not name:
            raise ValueError("label name must not be blank")
        if len(color) != 6:
            raise ValueError(f"label '{name}' must define a 6-digit color")
        if name in seen_names:
            raise ValueError(f"duplicate label name: {name}")

        seen_names.add(name)
        labels.append(LabelDefinition(name=name, color=color, description=description))

    return labels


def index_labels(labels: list[LabelDefinition]) -> dict[str, LabelDefinition]:
    return {label.name: label for label in labels}


def build_sync_plan(
    desired_labels: list[LabelDefinition],
    current_labels: list[LabelDefinition],
) -> dict[str, list[LabelDefinition]]:
    desired_by_name = index_labels(desired_labels)
    current_by_name = index_labels(current_labels)

    to_create: list[LabelDefinition] = []
    to_update: list[LabelDefinition] = []
    unchanged: list[LabelDefinition] = []

    for name, desired in desired_by_name.items():
        current = current_by_name.get(name)
        if current is None:
            to_create.append(desired)
            continue
        if current.color != desired.color or current.description != desired.description:
            to_update.append(desired)
            continue
        unchanged.append(desired)

    return {
        "create": sorted(to_create, key=lambda item: item.name),
        "update": sorted(to_update, key=lambda item: item.name),
        "unchanged": sorted(unchanged, key=lambda item: item.name),
    }


def run_gh(args: list[str]) -> str:
    result = subprocess.run(
        [resolve_gh_executable(), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def fetch_current_labels(repo: str) -> list[LabelDefinition]:
    response = run_gh(["api", f"repos/{repo}/labels?per_page=100"])
    payload = json.loads(response)
    return [
        LabelDefinition(
            name=str(item["name"]).strip(),
            color=normalize_color(str(item.get("color", ""))),
            description=str(item.get("description") or "").strip(),
        )
        for item in payload
    ]


def create_label(repo: str, label: LabelDefinition) -> None:
    run_gh(
        [
            "api",
            "--method",
            "POST",
            f"repos/{repo}/labels",
            "-f",
            f"name={label.name}",
            "-f",
            f"color={label.color}",
            "-f",
            f"description={label.description}",
        ]
    )


def update_label(repo: str, label: LabelDefinition) -> None:
    run_gh(
        [
            "api",
            "--method",
            "PATCH",
            f"repos/{repo}/labels/{quote(label.name, safe='')}",
            "-f",
            f"new_name={label.name}",
            "-f",
            f"color={label.color}",
            "-f",
            f"description={label.description}",
        ]
    )


def apply_sync_plan(repo: str, plan: dict[str, list[LabelDefinition]]) -> None:
    for label in plan["create"]:
        create_label(repo, label)
    for label in plan["update"]:
        update_label(repo, label)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument(
        "--labels-path",
        type=Path,
        default=Path(".github/labels.json"),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    desired_labels = load_label_catalog(args.labels_path)
    current_labels = fetch_current_labels(args.repo)
    plan = build_sync_plan(desired_labels, current_labels)

    summary = {
        "create": [label.name for label in plan["create"]],
        "update": [label.name for label in plan["update"]],
        "unchanged_count": len(plan["unchanged"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not args.dry_run:
        apply_sync_plan(args.repo, plan)


if __name__ == "__main__":
    main()
