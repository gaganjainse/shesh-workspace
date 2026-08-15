"""Tests for the autopilot safety core."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from autopilot import safety  # noqa: E402
from autopilot.ledger import Ledger, Task  # noqa: E402
from autopilot.gate import run_gate  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    import subprocess
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True)


def _make_repo(tmp_path: Path, with_tests: bool = True) -> Path:
    repo = tmp_path / "comp"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "__init__.py").write_text("")
    (repo / "tests").mkdir()
    if with_tests:
        (repo / "tests" / "test_ok.py").write_text(
            "def test_ok():\n    assert 1 + 1 == 2\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


# ── safety ──────────────────────────────────────────────────────

def test_safe_path_refuses_protected(tmp_path):
    import pytest
    with pytest.raises(safety.SafetyError):
        safety.assert_safe_path(tmp_path / ".ssh" / "id_rsa")


def test_assert_can_commit_passes_when_tests_green(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "src" / "new.py").write_text("X = 1\n")
    _git(repo, "add", "-A")
    report = safety.assert_can_commit(repo)
    assert report.ok


def test_assert_can_commit_refuses_when_tests_red(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "tests" / "test_bad.py").write_text("def test_bad(): assert False\n")
    _git(repo, "add", "-A")
    import pytest
    with pytest.raises(safety.SafetyError):
        safety.assert_can_commit(repo)


def test_safe_commit_and_push_remote_check(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "src" / "new.py").write_text("X = 1\n")
    sha = safety.safe_commit(repo, "test change")
    assert len(sha) >= 7
    # No remote set -> push should refuse, not force.
    import pytest
    with pytest.raises(safety.SafetyError):
        safety.safe_push(repo)


def test_rollback_soft_resets(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "src" / "new.py").write_text("X = 1\n")
    safety.safe_commit(repo, "to be rolled back")
    safety.rollback(repo)
    assert safety.has_uncommitted(repo)  # changes are back in working tree


# ── ledger ──────────────────────────────────────────────────────

def test_ledger_persists_tasks(tmp_path):
    path = tmp_path / "ledger.jsonl"
    l1 = Ledger(path)
    l1.add(Task(id="t1", title="do thing"))
    l1.update("t1", status="running")
    l2 = Ledger(path)
    assert l2.get("t1").status == "running"


def test_ledger_next_pending(tmp_path):
    ledger = Ledger(tmp_path / "l.jsonl")
    ledger.add(Task(id="a", title="a"))
    ledger.add(Task(id="b", title="b"))
    assert ledger.next_pending().id == "a"
    ledger.update("a", status="done")
    assert ledger.next_pending().id == "b"


# ── gate ────────────────────────────────────────────────────────

def test_gate_green(tmp_path):
    repo = _make_repo(tmp_path)
    r = run_gate(repo)
    assert r.ok
    assert r.n_tests >= 1


def test_gate_red_on_failing_test(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "tests" / "test_bad.py").write_text("def test_bad(): assert False")
    r = run_gate(repo)
    assert not r.ok


def test_gate_requires_tests(tmp_path):
    import shutil
    repo = _make_repo(tmp_path)
    shutil.rmtree(repo / "tests")
    r = run_gate(repo)
    assert not r.ok and "no tests" in r.test_output
