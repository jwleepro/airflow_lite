from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".codex" / "skills" / "reference-reader" / "scripts" / "read_reference.py"


def run_reference_reader(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        check=False,
        text=True,
        cwd=REPO_ROOT,
    )


def test_reference_reader_lists_docs() -> None:
    result = run_reference_reader("--list")

    assert result.returncode == 0
    assert "agent-format" in result.stdout
    assert "skill-format" in result.stdout


def test_reference_reader_reads_specific_doc() -> None:
    result = run_reference_reader("--doc", "skill-format")

    assert result.returncode == 0
    assert "title: Skill Package Format" in result.stdout
    assert "path: reference/codex/skill-format.md" in result.stdout
