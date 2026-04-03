from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MartValidationIssue:
    severity: str
    message: str


@dataclass
class MartValidationReport:
    issues: list[MartValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def add_issue(self, severity: str, message: str) -> None:
        self.issues.append(MartValidationIssue(severity=severity, message=message))
