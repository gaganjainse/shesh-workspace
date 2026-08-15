"""Quality gate: per-component tests + ruff before commit/push."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GateReport:
    path: Path
    tests_passed: bool = False
    ruff_passed: bool = True
    test_output: str = ""
    n_tests: int = 0

    @property
    def ok(self) -> bool:
        return self.tests_passed and self.ruff_passed


def _run(repo: Path, *args: str, timeout: int) -> tuple[int, str]:
    p = subprocess.run(list(args), cwd=repo, capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def run_gate(repo: Path, require_tests: bool = True) -> GateReport:
    report = GateReport(path=repo)

    if not (repo / "tests").exists() and require_tests:
        report.tests_passed = False
        report.test_output = "no tests/ directory"
        return report

    if shutil.which("ruff"):
        rc, out = _run(repo, "python3", "-m", "ruff", "check",
                       "src/", "tests/", timeout=120)
        report.ruff_passed = rc == 0
        if not report.ruff_passed:
            report.test_output = out

    rc, out = _run(repo, "python3", "-m", "pytest", "tests/", "-q",
                   "-p", "no:cacheprovider", "-o", "addopts=",
                   "--confcutdir", str(repo), timeout=300)
    report.tests_passed = rc == 0
    report.test_output = out
    for line in out.splitlines():
        if "passed" in line:
            digits = "".join(c for c in line.split("passed")[0] if c.isdigit() or c == " ")
            report.n_tests = int(digits.strip().split()[-1]) if digits.strip() else 0
    return report
