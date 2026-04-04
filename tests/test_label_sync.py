from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


SYNC_MODULE_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "sync_labels.py"
SYNC_LABELS = load_module("sync_labels", SYNC_MODULE_PATH)

TRIAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "issue_triage.py"
ISSUE_TRIAGE = load_module("issue_triage", TRIAGE_MODULE_PATH)


def test_label_catalog_covers_issue_template_defaults_and_area_options() -> None:
    catalog = SYNC_LABELS.load_label_catalog(Path(".github/labels.json"))
    catalog_names = {label.name for label in catalog}

    for template_path in Path(".github/ISSUE_TEMPLATE").glob("*.yml"):
        template_text = template_path.read_text(encoding="utf-8")

        label_block = re.search(r"^labels:\n(?P<body>(?:  - .+\n)+)", template_text, re.MULTILINE)
        if label_block is None:
            continue
        for line in label_block.group("body").strip().splitlines():
            label_name = line.strip()[2:].strip()
            assert label_name in catalog_names

        for area_label in re.findall(r"area:[a-z-]+", template_text):
            assert area_label in catalog_names


def test_issue_triage_area_labels_match_catalog() -> None:
    catalog = SYNC_LABELS.load_label_catalog(Path(".github/labels.json"))
    catalog_area_labels = {label.name for label in catalog if label.name.startswith("area:")}

    assert ISSUE_TRIAGE.KNOWN_AREA_LABELS == catalog_area_labels


def test_build_sync_plan_separates_creates_updates_and_unchanged() -> None:
    desired = [
        SYNC_LABELS.LabelDefinition("area:backend", "5319e7", "Backend area"),
        SYNC_LABELS.LabelDefinition("priority:medium", "fbca04", "Medium priority"),
        SYNC_LABELS.LabelDefinition("type:feature", "0e8a16", "Feature implementation work"),
    ]
    current = [
        SYNC_LABELS.LabelDefinition("area:backend", "5319e7", "Backend area"),
        SYNC_LABELS.LabelDefinition("priority:medium", "ffffff", "Old description"),
    ]

    plan = SYNC_LABELS.build_sync_plan(desired, current)

    assert [label.name for label in plan["create"]] == ["type:feature"]
    assert [label.name for label in plan["update"]] == ["priority:medium"]
    assert [label.name for label in plan["unchanged"]] == ["area:backend"]
