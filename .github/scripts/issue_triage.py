from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


KNOWN_AREA_LABELS = {
    "area:backend",
    "area:frontend",
    "area:infra",
    "area:ci",
    "area:docs",
}

MANAGED_PREFIXES = ("type:", "priority:", "area:")
MANAGED_EXACT_LABELS = {"documentation", "question"}
SECTION_PATTERN = re.compile(
    r"^###\s+(?P<name>.+?)\r?\n(?P<value>.*?)(?=^###\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)

BUG_IMPACT_PRIORITY = {
    "서비스 중단 또는 데이터 손상 가능": "priority:high",
    "핵심 기능 사용 불가 또는 심각한 불편": "priority:high",
    "우회 가능한 문제 또는 제한적 영향": "priority:low",
}

REQUEST_PRIORITY = {
    "이번 스프린트나 현재 작업과 직접 연결됨": "priority:high",
    "가까운 시일 내 필요하지만 우회 가능": "priority:medium",
    "아이디어 탐색 또는 장기 후보": "priority:low",
    "현재 진행 중인 작업을 막고 있음": "priority:high",
    "곧 필요하지만 우회 가능": "priority:medium",
    "백로그 후보": "priority:low",
}

REQUESTED_TYPE_LABELS = {
    "type:refactor": {"type:refactor"},
    "type:test": {"type:test"},
    "type:chore": {"type:chore"},
    "documentation": {"documentation"},
    "question": {"question"},
}

HUMAN_REVIEW_SECTION = "사람 검토 필요 신호"


def normalize_body(body: str) -> str:
    return body.replace("\r\n", "\n").strip()


def parse_issue_form_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for match in SECTION_PATTERN.finditer(normalize_body(body)):
        name = match.group("name").strip()
        value = match.group("value").strip()
        sections[name] = value
    return sections


def split_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.split(r"[\n,]+", value):
        token = raw.strip()
        if token:
            tokens.append(token)
    return tokens


def extract_area_labels(sections: dict[str, str]) -> set[str]:
    area_values: set[str] = set()
    for field_name in ("영향 범위", "관련 영역"):
        value = sections.get(field_name)
        if not value:
            continue
        for token in split_tokens(value):
            if token in KNOWN_AREA_LABELS:
                area_values.add(token)
    return area_values


def extract_type_labels(
    sections: dict[str, str],
    current_labels: set[str],
) -> set[str]:
    if "type:feature" in current_labels:
        return {"type:feature"}

    requested_type = sections.get("요청 유형")
    if not requested_type:
        return set()

    first_token = split_tokens(requested_type)[0]
    return set(REQUESTED_TYPE_LABELS.get(first_token, set()))


def extract_priority_labels(
    sections: dict[str, str],
    current_labels: set[str],
) -> set[str]:
    impact = sections.get("영향도")
    if impact:
        priority = BUG_IMPACT_PRIORITY.get(split_tokens(impact)[0])
        if priority:
            return {priority}

    urgency = sections.get("요청 긴급도")
    if urgency:
        priority = REQUEST_PRIORITY.get(split_tokens(urgency)[0])
        if priority:
            return {priority}

    existing = {label for label in current_labels if label.startswith("priority:")}
    if existing:
        return existing

    return {"priority:medium"}


def extract_additive_labels(sections: dict[str, str]) -> set[str]:
    labels: set[str] = set()
    human_review = sections.get(HUMAN_REVIEW_SECTION)
    if human_review and "[x]" in human_review.lower():
        labels.add("needs-human")
    return labels


def is_managed_label(label: str) -> bool:
    return label.startswith(MANAGED_PREFIXES) or label in MANAGED_EXACT_LABELS


def compute_label_plan(body: str, current_labels: list[str]) -> dict[str, list[str]]:
    current = set(current_labels)
    sections = parse_issue_form_sections(body)

    desired = set()
    desired.update(extract_area_labels(sections))
    desired.update(extract_type_labels(sections, current))
    desired.update(extract_priority_labels(sections, current))
    desired.update(extract_additive_labels(sections))

    current_managed = {label for label in current if is_managed_label(label)}
    labels_to_add = sorted(desired - current)
    labels_to_remove = sorted(current_managed - desired)

    return {
        "desired_labels": sorted(desired),
        "labels_to_add": labels_to_add,
        "labels_to_remove": labels_to_remove,
    }


def write_outputs(output_path: Path, plan: dict[str, list[str]]) -> None:
    lines = []
    for key, value in plan.items():
        payload = json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}={payload}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    event = json.loads(args.event_path.read_text(encoding="utf-8"))
    issue = event["issue"]
    body = issue.get("body") or ""
    current_labels = [label["name"] for label in issue.get("labels", [])]
    plan = compute_label_plan(body, current_labels)
    write_outputs(args.output_path, plan)


if __name__ == "__main__":
    main()
